# modules/narration_chronology.py
"""
Transforma a narração transcrita de uma live (muitas vezes narração em ESTÚDIO)
no mesmo formato de resultado usado pelo relatório Expert (write_expert_report).

Fontes:
- Narração completa (.txt com [tempo no vídeo | horário real]).
- Pesquisa no Gemini Web (navegador logado) para os dados oficiais do jogo.
- Gemini API para cruzar tudo e devolver JSON estruturado.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from modules.narration_transcriber import gemini_generate_text, read_narration_body, fmt_hms

MAX_NARRATION_CHARS = 600_000


def guess_match_from_title(title: str) -> Dict[str, str]:
    """Extrai 'Time A x Time B' e competição de títulos como 'AO VIVO: ATHLETICO X VASCO | BRASILEIRÃO 2026 | 34ª RODADA'."""
    t = re.sub(r"(?i)^\s*(ao vivo|live|narra[cç][aã]o|pr[eé]-jogo|p[oó]s-jogo)[^:]*:\s*", "", title or "").strip()
    parts = [p.strip() for p in re.split(r"\s*[|•\-–]\s+", t) if p.strip()]
    team1 = team2 = comp = ""
    for i, p in enumerate(parts):
        m = re.search(r"(.+?)\s+(?:x|vs\.?|versus)\s+(.+)", p, re.IGNORECASE)
        if m and not team1:
            team1, team2 = m.group(1).strip(" :"), m.group(2).strip(" :")
            rest = parts[i + 1:]
            if rest:
                comp = rest[0]
            break

    def nice(s: str) -> str:
        return " ".join(w.capitalize() if w.isupper() or w.islower() else w for w in s.split())

    comp = re.sub(r"\s*\d{2}/\d{2}$", "", comp)
    return {"team1": nice(team1), "team2": nice(team2), "competition": nice(comp)}


def build_web_query(meta: Dict[str, Any], event: Dict[str, Any]) -> str:
    from modules.web_verdict_collector import human_date

    t1, t2 = meta.get("team1", ""), meta.get("team2", "")
    comp = meta.get("competition", "")
    date = meta.get("date", "")
    jogo = f"{t1} x {t2}" if t1 and t2 else event.get("title", "")
    try:
        d_h = human_date(date) if date else date
    except Exception:
        d_h = date
    return (
        f"Pesquise na súmula oficial e na cobertura minuto a minuto (GE, Lance!, UOL, ESPN) o jogo {jogo}"
        f"{' pelo ' + comp if comp else ''}{' em ' + d_h if d_h else ''}. Informe em tópicos: placar final; "
        "horário oficial (Brasília) do início do 1º tempo, fim do 1º tempo, início do 2º tempo e apito final; "
        "acréscimos de cada tempo; todos os gols com minuto e autor; cartões; substituições; lances de VAR; "
        "estádio e arbitragem. Diga também se o canal "
        f"\"{event.get('channel_name', '')}\" transmitiu ou narrou essa partida no YouTube."
    )


def collect_web_info(meta: Dict[str, Any], event: Dict[str, Any], log: Callable[[str], None]) -> Dict[str, Any]:
    try:
        from modules.web_verdict_collector import ask_gemini_web
        log("🌐 Pesquisando informações oficiais do jogo no Gemini Web...")
        r = ask_gemini_web(build_web_query(meta, event), headless=True, timeout_s=150)
        if r.get("ok"):
            txt = re.sub(r"\*\*", "", r.get("text", ""))
            log("🌐 Gemini Web respondeu com sucesso.")
            return {"verdict_text": txt, "references": r.get("links", [])[:8], "source": "gemini_web"}
        log(f"⚠️ Gemini Web indisponível ({r.get('error') or 'sem resposta'}). Seguindo só com a narração.")
    except Exception as ex:  # noqa: BLE001
        log(f"⚠️ Gemini Web falhou: {str(ex)[:160]}")
    return {}


def _compact_narration(body: str) -> str:
    if len(body) <= MAX_NARRATION_CHARS:
        return body
    # Mantém início/fim integrais e amostra o meio para caber no contexto
    keep = MAX_NARRATION_CHARS // 2
    return body[:keep] + "\n[... trecho intermediário omitido por tamanho ...]\n" + body[-keep:]


PROMPT_TMPL = """Você é um auditor de transmissões esportivas. Abaixo está a TRANSCRIÇÃO COMPLETA de uma live do YouTube
do canal "{channel}" (título: "{title}"). Em muitos casos é uma NARRAÇÃO EM ESTÚDIO: o canal não exibe as imagens do jogo,
apenas narra/comenta. Por isso o horário do vídeo NÃO é necessariamente o horário oficial do jogo.

Cada linha da transcrição tem o formato [tempo no vídeo | horário real de Brasília] fala.
Início da live: {live_start} | Fim da live: {live_end} | Duração: {duration}

Dados informados para o jogo: {team1} x {team2} | Competição: {competition} | Data: {date}

INFORMAÇÕES OFICIAIS PESQUISADAS NA WEB (use como fonte prioritária para horários oficiais, placar e lances):
<<<WEB
{web}
WEB>>>

TRANSCRIÇÃO:
<<<NARRACAO
{narration}
NARRACAO>>>

Tarefa: monte a cronologia do jogo e da transmissão. Responda SOMENTE com um JSON válido neste formato:
{{
  "team1": "...", "team2": "...", "competition": "...", "date": "DD/MM/AAAA",
  "final_score": "2 x 1",
  "pre_game_start": "HH:MM:SS (horário real em que a live/pré-jogo começou)",
  "first_half_start": "HH:MM:SS", "half_time_start": "HH:MM:SS",
  "second_half_start": "HH:MM:SS", "match_end": "HH:MM:SS",
  "post_game_end": "HH:MM:SS (fim da live)",
  "stoppage_time_1t": 0, "stoppage_time_2t": 0,
  "times_source": "oficial_web | narracao | misto",
  "technical_milestones": [
    {{"minute": 12, "type": "GOL", "time": "HH:MM:SS", "event": "Descrição curta (autor, assistência, placar parcial)", "confidence": 0.9}}
  ],
  "transcript_events": [
    {{"video_time": "HH:MM:SS", "real_time": "HH:MM:SS", "narration": "frase-chave dita na narração", "analysis": "o que aconteceu / relevância"}}
  ],
  "broadcast_summary": "3-6 frases descrevendo a transmissão: tipo (estúdio, in loco, som ambiente), narrador/comentaristas citados, convidados, momentos marcantes.",
  "narration_type": "estudio | in_loco | som_ambiente | indefinido",
  "confidence_score": 0.0
}}
Regras:
- Horários do JOGO (first_half_start, half_time_start, second_half_start, match_end): prefira os oficiais da web; se ausentes, use o horário real da narração em que o narrador anuncia o apito e marque times_source="narracao".
- Em technical_milestones inclua gols, cartões, VAR, pênaltis, substituições relevantes e acréscimos; "time" = horário real (Brasília) em que o lance foi narrado.
- transcript_events: 10 a 30 momentos da TRANSMISSÃO (início da live, abertura, escalações, apitos narrados, gols narrados, intervalo, entrevistas, encerramento).
- Não invente lances que não estejam na web nem na narração. Use "N/A" quando não souber um horário."""


def _parse_json(text: str) -> Dict[str, Any]:
    t = text.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.MULTILINE).strip()
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"\{.*\}", t, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def generate_narration_chronology(event: Dict[str, Any], meta: Dict[str, Any], *, api_key: Any, model_id: str,
                                  log: Optional[Callable[[str], None]] = None, use_web: bool = True) -> Dict[str, Any]:
    """Retorna um dict compatível com ReportGenerator.write_expert_report (ou {'error': ...})."""
    log = log or (lambda m: print(f"[CRONOLOGIA NARRAÇÃO] {m}"))
    path = event.get("narration_path")
    if not path:
        return {"error": "Narração ainda não transcrita."}
    try:
        body = read_narration_body(path)
    except Exception as ex:  # noqa: BLE001
        return {"error": f"Não foi possível ler a narração: {ex}"}

    start = event.get("actual_start_epoch")
    dur = int(event.get("duration") or 0)
    live_start = datetime.fromtimestamp(start).strftime("%H:%M:%S") if start else "N/A"
    live_end = datetime.fromtimestamp(start + dur).strftime("%H:%M:%S") if (start and dur) else "N/A"
    live_date = datetime.fromtimestamp(start).strftime("%d/%m/%Y") if start else ""
    meta = dict(meta)
    meta.setdefault("date", live_date)
    if not meta.get("date"):
        meta["date"] = live_date

    web = collect_web_info(meta, event, log) if use_web else {}

    prompt = PROMPT_TMPL.format(
        channel=event.get("channel_name", ""), title=event.get("title", ""),
        live_start=live_start, live_end=live_end, duration=fmt_hms(dur) if dur else "N/A",
        team1=meta.get("team1") or "?", team2=meta.get("team2") or "?",
        competition=meta.get("competition") or "?", date=meta.get("date") or "?",
        web=(web.get("verdict_text") or "(pesquisa web indisponível)")[:20000],
        narration=_compact_narration(body),
    )
    log("🧠 Gemini analisando a narração completa e montando a cronologia...")
    try:
        raw = gemini_generate_text(api_key, model_id, [prompt], json_mode=True, log=log)
        data = _parse_json(raw)
    except Exception as ex:  # noqa: BLE001
        return {"error": f"Falha ao gerar cronologia: {ex}"}

    t1 = data.get("team1") or meta.get("team1") or "Time 1"
    t2 = data.get("team2") or meta.get("team2") or "Time 2"
    score = str(data.get("final_score") or "").strip()
    milestones: List[Dict[str, Any]] = []
    for m in data.get("technical_milestones") or []:
        if isinstance(m, dict) and (m.get("event") or m.get("type")):
            milestones.append(m)

    try:
        conf = float(data.get("confidence_score") or 0.0)
        conf = conf / 100.0 if conf > 1 else conf
    except Exception:
        conf = 0.0

    result: Dict[str, Any] = {
        "match_display": f"{t1} x {t2}" + (f" ({score})" if score else ""),
        "team1": t1, "team2": t2,
        "competition": data.get("competition") or meta.get("competition") or "—",
        "date": data.get("date") or meta.get("date") or live_date,
        "platform": event.get("channel_name") or "YouTube",
        "confidence_score": conf,
        "duration": dur or None,
        "live_start_time": live_start if start else None,
        "live_end_time": live_end if (start and dur) else None,
        "technical_milestones": milestones,
        "transcript_events": [e for e in (data.get("transcript_events") or []) if isinstance(e, dict)],
        "stoppage_time_1t": data.get("stoppage_time_1t") or None,
        "stoppage_time_2t": data.get("stoppage_time_2t") or None,
        "report_title": f"Relatório de Narração ({event.get('channel_name', 'YouTube')}) — Cronologia do Evento",
        "report_kind": "narration",
        "broadcast_info": {
            "channel_name": event.get("channel_name", ""),
            "channel_url": event.get("channel_url", ""),
            "video_title": event.get("title", ""),
            "video_url": event.get("url", ""),
            "live_start": datetime.fromtimestamp(start).strftime("%d/%m/%Y %H:%M:%S") if start else "N/D",
            "live_end": datetime.fromtimestamp(start + dur).strftime("%d/%m/%Y %H:%M:%S") if (start and dur) else "N/D",
            "duration": fmt_hms(dur) if dur else "N/D",
            "transcript_source": event.get("transcript_source_label") or event.get("transcript_source") or "",
            "narration_file": os.path.basename(path),
            "narration_type": data.get("narration_type") or "indefinido",
            "final_score": score,
            "times_source": data.get("times_source") or "",
            "summary": data.get("broadcast_summary") or "",
        },
    }
    for k in ("pre_game_start", "first_half_start", "half_time_start", "second_half_start", "match_end", "post_game_end"):
        v = str(data.get(k) or "").strip()
        if v and v.upper() != "N/A" and re.match(r"^\d{1,2}:\d{2}", v):
            result[k] = v[:8]
    if web:
        result["grounding_verdict"] = web
    log("✅ Cronologia da narração gerada.")
    return result
