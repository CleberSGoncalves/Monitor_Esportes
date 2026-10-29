import os
import re

GUI_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gui", "main_gui.py")

with open(GUI_PATH, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add _sort_games_chronologically before _load_scheduled_games
sort_func = '''def _sort_games_chronologically(games_list: list) -> list:
    """Ordena estritamente a fila de agendamentos por ordem cronológica (data e hora de início)."""
    def _parse_key(g):
        try:
            d_str = str(g.get("date", "")).strip().replace("-", "/")
            t_str = str(g.get("time", "")).strip() or "00:00"
            return datetime.strptime(f"{d_str} {t_str}", "%d/%m/%Y %H:%M")
        except Exception:
            return datetime.max
    return sorted(games_list, key=_parse_key)

'''

if "def _sort_games_chronologically" not in code:
    code = code.replace("def _load_scheduled_games() -> list:", sort_func + "def _load_scheduled_games() -> list:")
    print("Added _sort_games_chronologically")

# 2. In _load_scheduled_games, sort before saving and returning
old_valid = '''                    if valid_games:

                        _save_scheduled_games(valid_games)

                        return valid_games'''
new_valid = '''                    if valid_games:
                        valid_games = _sort_games_chronologically(valid_games)
                        _save_scheduled_games(valid_games)
                        return valid_games'''
if old_valid in code:
    code = code.replace(old_valid, new_valid)
    print("Updated valid_games sort in _load_scheduled_games")
else:
    # Regex fallback
    code = re.sub(
        r'if valid_games:\s*_save_scheduled_games\(valid_games\)\s*return valid_games',
        'if valid_games:\n                        valid_games = _sort_games_chronologically(valid_games)\n                        _save_scheduled_games(valid_games)\n                        return valid_games',
        code
    )
    print("Regex updated valid_games in _load_scheduled_games")

# 3. In _save_scheduled_games, sort list
old_save = '''def _save_scheduled_games(games_list: list) -> None:

    _save_config_file("scheduled_games.json", games_list)'''
new_save = '''def _save_scheduled_games(games_list: list) -> None:
    sorted_list = _sort_games_chronologically(games_list)
    _save_config_file("scheduled_games.json", sorted_list)'''
if old_save in code:
    code = code.replace(old_save, new_save)
    print("Updated _save_scheduled_games")
else:
    code = re.sub(
        r'def _save_scheduled_games\(games_list: list\) -> None:\s*_save_config_file\("scheduled_games\.json", games_list\)',
        'def _save_scheduled_games(games_list: list) -> None:\n    sorted_list = _sort_games_chronologically(games_list)\n    _save_config_file("scheduled_games.json", sorted_list)',
        code
    )
    print("Regex updated _save_scheduled_games")

# 4. In _update_schedule_panel_ui, sort games
old_panel = 'games = [g for g in raw_games if g.get("status") in ["pending", "running", "queued", "failed"]]'
new_panel = 'games = _sort_games_chronologically([g for g in raw_games if g.get("status") in ["pending", "running", "queued", "failed"]])'
if old_panel in code:
    code = code.replace(old_panel, new_panel)
    print("Updated games sort in _update_schedule_panel_ui")

# 5. In _open_schedule_queue_modal, sort current_sched and cbf_evts
old_modal_sched = 'current_sched = [g for g in getattr(self, "_scheduled_games", []) if g.get("status") in ("pending", "running", "queued", "failed")]'
new_modal_sched = 'current_sched = _sort_games_chronologically([g for g in getattr(self, "_scheduled_games", []) if g.get("status") in ("pending", "running", "queued", "failed")])'
if old_modal_sched in code:
    code = code.replace(old_modal_sched, new_modal_sched)
    print("Updated current_sched sort in _open_schedule_queue_modal")

# Also sort games_to_show before populating rows
old_show = '''        for idx in range(5):

            if idx < len(games_to_show):'''
new_show = '''        games_to_show = _sort_games_chronologically(games_to_show)

        for idx in range(5):

            if idx < len(games_to_show):'''
if old_show in code:
    code = code.replace(old_show, new_show)
    print("Updated games_to_show sort in _open_schedule_queue_modal")

# 6. In _auto_fill_cbf_events, sort cbf_events
old_autofill = 'cbf_events = CBFScheduleFetcher.get_upcoming_matches()'
new_autofill = 'cbf_events = _sort_games_chronologically(CBFScheduleFetcher.get_upcoming_matches())'
if old_autofill in code:
    code = code.replace(old_autofill, new_autofill, 1)
    print("Updated cbf_events sort in _auto_fill_cbf_events")

# 7. In _save_schedule, sort new_scheduled_list
old_modal_save = '''            _save_scheduled_games(new_scheduled_list)

            self._scheduled_games = new_scheduled_list'''
new_modal_save = '''            new_scheduled_list = _sort_games_chronologically(new_scheduled_list)
            _save_scheduled_games(new_scheduled_list)
            self._scheduled_games = new_scheduled_list'''
if old_modal_save in code:
    code = code.replace(old_modal_save, new_modal_save)
    print("Updated new_scheduled_list sort in _save_schedule")

# 8. In _run_auto_schedule_fetch, sort games before saving
old_auto_save = '''                if added_count > 0:

                    _save_scheduled_games(games)

                    self._scheduled_games = games'''
new_auto_save = '''                if added_count > 0:
                    games = _sort_games_chronologically(games)
                    _save_scheduled_games(games)
                    self._scheduled_games = games'''
if old_auto_save in code:
    code = code.replace(old_auto_save, new_auto_save)
    print("Updated games sort in _run_auto_schedule_fetch")

# 9. In _trigger_scheduled_audit, pass allow_web_fallback
old_payload = '''                    payload = {

                        "team1": _game.get("team1"),

                        "team2": _game.get("team2"),

                        "competition": _game.get("comp"),

                        "platform": _game.get("platform"),

                        "date": _game.get("date"),

                        "start_timestamp": None,

                        "duration": None,

                        "video_url": None,

                        "transcript_text": None

                    }'''

new_payload = '''                    kickoff_dt = None
                    try:
                        kickoff_dt = datetime.strptime(f"{_game.get('date')} {_game.get('time')}", "%d/%m/%Y %H:%M")
                    except:
                        pass
                    passed_tol = bool(kickoff_dt and (datetime.now() - kickoff_dt > timedelta(hours=2, minutes=30)))
                    allow_fb = bool(_game.get("_sumula_attempts", 0) >= 2 or passed_tol)
                    payload = {
                        "team1": _game.get("team1"),
                        "team2": _game.get("team2"),
                        "competition": _game.get("comp"),
                        "platform": _game.get("platform"),
                        "date": _game.get("date"),
                        "start_timestamp": None,
                        "duration": None,
                        "video_url": None,
                        "transcript_text": None,
                        "allow_web_fallback": allow_fb
                    }'''

if old_payload in code:
    code = code.replace(old_payload, new_payload)
    print("Updated payload with allow_web_fallback in _trigger_scheduled_audit")

with open(GUI_PATH, "w", encoding="utf-8") as f:
    f.write(code)

print("Saved main_gui.py successfully!")
