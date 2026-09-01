from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


@dataclass
class ReportPaths:
    json_path: str
    pdf_path: str


def _safe_filename(name: str) -> str:
    s = (name or "report").strip()
    s = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in s)
    s = re.sub(r"_+", "_", s).strip("_")
    return (s or "report")[:120]


def _uniq_keep_order(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _fmt_seconds(v: Any) -> str:
    try:
        f = float(v)
    except Exception:
        return "—"

    if f < 0:
        f = 0.0

    h = int(f // 3600)
    m = int((f % 3600) // 60)
    s = int(f % 60)

    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _fmt_duration(start_t: Any, end_t: Any) -> str:
    try:
        if start_t is None or end_t is None:
            return "—"
        dur = max(0.0, float(end_t) - float(start_t))
        return _fmt_seconds(dur)
    except Exception:
        return "—"


def _phase_label(label: Optional[str]) -> str:
    mapping = {
        "HUD_PARCIAL": "HUD Parcial",
        "CLOUD_ORACLE_CORRECTION": "Correção via IA",
        "PRIMEIRO_TEMPO_START": "Início do 1º Tempo",
        "SEGUNDO_TEMPO_START": "Início do 2º Tempo",
        "INTERVALO_START": "Início do Intervalo",
        "POS_JOGO_START": "Fim de Jogo",
        "pre_jogo": "Pré-jogo",
        "jogo": "Jogo",
        "intervalo": "Intervalo",
        "pos_jogo": "Pós-jogo",
        "primeiro_tempo": "1º Tempo",
        "segundo_tempo": "2º Tempo",
        "em_jogo": "Em jogo",
        "hud_parcial": "HUD parcial",
    }
    return mapping.get(str(label or ""), str(label or "—"))


def _context_label(label: Optional[str]) -> str:
    mapping = {
        "PRE_JOGO_COUNTDOWN": "Pré-jogo",
        "JOGO_AO_VIVO": "Jogo ao vivo",
        "INTERVALO": "Intervalo",
        "POS_JOGO": "Pós-jogo",
        "COMENTARIO_ANALISE": "Comentário",
        "REPLAY": "Replay",
        "VAR": "VAR",
        "INTERRUPCAO_TECNICA": "Interrupção técnica",
        "CLOUD_ORACLE_UPDATE": "Insight da IA",
        "pre_jogo_countdown": "Pré-jogo",
        "jogo_ao_vivo": "Jogo ao vivo",
        "intervalo": "Intervalo",
        "pos_jogo": "Pós-jogo",
        "comentario": "Comentário",
        "replay": "Replay",
        "var": "VAR",
        "interrupcao_tecnica": "Interrupção técnica",
    }
    return mapping.get(str(label or ""), str(label or "—"))


def _match_event_label(label: Optional[str]) -> str:
    mapping = {
        "GOL": "Gol",
        "VAR": "VAR",
        "SUBSTITUICAO": "Substituição",
        "CARTAO_AMARELO": "Cartão amarelo",
        "CARTAO_VERMELHO": "Cartão vermelho",
        "REPLAY": "Replay",
        "HUD_MENSAGEM": "Informação HUD",
    }
    return mapping.get(str(label or ""), str(label or "—"))


def _interruption_label(label: Optional[str]) -> str:
    mapping = {
        "BLACK_SCREEN": "Tela preta",
        "FREEZE": "Congelamento",
    }
    return mapping.get(str(label or ""), str(label or "—"))


def _clean_inline_text(value: Any, max_len: int = 200) -> str:
    txt = re.sub(r"\s+", " ", str(value or "")).strip()
    if not txt:
        return ""
    return txt[:max_len]


def _banner_kind_from_text(text: str, context: Optional[str] = None, event_label: Optional[str] = None) -> str:
    s = (text or "").upper()
    ctx = str(context or "").lower()
    ev = str(event_label or "").upper()

    if ev == "GOL" or "GOOOL" in s or "GOL" in s:
        return "evento"
    if ev in {"VAR", "SUBSTITUICAO", "CARTAO_AMARELO", "CARTAO_VERMELHO"}:
        return "evento"
    if any(k in s for k in ["AO VIVO EM", "DAQUI A POUCO", "EM INSTANTES", "VAI COMEÇAR", "VAI COMECAR", "AGUARDE", "PRÉ-JOGO", "PRE JOGO"]):
        return "pré-jogo"
    if "countdown" in ctx or "pre_jogo" in ctx:
        return "pré-jogo"
    if "intervalo" in ctx or "INTERVALO" in s:
        return "intervalo"
    if "posse" in s or "ESTAT" in s:
        return "informativo"
    return "informativo"


class ReportGenerator:
    """
    Gera um JSON rico e um PDF vivo acumulativo do evento.
    O PDF sempre reflete o estado atual + histórico relevante + banners capturados.
    """

    def __init__(self, reports_dir: str) -> None:
        self.reports_dir = reports_dir
        os.makedirs(self.reports_dir, exist_ok=True)

    def build_report_payload(
        self,
        event_meta: Dict[str, Any],
        timeline: List[Dict[str, Any]],
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat() + "Z"
        summary = self._summarize(timeline, notes or {})

        return {
            "generated_at_utc": now,
            "event": {
                "id": event_meta.get("id"),
                "title": event_meta.get("title"),
                "url": event_meta.get("url"),
                "channel": event_meta.get("channel"),
                "scheduled_start": event_meta.get("scheduled_start"),
                "status": event_meta.get("status"),
                "competition": event_meta.get("competition"),
                "match_display": event_meta.get("match_display"),
                "team_a": event_meta.get("team_a"),
                "team_b": event_meta.get("team_b"),
            },
            "analysis": {
                "principle": "derived_data_only",
                "timeline": timeline,
                "summary": summary,
                "notes": notes or {},
            },
        }

    def _write_json_atomic(self, json_path: str, payload: Dict[str, Any]) -> str:
        tmp_path = json_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, json_path)
        return json_path

    def _normalize_single_session_name(self, base_name: str, payload: Optional[Dict[str, Any]] = None) -> str:
        raw = str(base_name or "").strip()
        safe = _safe_filename(raw)

        event = (payload or {}).get("event", {}) if payload else {}
        notes = (payload or {}).get("analysis", {}).get("notes", {}) if payload else {}

        title = event.get("title") or notes.get("current_match_display") or event.get("match_display")
        channel = event.get("channel")

        if title:
            parts = []
            if channel:
                parts.append(_safe_filename(str(channel)).lower())
            parts.append(_safe_filename(str(title)).lower())
            stable = "_".join([p for p in parts if p])
            return _safe_filename(f"live_{stable}")

        safe = re.sub(r"^(parcial|partial|tmp|temp|live)_+", "", safe, flags=re.IGNORECASE)
        safe = re.sub(r"_(\d{8,14}|\d{2,6})$", "", safe)
        safe = re.sub(r"(_json|_pdf)$", "", safe, flags=re.IGNORECASE)

        if "youtube" in safe.lower():
            y = re.sub(r"https?_+", "", safe, flags=re.IGNORECASE)
            y = re.sub(r"(www_)?youtube_com_+", "youtube_", y, flags=re.IGNORECASE)
            y = re.sub(r"watch_v_+", "", y, flags=re.IGNORECASE)
            y = re.sub(r"streams_*$", "", y, flags=re.IGNORECASE)
            safe = y

        return _safe_filename(f"live_{safe or 'session'}")

    def write_live_report(
        self,
        event_meta: Dict[str, Any],
        timeline: List[Dict[str, Any]],
        notes: Optional[Dict[str, Any]] = None,
        base_name: str = "session_live",
        generate_pdf: bool = True,
    ) -> ReportPaths:
        payload = self.build_report_payload(event_meta, timeline, notes)
        stable_name = self._normalize_single_session_name(base_name, payload)
        json_path = os.path.join(self.reports_dir, f"{stable_name}.json")
        pdf_path = os.path.join(self.reports_dir, f"{stable_name}.pdf")
        self._write_json_atomic(json_path, payload)
        if generate_pdf:
            self._write_pdf(payload, pdf_path)
        return ReportPaths(json_path=json_path, pdf_path=pdf_path)

    def finalize_live_report(
        self,
        event_meta: Dict[str, Any],
        timeline: List[Dict[str, Any]],
        notes: Optional[Dict[str, Any]] = None,
        base_name: str = "session_live",
        generate_pdf: bool = True,
    ) -> ReportPaths:
        payload = self.build_report_payload(event_meta, timeline, notes)
        stable_name = self._normalize_single_session_name(base_name, payload)
        json_path = os.path.join(self.reports_dir, f"{stable_name}.json")
        pdf_path = os.path.join(self.reports_dir, f"{stable_name}.pdf")
        self._write_json_atomic(json_path, payload)
        if generate_pdf:
            self._write_pdf(payload, pdf_path)
        return ReportPaths(json_path=json_path, pdf_path=pdf_path)

    def update_single_file_report(
        self,
        event_meta: Dict[str, Any],
        timeline: List[Dict[str, Any]],
        notes: Optional[Dict[str, Any]] = None,
        base_name: str = "session_live",
        finalize: bool = False,
        generate_pdf_on_finalize: bool = True,
        generate_pdf_while_live: bool = True,
    ) -> ReportPaths:
        if finalize:
            return self.finalize_live_report(
                event_meta=event_meta,
                timeline=timeline,
                notes=notes,
                base_name=base_name,
                generate_pdf=generate_pdf_on_finalize,
            )
        return self.write_live_report(
            event_meta=event_meta,
            timeline=timeline,
            notes=notes,
            base_name=base_name,
            generate_pdf=generate_pdf_while_live,
        )

    def write_report(self, payload: Dict[str, Any], base_name: str) -> ReportPaths:
        notes = ((payload.get("analysis") or {}).get("notes") or {})
        force_legacy = bool(notes.get("force_legacy_multi_file"))

        if force_legacy:
            safe_name = _safe_filename(base_name)
            json_path = os.path.join(self.reports_dir, f"{safe_name}.json")
            pdf_path = os.path.join(self.reports_dir, f"{safe_name}.pdf")
            self._write_json_atomic(json_path, payload)
            self._write_pdf(payload, pdf_path)
            return ReportPaths(json_path=json_path, pdf_path=pdf_path)

        stable_name = self._normalize_single_session_name(base_name, payload)
        json_path = os.path.join(self.reports_dir, f"{stable_name}.json")
        pdf_path = os.path.join(self.reports_dir, f"{stable_name}.pdf")
        self._write_json_atomic(json_path, payload)

        report_kind = str(notes.get("report_kind") or "").strip().lower()
        should_generate_pdf = report_kind == "final" or bool(notes.get("finalize_report"))
        if should_generate_pdf:
            self._write_pdf(payload, pdf_path)

        return ReportPaths(json_path=json_path, pdf_path=pdf_path)

    def _summarize(self, timeline: List[Dict[str, Any]], notes: Dict[str, Any]) -> Dict[str, Any]:
        phases: List[str] = []
        contexts: Dict[str, int] = {}
        match_events: List[Dict[str, Any]] = []
        interruptions: List[Dict[str, Any]] = []
        event_history: List[Dict[str, Any]] = []
        banners: List[Dict[str, Any]] = []
        hud_history: List[Dict[str, Any]] = []

        last_clock = notes.get("current_clock") or None
        last_score = notes.get("current_score") or None
        last_phase = notes.get("current_phase") or None
        last_context = notes.get("current_context") or None
        last_context_summary = notes.get("current_context_summary") or None
        first_phase_t = None
        last_t_seconds = 0.0

        open_interruptions: Dict[str, Dict[str, Any]] = {}
        seen_banner_keys = set()
        seen_hud_keys = set()
        seen_history_keys = set()

        def add_history(t_seconds: float, typ: str, label: str, detail: str, importance: int = 1) -> None:
            clean_detail = _clean_inline_text(detail, 180)
            if not clean_detail:
                return
            
            # OTIMIZAÇÃO: Evitar repetecos idênticos em curto intervalo (ex: banners ou HUDs repetidos)
            if event_history:
                last = event_history[-1]
                if last["detail"] == clean_detail and (float(t_seconds) - last["t_seconds"]) < 60:
                    return

            key = (round(float(t_seconds or 0.0), 1), typ, label, clean_detail)
            if key in seen_history_keys:
                return
            seen_history_keys.add(key)
            event_history.append(
                {
                    "t_seconds": float(t_seconds or 0.0),
                    "t_pretty": _fmt_seconds(t_seconds),
                    "type": typ,
                    "label": label,
                    "detail": clean_detail,
                    "importance": int(importance),
                }
            )

        def add_banner(t_seconds: float, text: str, kind: str, context: str = "", source: str = "", score: str = "", clock: str = "") -> None:
            clean = _clean_inline_text(text, 180)
            if not clean:
                return
            key = (clean.upper(), kind, context)
            if key in seen_banner_keys:
                return
            seen_banner_keys.add(key)
            banners.append(
                {
                    "t_seconds": float(t_seconds or 0.0),
                    "t_pretty": _fmt_seconds(t_seconds),
                    "kind": kind or "informativo",
                    "text": clean,
                    "context": _clean_inline_text(context, 80),
                    "source": source or "timeline",
                    "score": score or None,
                    "clock": clock or None,
                }
            )

        def add_hud_snapshot(t_seconds: float, score: Any, clock: Any, phase: Any, confidence: str = "alta") -> None:
            score_txt = _clean_inline_text(score, 20)
            clock_txt = _clean_inline_text(clock, 20)
            phase_txt = _phase_label(_clean_inline_text(phase, 30)) if phase else ""
            if not (score_txt or clock_txt or phase_txt):
                return
            if score_txt and not clock_txt and not phase_txt:
                return
            key = (score_txt, clock_txt, phase_txt)
            if key in seen_hud_keys:
                return
            seen_hud_keys.add(key)
            hud_history.append(
                {
                    "t_seconds": float(t_seconds or 0.0),
                    "t_pretty": _fmt_seconds(t_seconds),
                    "score": score_txt or "—",
                    "clock": clock_txt or "—",
                    "phase": phase_txt or "—",
                    "confidence": confidence,
                }
            )

        for ev in timeline:
            typ = ev.get("type")
            label = ev.get("label", "")
            details = ev.get("details") or {}
            t_seconds = float(ev.get("t_seconds", 0.0) or 0.0)
            last_t_seconds = max(last_t_seconds, t_seconds)

            if typ == "phase":
                phases.append(label)
                if first_phase_t is None:
                    first_phase_t = t_seconds
                
                friendly_phase = _phase_label(label)
                if label == "CLOUD_ORACLE_CORRECTION":
                    corrected = details.get("current_phase")
                    if corrected:
                        last_phase = corrected
                        friendly_phase = f"Correção via IA: {_phase_label(corrected)}"
                    else:
                        last_phase = label
                else:
                    last_phase = label

                add_history(t_seconds, "phase", label, friendly_phase, 3)

            if typ == "context":
                contexts[label] = contexts.get(label, 0) + 1
                last_context = label
                screen_ctx = details.get("screen_context") or {}
                if details.get("context_summary"):
                    last_context_summary = details.get("context_summary")
                elif details.get("banner_summary"):
                    last_context_summary = details.get("banner_summary")
                elif details.get("speech_summary"):
                    last_context_summary = details.get("speech_summary")
                elif isinstance(screen_ctx, dict) and screen_ctx.get("context_summary"):
                    last_context_summary = screen_ctx.get("context_summary")

                ctx_detail = details.get("context_summary") or details.get("banner_summary") or details.get("speech_summary")
                if label:
                    add_history(t_seconds, "context", label, ctx_detail or _context_label(label), 1)

                for text_key in ("banner_summary", "context_summary", "text", "banner"):
                    txt = details.get(text_key)
                    if txt:
                        add_banner(
                            t_seconds,
                            txt,
                            _banner_kind_from_text(str(txt), label),
                            context=_context_label(label),
                            source=f"context:{text_key}",
                            score=details.get("score") or details.get("score_to") or "",
                            clock=details.get("clock") or "",
                        )
                        break

            if details.get("clock"):
                last_clock = details.get("clock")
            if details.get("score"):
                last_score = details.get("score")
            if details.get("score_to"):
                last_score = details.get("score_to")

            if typ == "match_event":
                item = {
                    "label": label,
                    "label_pretty": _match_event_label(label),
                    "t_seconds": t_seconds,
                    "t_pretty": _fmt_seconds(t_seconds),
                    "clock": details.get("clock"),
                    "score_from": details.get("score_from"),
                    "score_to": details.get("score_to"),
                    "banner": details.get("banner"),
                    "summary": details.get("summary"),
                }
                match_events.append(item)
                detail = details.get("summary") or details.get("banner") or details.get("mensagem") or _match_event_label(label)
                add_history(t_seconds, "match_event", label, detail, 4)
                if details.get("banner"):
                    add_banner(
                        t_seconds,
                        details.get("banner"),
                        _banner_kind_from_text(str(details.get("banner")), last_context, label),
                        context=_match_event_label(label),
                        source="match_event:banner",
                        score=details.get("score_to") or details.get("score_from") or "",
                        clock=details.get("clock") or "",
                    )

            if typ == "interruption":
                if label.endswith("_START"):
                    key = label.replace("_START", "")
                    open_interruptions[key] = ev
                    add_history(t_seconds, "interruption", label, f"{_interruption_label(key)} iniciada", 5)
                elif label.endswith("_END"):
                    key = label.replace("_END", "")
                    start_ev = open_interruptions.pop(key, None)
                    start_t = start_ev.get("t_seconds") if start_ev else None
                    end_t = t_seconds
                    interruptions.append(
                        {
                            "label": key,
                            "label_pretty": _interruption_label(key),
                            "start_t_seconds": start_t,
                            "end_t_seconds": end_t,
                            "duration_seconds": (max(0.0, float(end_t) - float(start_t)) if start_t is not None else None),
                            "duration_pretty": _fmt_duration(start_t, end_t),
                        }
                    )
                    add_history(t_seconds, "interruption", label, f"{_interruption_label(key)} encerrada", 5)

            if typ in {"phase", "context", "match_event"}:
                add_hud_snapshot(
                    t_seconds,
                    details.get("score") or details.get("score_to") or last_score,
                    details.get("clock") or last_clock,
                    details.get("phase") or details.get("phase_text") or last_phase,
                )

        for key, start_ev in open_interruptions.items():
            start_t = start_ev.get("t_seconds")
            interruptions.append(
                {
                    "label": key,
                    "label_pretty": _interruption_label(key),
                    "start_t_seconds": start_t,
                    "end_t_seconds": None,
                    "duration_seconds": None,
                    "duration_pretty": "em aberto",
                }
            )

        add_hud_snapshot(last_t_seconds, last_score, last_clock, last_phase)

        phase_sequence_pretty = [_phase_label(x) for x in _uniq_keep_order(phases)]
        current_state = {
            "report_kind": str(notes.get("report_kind") or "live"),
            "last_update_utc": datetime.utcnow().isoformat() + "Z",
            "session_last_t_seconds": round(last_t_seconds, 3),
            "session_last_t_pretty": _fmt_seconds(last_t_seconds),
            "current_phase": last_phase,
            "current_phase_pretty": _phase_label(last_phase),
            "current_context": last_context,
            "current_context_pretty": _context_label(last_context),
            "current_context_summary": _clean_inline_text(last_context_summary, 220) or "—",
            "current_score": last_score or "—",
            "current_clock": last_clock or "—",
        }

        banner_headline = banners[-1]["text"] if banners else "—"
        editorial_lines: List[str] = []
        editorial_lines.append(
            f"A transmissão está em {current_state['current_phase_pretty'].lower() if current_state['current_phase_pretty'] != '—' else 'estado não confirmado'}."
        )
        if current_state["current_score"] != "—" or current_state["current_clock"] != "—":
            editorial_lines.append(
                f"HUD atual: placar {current_state['current_score']} e clock {current_state['current_clock']}."
            )
        if current_state["current_context_summary"] != "—":
            editorial_lines.append(current_state["current_context_summary"])
        elif banner_headline != "—":
            editorial_lines.append(f"Último banner relevante: {banner_headline}.")
        if interruptions:
            editorial_lines.append(f"Interrupções técnicas acumuladas: {len(interruptions)}.")
        else:
            editorial_lines.append("Nenhuma interrupção técnica relevante até o momento.")

        return {
            "total_timeline_items": len(timeline),
            "phases_detected": _uniq_keep_order(phases),
            "phases_detected_pretty": phase_sequence_pretty,
            "contexts_count": contexts,
            "contexts_count_pretty": {_context_label(k): v for k, v in contexts.items()},
            "match_events": match_events,
            "interruptions": interruptions,
            "interruptions_count": len(interruptions),
            "match_events_count": len(match_events),
            "last_clock": last_clock,
            "last_score": last_score,
            "last_phase": last_phase,
            "last_phase_pretty": _phase_label(last_phase),
            "last_context": last_context,
            "last_context_pretty": _context_label(last_context),
            "last_context_summary": last_context_summary,
            "last_screen_context_summary": last_context_summary,
            "first_phase_t_seconds": first_phase_t,
            "first_phase_t_pretty": _fmt_seconds(first_phase_t) if first_phase_t is not None else "—",
            "current_state": current_state,
            "editorial_summary": " ".join([x for x in editorial_lines if x]).strip(),
            "event_history": sorted(event_history, key=lambda x: x.get("t_seconds", 0.0))[-80:],
            "banners": sorted(banners, key=lambda x: x.get("t_seconds", 0.0))[-80:],
            "hud_history": sorted(hud_history, key=lambda x: x.get("t_seconds", 0.0))[-60:],
            "banner_headline": banner_headline,
        }

    def _write_pdf(self, payload: Dict[str, Any], pdf_path: str) -> None:
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        y = height - 42
        line_h = 13

        event = payload.get("event", {}) or {}
        analysis = payload.get("analysis", {}) or {}
        summary = analysis.get("summary", {}) or {}
        current = summary.get("current_state", {}) or {}

        def ensure_page(lines_needed: int = 1) -> None:
            nonlocal y
            if y - (line_h * lines_needed) < 45:
                c.showPage()
                y = height - 42

        def draw_line(txt: str = "", font: str = "Helvetica", size: int = 10) -> None:
            nonlocal y
            ensure_page(1)
            c.setFont(font, size)
            c.drawString(36, y, (txt or "")[:145])
            y -= line_h

        def wrap_text(txt: str, width_chars: int = 118) -> List[str]:
            s = _clean_inline_text(txt, 4000)
            if not s:
                return ["—"]
            words = s.split()
            lines: List[str] = []
            cur = ""
            for w in words:
                nxt = w if not cur else f"{cur} {w}"
                if len(nxt) <= width_chars:
                    cur = nxt
                else:
                    if cur:
                        lines.append(cur)
                    cur = w
            if cur:
                lines.append(cur)
            return lines or ["—"]

        def draw_wrapped(label: str, value: str, indent: int = 0, max_lines: int = 6) -> None:
            prefix = (" " * indent) + (label if label else "")
            lines = wrap_text(value)
            if prefix:
                if lines:
                    draw_line(prefix + lines[0])
                    for ln in lines[1:max_lines]:
                        draw_line((" " * (indent + len(label))) + ln)
                else:
                    draw_line(prefix + "—")
            else:
                for ln in lines[:max_lines]:
                    draw_line((" " * indent) + ln)

        def draw_section(title: str) -> None:
            draw_line("")
            draw_line(title, "Helvetica-Bold", 12)

        draw_line("Relatório Vivo de Monitoramento de Transmissão", "Helvetica-Bold", 15)
        draw_line(f"Última atualização (UTC): {payload.get('generated_at_utc') or '—'}")

        draw_section("Cabeçalho do evento")
        draw_line(f"Partida: {event.get('match_display') or event.get('title') or '—'}")
        draw_line(f"Competição: {event.get('competition') or '—'}")
        draw_line(f"Canal: {event.get('channel') or '—'}")
        draw_line(f"Status do evento: {event.get('status') or '—'}")
        draw_line(f"Tempo monitorado: {current.get('session_last_t_pretty') or summary.get('session_last_t_pretty') or '—'}")
        draw_line(f"Fase atual: {current.get('current_phase_pretty') or '—'}")
        draw_line(f"Contexto atual: {current.get('current_context_pretty') or '—'}")
        draw_line(f"Placar atual: {current.get('current_score') or '—'}")
        draw_line(f"Clock atual: {current.get('current_clock') or '—'}")

        draw_section("Resumo atual da transmissão")
        draw_wrapped("", summary.get("editorial_summary") or "—", max_lines=8)
        draw_line(f"Banner principal: {summary.get('banner_headline') or '—'}")

        draw_section("Histórico do evento")
        history = summary.get("event_history") or []
        if not history:
            draw_line("Nenhum fato relevante acumulado até o momento.")
        else:
            for item in history[-40:]:
                detail = item.get("detail") or item.get("label") or "—"
                draw_wrapped(f"- {item.get('t_pretty') or '—'} — ", detail, max_lines=3)

        draw_section("Banners capturados")
        banners = summary.get("banners") or []
        if not banners:
            draw_line("Nenhum banner relevante capturado.")
        else:
            for b in banners[-35:]:
                meta = f"{b.get('t_pretty') or '—'} | {b.get('kind') or '—'} | {b.get('context') or '—'}"
                draw_wrapped(f"- {meta} | ", b.get("text") or "—", max_lines=3)

        draw_section("Leituras confirmadas do HUD")
        hud = summary.get("hud_history") or []
        if not hud:
            draw_line("Nenhuma leitura confirmada do HUD.")
        else:
            for h in hud[-25:]:
                draw_line(
                    f"- {h.get('t_pretty') or '—'} | score={h.get('score') or '—'} | "
                    f"clock={h.get('clock') or '—'} | fase={h.get('phase') or '—'}"
                )

        draw_section("Interrupções técnicas")
        interruptions = summary.get("interruptions") or []
        if not interruptions:
            draw_line("Nenhuma interrupção detectada.")
        else:
            for it in interruptions[-20:]:
                draw_line(
                    f"- {it.get('label_pretty') or it.get('label') or '—'} | "
                    f"início={_fmt_seconds(it.get('start_t_seconds'))} | "
                    f"fim={_fmt_seconds(it.get('end_t_seconds')) if it.get('end_t_seconds') is not None else '—'} | "
                    f"duração={it.get('duration_pretty') or '—'}"
                )

        c.save()

    def write_ad_report(self, video_path: str, results: List[Dict[str, Any]]) -> str:
        """
        Gera um relatório PDF específico para a análise de anúncios de um vídeo.
        """
        file_name = os.path.basename(video_path)
        safe_name = _safe_filename(file_name)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"ads_{safe_name}_{timestamp}.pdf"
        pdf_path = os.path.join(self.reports_dir, report_name)
        
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        y = height - 50
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y, "Relatório de Detecção de Comerciais e Merchandising")
        y -= 30
        
        c.setFont("Helvetica", 10)
        c.drawString(40, y, f"Arquivo Original: {file_name}")
        y -= 15
        c.drawString(40, y, f"Data da Análise: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        y -= 30
        
        if not results:
            c.setFont("Helvetica", 12)
            c.drawString(40, y, "Nenhum anúncio ou comercial detectado.")
        else:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(40, y, "Itens Detectados no Vídeo:")
            y -= 25
            
            for res in results:
                if y < 100: # Nova página
                    c.showPage()
                    y = height - 50
                    c.setFont("Helvetica-Bold", 12)
                
                tipo = str(res.get("tipo", "Desconhecido")).upper()
                marca = str(res.get("marca", "—"))
                ts = str(res.get("timestamp", "—"))
                desc = str(res.get("descricao", ""))
                conf_val = res.get("confianca", 0)
                try:
                    conf = int(float(conf_val or 0) * 100)
                except:
                    conf = 0
                
                # Linha de cabeçalho do item
                c.setFont("Helvetica-Bold", 11)
                c.drawString(40, y, f"[{ts}] {tipo} - {marca} ({conf}% confianca)")
                y -= 14
                
                # Descrição com wrap
                c.setFont("Helvetica", 10)
                words = desc.split()
                line = ""
                for word in words:
                    # Largura aproximada de 80 caracteres
                    if len(line + " " + word) < 95:
                        line += " " + word
                    else:
                        c.drawString(55, y, line.strip())
                        y -= 12
                        line = word
                if line:
                    c.drawString(55, y, line.strip())
                
                y -= 18
                c.setDash(1, 2)
                c.line(40, y, width - 40, y)
                c.setDash()
                y -= 15
        
        c.save()
        return pdf_path

    def get_expert_report_text(self, results: List[Dict[str, Any]], prefs: Dict[str, bool] = None) -> str:
        """Gera uma versão em texto simples do relatório expert para logs e colagem."""
        if prefs is None:
            prefs = {"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}
            
        lines = []
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        lines.append("="*60)
        lines.append("Relatório Consolidado de Cronologia Técnica (Expert)")
        lines.append(f"Data de Emissão: {now_str}")
        lines.append("="*60)
        
        for res in results:
            m_display = res.get("match_display") or res.get("match_id", "Evento Desconhecido")
            m_comp = res.get("competition", "—")
            m_conf = float(res.get("confidence_score") or 0.0)
            m_date = res.get("date", "—")
            m_platform = res.get("platform") or "Não Informada"
            
            lines.append(f"\nEVENTO: {m_display}")
            lines.append(f"Data da Partida: {m_date} | Competição: {m_comp} | Plataforma: {m_platform} | Confiança: {m_conf*100:.1f}%")
            
            st1 = res.get("stoppage_time_1t")
            st2 = res.get("stoppage_time_2t")
            if (st1 or st2) and prefs.get("show_chrono", True):
                st_parts = []
                if st1: st_parts.append(f"1T (+{st1}')")
                if st2: st_parts.append(f"2T (+{st2}')")
                lines.append(f"Acréscimos Detectados: {' | '.join(st_parts)}")
            
            lines.append("\nCRONOLOGIA COMPLETA E AUDITADA:")
            
            def get_sec(t_str):
                if not t_str or t_str == "N/A": return None
                m = re.match(r"^(\d+):(\d+)(?::(\d+))?", str(t_str).strip())
                if m:
                    return int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                return None

            to_render = []
            seen_labels = set()
            if prefs.get("show_chrono", True):
                fh_start_sec = get_sec(res.get("first_half_start"))
                sh_start_sec = get_sec(res.get("second_half_start"))

                chrono_map = [
                    ("pre_game_start", "INÍCIO PRÉ-JOGO / TRANSMISSÃO", -10),
                    ("match_start", "INÍCIO", -5),
                    ("first_half_start", "APITO INICIAL (1T)", 0),
                    ("half_time_start", "FIM DO 1º TEMPO", 45),
                    ("half_time_end", "VOLTA INTERVALO", 45),
                    ("second_half_start", "APITO INICIAL (2T)", 45),
                    ("match_end", "APITO FINAL", 90),
                    ("post_game_end", "ENCERRAMENTO", 120)
                ]
                for key, lbl, def_min in chrono_map:
                    val = res.get(key)
                    if val and val != "N/A":
                        dyn_min = def_min
                        val_sec = get_sec(val)
                        if val_sec is not None:
                            if key == "half_time_start" and fh_start_sec is not None:
                                diff = val_sec - fh_start_sec
                                if diff < -43200: diff += 86400
                                dyn_min = round(diff / 60.0)
                            elif key == "match_end" and sh_start_sec is not None:
                                diff = val_sec - sh_start_sec
                                if diff < -43200: diff += 86400
                                dyn_min = 45 + round(diff / 60.0)
                            elif key == "post_game_end" and sh_start_sec is not None:
                                diff = val_sec - sh_start_sec
                                if diff < -43200: diff += 86400
                                dyn_min = 45 + round(diff / 60.0)

                        # We also include 'min' in to_render for text report if we want to show it.
                        to_render.append({"min": dyn_min, "lbl": lbl, "clock": val, "txt": f"{lbl} detectado via Auditoria IA.", "conf": m_conf})
                        seen_labels.add(lbl)
            
            for m in res.get("technical_milestones", []):
                lab = str(m.get("type", "EVENTO")).upper()
                is_milestone = any(k in lab for k in ["GOL", "CARTÃO", "SUBSTITU", "PENAL"])
                is_secondary = any(k in lab for k in ["VAR", "CHANCE", "TRAVE", "SUBST", "INTERRUP"])
                
                if is_milestone and not prefs.get("show_milestones", True): continue
                if is_secondary and not is_milestone and not prefs.get("show_secondary", True): continue
                
                # Deduplicação
                if lab in seen_labels and lab in ("APITO FINAL", "INÍCIO TRANSMISSÃO", "INÍCIO", "ENCERRAMENTO"): continue
                
                to_render.append({"lbl": lab, "clock": str(m.get("time") or ""), "txt": m.get("event"), "conf": m.get("confidence") or m_conf})
            
            # Ordenação básica por horário
            def sort_key(x):
                clk = str(x.get("clock", "")).strip()
                m = re.match(r"^(\d+):(\d+)", clk)
                if m: return int(m.group(1))*60 + int(m.group(2))
                return 9999
            
            to_render.sort(key=sort_key)
            
            for item in to_render:
                clk = item["clock"] if item["clock"] else "--:--"
                try: m_min = int(item.get("min", 0))
                except: m_min = 0
                show_min = m_min > 0 or any(k in item.get("lbl", "").upper() for k in ["GOL", "CARTÃO", "VAR", "SUBSTI", "PENAL"])
                min_lbl = f" - {m_min}'" if show_min else ""
                
                conf_pct = int(float(item["conf"]) * 100)
                lines.append(f"[{clk}{min_lbl}] {item['lbl']} (IA: {conf_pct}% conf.)")
                lines.append(f"   {item['txt']}")
                
            # Fontes
            if prefs.get("show_sources", True):
                sources = res.get("sources", [])
                if sources:
                    lines.append("\nFONTES DE PESQUISA (GROUNDING):")
                    for s in sources:
                        lines.append(f" • {s.get('title', 'Fonte')}: {s.get('uri', '—')}")
            
            lines.append("\n" + "-"*40)
            
        return "\n".join(lines)

    def write_expert_report(self, results: List[Dict[str, Any]], prefs: Dict[str, bool] = None) -> str:
        """
        Gera um relatório PDF consolidado para múltiplas análises Expert (cronologia)
        E também salva um JSON para histórico na GUI.
        """
        if prefs is None:
            prefs = {"show_chrono": True, "show_milestones": True, "show_secondary": True, "show_sources": True}
        # Tentar gerar um nome descritivo baseado no primeiro resultado
        base_name = "expert_batch"
        if results:
            res0 = results[0]
            channel = _safe_filename(str(res0.get("platform") or "monitor")).lower()
            comp = _safe_filename(str(res0.get("competition") or "comp")).lower()
            match = _safe_filename(str(res0.get("match_display") or "match")).lower()
            # Limpar data (ex: 01/04/2026 -> 01042026)
            date_raw = str(res0.get("date") or "").replace("/", "").replace("-", "")
            date_str = _safe_filename(date_raw) if date_raw else "date"
            
            base_name = f"expert_{channel}_{comp}_{match}_{date_str}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_name = f"{base_name}_{timestamp}.pdf"
        pdf_path = os.path.join(self.reports_dir, report_name)
        json_path = os.path.join(self.reports_dir, f"{base_name}_{timestamp}.json")
        
        # Salvar JSON para histórico
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({"expert_results": results, "generated_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        y = height - 50
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y, "Relatório Consolidado de Cronologia Técnica (Expert)")
        y -= 20
        c.setFont("Helvetica", 10)
        c.drawString(40, y, f"Data de Emissão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        y -= 40
        
        for res in results:
            if y < 200:
                c.showPage()
                y = height - 50
            
            m_display = str(res.get("match_display") or res.get("match_id", "Evento Desconhecido")).strip().lstrip(":").strip()
            m_comp = res.get("competition", "—")
            m_conf = float(res.get("confidence_score") or 0.0)
            
            m_date = res.get("date", "—")
            
            c.setFont("Helvetica-Bold", 14)
            c.drawString(40, y, f"EVENTO: {m_display}")
            y -= 18
            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y, f"Data da Partida: {m_date}")
            m_platform = res.get("platform") or "Não Informada"
            c.drawString(200, y, f"Plataforma: {m_platform}")
            c.drawString(380, y, f"Confiança da IA: {m_conf*100:.1f}%")
            y -= 15
            c.drawString(40, y, f"Competição: {m_comp}")
            y -= 18
            
            st1 = res.get("stoppage_time_1t")
            st2 = res.get("stoppage_time_2t")
            if (st1 or st2) and prefs.get("show_chrono", True):
                c.setFont("Helvetica", 10)
                st_parts = []
                if st1: st_parts.append(f"1T (+{st1}')")
                if st2: st_parts.append(f"2T (+{st2}')")
                c.drawString(40, y, f"Acréscimos Detectados: {' | '.join(st_parts)}")
                y -= 15
            
            y -= 10
            
            # --- Reconstruir e Ordenar Marcos (mesma lógica da GUI) ---
            to_render = []
            seen_labels = set()
            total_duration_min = 120
            if res.get("duration"):
                try:
                    total_duration_min = int(float(res.get("duration"))) // 60
                except: pass

            seen_clocks = set()
            if prefs.get("show_chrono", True):
                def get_sec(t_str):
                    if not t_str or t_str == "N/A": return None
                    m = re.match(r"^(\d+):(\d+)(?::(\d+))?", str(t_str).strip())
                    if m:
                        return int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                    return None

                fh_start_sec = get_sec(res.get("first_half_start"))
                sh_start_sec = get_sec(res.get("second_half_start"))

                chrono_map = [
                    ("pre_game_start", "INÍCIO PRÉ-JOGO / TRANSMISSÃO", -10),
                    ("first_half_start", "APITO INICIAL (1T)", 0),
                    ("half_time_start", "FIM DO 1º TEMPO", 45),
                    ("second_half_start", "APITO INICIAL (2T)", 45),
                    ("match_end", "APITO FINAL", 90),
                    ("post_game_end", "ENCERRAMENTO", total_duration_min)
                ]
                for key, lbl, def_min in chrono_map:
                    val = res.get(key)
                    if val and val != "N/A":
                        dyn_min = def_min
                        val_sec = get_sec(val)
                        if val_sec is not None:
                            if key == "half_time_start" and fh_start_sec is not None:
                                diff = val_sec - fh_start_sec
                                if diff < -43200: diff += 86400
                                dyn_min = round(diff / 60.0)
                            elif key == "match_end" and sh_start_sec is not None:
                                diff = val_sec - sh_start_sec
                                if diff < -43200: diff += 86400
                                dyn_min = 45 + round(diff / 60.0)
                            elif key == "post_game_end" and sh_start_sec is not None:
                                diff = val_sec - sh_start_sec
                                if diff < -43200: diff += 86400
                                dyn_min = 45 + round(diff / 60.0)

                        to_render.append({"min": dyn_min, "lbl": lbl, "clock": val, "txt": f"{lbl} detectado via Auditoria IA.", "conf": m_conf})
                        seen_labels.add(lbl)
                        seen_clocks.add(str(val))
            
            for m in res.get("technical_milestones", []):
                try: 
                    m_min = int(m.get("minute", 0))
                except: m_min = 0
                lab = str(m.get("type", "EVENTO")).upper()
                clk = str(m.get("time") or "")
                
                is_milestone = any(k in lab for k in ["GOL", "CARTÃO", "SUBSTITU", "PENAL"])
                is_secondary = any(k in lab for k in ["VAR", "CHANCE", "TRAVE", "SUBST", "INTERRUP"])
                
                if is_milestone and not prefs.get("show_milestones", True): continue
                if is_secondary and not is_milestone and not prefs.get("show_secondary", True): continue
                
                # Descartar marcos estruturais genéricos dos marcos técnicos pois o backbone do chrono_map já os renderiza!
                m_txt_upper = str(m.get("event") or "").upper()
                is_structural_generic = any(k in lab or k in m_txt_upper for k in [
                    "INÍCIO DE TEMPO", "FIM DE TEMPO", "INÍCIO DO 1", "INÍCIO DO 2",
                    "FIM DO 1", "FIM DO 2", "FIM DO SEGUNDO", "FIM DO PRIMEIRO",
                    "INÍCIO DA PARTIDA", "FIM DE JOGO", "VOLTA INTERVALO", "INÍCIO INTERVALO"
                ])
                if is_structural_generic:
                    continue

                if lab in seen_labels and lab in ("APITO FINAL", "INÍCIO TRANSMISSÃO", "INÍCIO", "ENCERRAMENTO", "FIM DO 1º TEMPO"): continue
                if "INTERRUPÇÃO TÉCNICA" in lab and clk in seen_clocks: continue
                
                to_render.append({"min": m_min, "lbl": lab, "clock": clk, "txt": m.get("event"), "conf": m.get("confidence") or m_conf})
                if lab in ("APITO FINAL", "INÍCIO TRANSMISSÃO", "INÍCIO", "ENCERRAMENTO", "FIM DO 1º TEMPO"):
                    seen_labels.add(lab)
            
            # Encontrar base_sec para suportar virada de meia-noite
            base_sec = None
            # Tentar encontrar o marco de início real primeiro
            for item in to_render:
                lbl = item.get("lbl", "").upper()
                if "INÍCIO" in lbl and "INTERVALO" not in lbl:
                    m = re.match(r"^(\d+):(\d+)(?::(\d+))?", str(item.get("clock", "")).strip())
                    if m:
                        base_sec = int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                        break
            
            # Se não achou início, pega o primeiro válido
            if base_sec is None:
                for item in to_render:
                    m = re.match(r"^(\d+):(\d+)(?::(\d+))?", str(item.get("clock", "")).strip())
                    if m:
                        base_sec = int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                        break

            def sort_key(x):
                lbl = x.get("lbl", "").upper()
                try:
                    m_min = int(x.get("min", 0))
                except:
                    m_min = 0
                
                # Prioridades para marcos no mesmo minuto/horário
                prio = 50
                if "INÍCIO TRANSMISSÃO" in lbl: prio = 0
                elif "INÍCIO" in lbl and "INTERVALO" not in lbl: prio = 1
                elif "APITO INICIAL (1T)" in lbl: prio = 2
                elif any(k in lbl for k in ["GOL", "CARTÃO", "VAR", "SUBSTI", "PENAL"]): prio = 5
                elif "ACRÉSCIMO" in lbl: prio = 8
                elif "INTERVALO" in lbl: prio = 10
                elif "VOLTA INTERVALO" in lbl: prio = 11
                elif "APITO INICIAL (2T)" in lbl: prio = 12
                elif "APITO FINAL" in lbl: prio = 90
                elif "ENCERRAMENTO" in lbl: prio = 100
                
                clk_str = str(x.get("clock", "")).strip()
                m = re.match(r"^(\d+):(\d+)(?::(\d+))?", clk_str)
                if m:
                    clk_sec = int(m.group(1))*3600 + int(m.group(2))*60 + (int(m.group(3)) if m.group(3) else 0)
                    if base_sec is not None and clk_sec < base_sec - 43200: # Virada de meia-noite
                        clk_sec += 86400
                    return (1, clk_sec, prio, m_min)
                
                return (0, m_min, prio, clk_str)

            
            to_render.sort(key=sort_key)
            
            # --- Trava de Segurança Cronológica (Guardrail) ---
            # Garante que APITO FINAL e ENCERRAMENTO fiquem ESTRITAMENTE DEPOIS de todos os gols/cartões do jogo
            last_game_event_idx = -1
            apito_idx = -1
            for idx_tr, item_tr in enumerate(to_render):
                lbl_tr = item_tr.get("lbl", "").upper()
                if any(k in lbl_tr for k in ["GOL", "CARTÃO", "VAR", "SUBSTI", "PENAL"]):
                    last_game_event_idx = idx_tr
                elif "APITO FINAL" in lbl_tr:
                    apito_idx = idx_tr

            if last_game_event_idx != -1 and apito_idx != -1 and apito_idx < last_game_event_idx:
                apito_item = to_render.pop(apito_idx)
                last_game_event_idx = max([i for i, item in enumerate(to_render) if any(k in item.get("lbl", "").upper() for k in ["GOL", "CARTÃO", "VAR", "SUBSTI", "PENAL"])], default=-1)
                to_render.insert(last_game_event_idx + 1, apito_item)

            enc_indices = [i for i, item in enumerate(to_render) if "ENCERRAMENTO" in item.get("lbl", "").upper()]
            if enc_indices:
                enc_item = to_render.pop(enc_indices[0])
                to_render.append(enc_item)
            
            # --- Imprimir Marcos ---
            c.setFont("Helvetica-Bold", 11)
            c.drawString(40, y, "CRONOLOGIA COMPLETA E AUDITADA:")
            y -= 20
            
            for item in to_render:
                if y < 80:
                    c.showPage()
                    y = height - 50
                
                clk = item["clock"] if (item["clock"] and item["clock"] != "N/A") else "--:--"
                try:
                    m_min = int(item.get("min", 0))
                except:
                    m_min = 0
                
                # Formata como [HH:MM - 15'] se tiver minuto, senão apenas [HH:MM]
                # Mostra o minuto se for > 0 ou se o label indicar um evento de jogo
                show_min = m_min > 0 or any(k in item.get("lbl", "").upper() for k in ["GOL", "CARTÃO", "VAR", "SUBSTI", "PENAL"])
                min_lbl = f" - {m_min}'" if show_min else ""
                time_label = f"[{clk}{min_lbl}]"
                
                conf_pct = int(float(item["conf"]) * 100)
                
                c.setFont("Helvetica-Bold", 10)
                c.drawString(50, y, f"{time_label} {item['lbl']} (IA: {conf_pct}% conf.)")
                y -= 14
                
                # Descrição
                c.setFont("Helvetica", 9)
                txt = str(item["txt"] or "N/A")
                words = txt.split()
                line = ""
                for word in words:
                    if len(line + " " + word) < 100: line += " " + word
                    else:
                        c.drawString(65, y, line.strip())
                        y -= 11
                        line = word
                if line:
                    c.drawString(65, y, line.strip())
                
                y -= 18
                c.setDash(1, 2)
                c.line(50, y, width - 50, y)
                c.setDash()
                y -= 15
            
            # --- Marcos de Transcrição Detectados (Nacionais/Locais) ---
            t_events = res.get("transcript_events", [])
            if t_events:
                if y < 150:
                    c.showPage()
                    y = height - 50
                
                c.setFont("Helvetica-Bold", 11)
                c.drawString(40, y, "RESUMO DE DIÁLOGOS/TRANSCRIÇÃO DETECTADOS (NARRADOR):")
                y -= 20
                
                for ev in t_events:
                    if y < 80:
                        c.showPage()
                        y = height - 50
                    
                    v_time = ev.get("video_time", "--:--")
                    r_time = ev.get("real_time", "--:--:--")
                    narr = ev.get("narration", "")
                    analysis = ev.get("analysis", "")
                    
                    c.setFont("Helvetica-Bold", 9)
                    c.drawString(50, y, f"[{v_time}] Relógio Real: {r_time} | {narr}")
                    y -= 12
                    c.setFont("Helvetica-Oblique", 8)
                    c.setFillColorRGB(0.3, 0.3, 0.3)
                    
                    # Wrappar a análise em linhas se for muito longa
                    words = str(analysis).split()
                    line = ""
                    for word in words:
                        if len(line + " " + word) < 110:
                            line += " " + word
                        else:
                            c.drawString(65, y, line.strip())
                            y -= 10
                            line = word
                    if line:
                        c.drawString(65, y, line.strip())
                    
                    c.setFillColorRGB(0, 0, 0)
                    y -= 16
                
                y -= 15
            
            y -= 30
            
            # --- Fontes de Pesquisa (Grounding) ---
            if prefs.get("show_sources", True):
                sources = res.get("sources", [])
                if sources:
                    if y < 150:
                        c.showPage()
                        y = height - 50
                    
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(40, y, "FONTES DE PESQUISA (GROUNDING):")
                    y -= 20
                    
                    for s in sources:
                        if y < 80:
                            c.showPage()
                            y = height - 50
                        
                        c.setFont("Helvetica-Bold", 9)
                        c.drawString(50, y, f"• {s.get('title', 'Fonte')}")
                        y -= 12
                        c.setFont("Helvetica", 8)
                        c.setFillColorRGB(0, 0, 1) # Azul para link
                        c.drawString(60, y, str(s.get('uri', '—')))
                        c.setFillColorRGB(0, 0, 0) # Volta pro preto
                        y -= 18
            
            y -= 30
            
        c.save()
        try:
            from modules.sharepoint_reporter import SharePointReporter
            res0 = results[0] if results else {}
            partida = str(res0.get("match_display") or res0.get("match_id") or "Partida").strip()
            comp = str(res0.get("competition") or "Brasileiro Serie A").strip()
            plat = str(res0.get("platform") or "Amazon Prime").strip()
            conf = f"{float(res0.get('confidence_score') or 99.0):.1f}%"
            SharePointReporter.sync_pdf_to_sharepoint(pdf_path, partida, comp, plat, confianca=conf)
        except Exception as e_sp:
            pass
        return pdf_path


# ============================================================
# FINAL LIVE REPORT SUMMARY PATCH
# ============================================================
_old_rg_summarize_final = ReportGenerator._summarize

def _rg_summarize_with_bootstrap(self, timeline: List[Dict[str, Any]], notes: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(_old_rg_summarize_final(self, timeline, notes) or {})
    try:
        current = dict(summary.get('current_state') or {})
        current_phase = current.get('current_phase') or notes.get('current_phase') or 'pre_jogo'
        current_context = current.get('current_context') or notes.get('current_context') or 'pre_jogo_countdown'
        current.setdefault('current_phase', current_phase)
        current.setdefault('current_phase_pretty', _phase_label(current_phase))
        current.setdefault('current_context', current_context)
        current.setdefault('current_context_pretty', _context_label(current_context))
        current.setdefault('current_context_summary', _clean_inline_text(notes.get('current_context_summary') or '', 220) or 'Monitoramento iniciado em pré-jogo.')
        summary['current_state'] = current

        history = list(summary.get('event_history') or [])
        if not any(str(x.get('label') or '').upper() == 'PRE_JOGO_START' for x in history):
            history.insert(0, {
                't_seconds': 0.0,
                't_pretty': '00:00',
                'type': 'phase',
                'label': 'PRE_JOGO_START',
                'detail': 'Sessão iniciada em Pré-jogo',
                'importance': 3,
            })
        summary['event_history'] = sorted(history, key=lambda x: x.get('t_seconds', 0.0))[-80:]

        editorial = str(summary.get('editorial_summary') or '').strip()
        boot = 'A sessão foi iniciada em pré-jogo para preservar banners e contexto desde o começo da transmissão.'
        if boot not in editorial:
            summary['editorial_summary'] = (boot + ' ' + editorial).strip()
    except Exception:
        pass
    return summary

ReportGenerator._summarize = _rg_summarize_with_bootstrap
