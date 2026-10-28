path = "modules/live_channel_monitor.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update apply_auto_detect_all to strictly check is_likely_match
old_auto_det = """                if st in ("upcoming", "live") or is_recent_ended:
                    ev["selected"] = True
                    ev["auto_queued"] = True"""

new_auto_det = """                if st in ("upcoming", "live") or is_recent_ended:
                    from modules.narration_chronology import is_likely_match
                    dur_val = int(ev.get("duration") or 0)
                    if not is_likely_match(ev.get("title", ""), dur_val):
                        # Descarta programas, debates, noticias e concentracoes
                        continue
                    ev["selected"] = True
                    ev["auto_queued"] = True"""

# 2. Update _analyze_job to remove non-match from queue immediately
old_not_match = """            self.update_event(
                vid,
                pipeline="not_match",
                is_match_narration=False,
                transcript_analysis=analysis,
                meta=meta,
                brand_mentions=brand_mentions,
                brands_summary=brands_summary,
                progress=prog_msg,
                error="",
            )
            self.log(f"ℹ️ [{ev.get('title', vid)[:45]}] Classificado como '{cat}' (Não é partida narrada).")"""

new_not_match = """            self.update_event(
                vid,
                pipeline="not_match",
                is_match_narration=False,
                transcript_analysis=analysis,
                meta=meta,
                brand_mentions=brand_mentions,
                brands_summary=brands_summary,
                progress=prog_msg,
                error="",
                selected=False,
                user_unselected=True
            )
            self.remove_from_queue(vid)
            self.log(f"🗑️ [Auto-Eliminação] '{ev.get('title', vid)[:45]}' não é jogo e foi removido da fila.")"""

# 3. Add clean_non_matches_from_queue method
clean_method = """
    def clean_non_matches_from_queue(self) -> int:
        \"\"\"Remove sumariamente da fila da direita todos os eventos que não são partidas de futebol reais.\"\"\"
        from modules.narration_chronology import is_likely_match, is_definitely_non_match
        removed = 0
        with self.lock:
            queue_list = list(self.state.get("active_queue", []))
            for vid in queue_list:
                ev = self.state["events"].get(vid)
                if not ev:
                    if vid in self.state["active_queue"]:
                        self.state["active_queue"].remove(vid)
                        removed += 1
                    continue
                is_match = ev.get("is_match_narration")
                pipe = ev.get("pipeline")
                title = ev.get("title", "")
                dur = int(ev.get("duration") or 0)

                is_non, _ = is_definitely_non_match(title)
                should_remove = False
                if pipe == "not_match" or is_match is False:
                    should_remove = True
                elif is_non:
                    should_remove = True
                elif pipe in ("waiting", "upcoming", "idle") and not is_likely_match(title, dur):
                    should_remove = True

                if should_remove:
                    ev["selected"] = False
                    ev["user_unselected"] = True
                    ev["pipeline"] = "not_match"
                    if vid in self.state["active_queue"]:
                        self.state["active_queue"].remove(vid)
                    removed += 1

            # Resgata jogos de 24/10 se estiverem pendentes
            for vid, ev in self.state["events"].items():
                title = ev.get("title", "")
                if "INTER X BOTAFOGO" in title.upper() and ("24/10" in title or "24/10" in str(ev.get("scheduled_epoch"))):
                    ev["status"] = "ended"
                    if ev.get("pipeline") in ("waiting", "idle", None):
                        ev["pipeline"] = "ended"
                    ev["selected"] = True
                    ev["is_match_narration"] = True
                    if vid not in self.state["active_queue"]:
                        self.state["active_queue"].append(vid)

        if removed:
            self.log(f"🧹 [Faxina] {removed} eventos que não eram partidas de futebol foram eliminados da fila.")
            self._changed()
        return removed
"""

changed = False
if old_auto_det in content:
    content = content.replace(old_auto_det, new_auto_det)
    changed = True
    print("[+] apply_auto_detect_all patched!")

if old_not_match in content:
    content = content.replace(old_not_match, new_not_match)
    changed = True
    print("[+] _analyze_job patched!")

if "def clean_non_matches_from_queue" not in content:
    content += clean_method
    changed = True
    print("[+] clean_non_matches_from_queue added!")

if changed:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Sucesso!")
else:
    print("Nenhuma alteracao aplicada!")
