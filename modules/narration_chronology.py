# modules/narration_chronology.py
"""
Análise inteligente de transcrição e geração de Cronologia Técnica a partir da
narração de uma live (estúdio/rádio/transmissão), no mesmo formato oficial do
relatório Expert (ReportGenerator.write_expert_report).

Fluxo:
1. analyze_narration_transcript(): analisa o .txt da transcrição para identificar:
   - Se foi realmente uma partida narrada em tempo real (is_match_narration: bool);
   - Times (team1, team2), competição, data, placar e equipe de transmissão;
   - Menções a marcas, patrocinadores, anúncios e merchandising durante a narração.
2. generate_narration_chronology(): cruza a narração com pesquisa no Gemini Web
   e Gemini API para montar a cronologia completa, marcas citadas e a análise
   final do Gemini no padrão oficial do sistema.
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
    """Extrai 'Time A x Time B' e competição de títulos como 'AO VIVO: ATHLETICO X VASCO | BRASILEIRÃO 2026'."""
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

    comp = re.sub(r"\s*\d{2}/\d{2}(?:/\d{2,4})?$", "", comp)
    return {"team1": nice(team1), "team2": nice(team2), "competition": nice(comp)}


def _compact_narration(body: str, limit: int = MAX_NARRATION_CHARS) -> str:
    if len(body) <= limit:
        return body
    keep = limit // 2
    return body[:keep] + "\n[... trecho intermediário omitido por tamanho ...]\n" + body[-keep:]


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


ANALYSIS_PROMPT_TMPL = """Você é um auditor especialista em transmissões esportivas e publicidade.
Analise a TRANSCRIÇÃO abaixo de uma live do canal "{channel}" (título: "{title}").
Início da live: {live_start} | Fim da live: {live_end} | Duração: {duration} | Data base: {live_date}

Cada linha da transcrição possui o formato: [tempo no vídeo | horário real de Brasília] fala.

TRANSCRIÇÃO:
<<<NARRACAO
{narration}
NARRACAO>>>

Sua tarefa é analisar o conteúdo real da transcrição e responder SOMENTE com um JSON válido no formato abaixo:
{{
  "is_match_narration": true,
  "event_category": "Partida Narrada ao Vivo | Programa de Debate / Concentração | Pré-Jogo / Pós-Jogo sem Partida | Noticiário / Entrevista",
  "classification_summary": "Explicação clara e direta (1 a 2 frases) dizendo se houve narração lance a lance de uma partida em tempo real ou se foi apenas debate/programa/concentração.",
  "team1": "Nome do Time Mandante (ou vazio se não for jogo)",
  "team2": "Nome do Time Visitante (ou vazio se não for jogo)",
  "competition": "Nome da Competição (ex: Brasileirão Série A, Copa do Brasil, Libertadores, Gauchão, etc.)",
  "date": "DD/MM/AAAA",
  "detected_score": "Placar final identificado na narração (ex: 2 x 1) ou vazio",
  "narrator_info": "Nomes do narrador, comentaristas e repórteres identificados na transmissão",
  "brands_summary": "Resumo consolidado de todas as marcas, patrocinadores, casas de apostas e anúncios mencionados durante a transmissão (ou 'Nenhuma menção comercial identificada').",
  "brand_mentions": [
    {{
      "brand": "Nome da Marca / Anunciante (ex: KTO, Banrisul, Betano, Supermercados Guanabara, Ipiranga, etc.)",
      "video_time": "HH:MM:SS",
      "real_time": "HH:MM:SS",
      "type": "Merchan / Patrocínio / Vinheta Comercial / Citação",
      "quote": "Trecho ou descrição do anúncio/menção feita pelo narrador ou comentarista"
    }}
  ]
}}

Regras críticas de classificação:
1. "is_match_narration" DEVE ser true SOMENTE se a transmissão contiver a narração de uma partida de futebol acontecendo em tempo real (com bola rolando, 1º tempo, 2º tempo, lances narrados minuto a minuto, mesmo que narrado de um estúdio/rádio).
2. Se for um programa de debate, live direto da concentração, mesa redonda, entrevista coletiva ou pré-jogo isolado que encerrou antes do jogo começar (como "Baldasso Night Show", "Bate-Bola", "Direto da Concentração", etc.), "is_match_narration" DEVE ser false!
3. Identifique TODAS as menções a marcas, patrocinadores, leituras de testemunhais (merchan), anúncios, ofertas, PIX/QR Code patrocinado e apoios comerciais falados durante a transmissão em "brand_mentions"."""


def analyze_narration_transcript(
    event: Dict[str, Any],
    *,
    api_key: Any,
    model_id: str = "gemini-2.5-flash",
    log: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """
    Analisa a transcrição recém-gerada para descobrir automaticamente:
    1) Se foi mesmo uma partida narrada em tempo real (is_match_narration);
    2) Quais os times (team1, team2), competição, data e placar;
    3) Quais marcas, patrocínios e anúncios foram mencionados durante a narração.
    """
    log = log or (lambda m: print(f"[ANÁLISE TRANSCRIÇÃO] {m}"))
    path = event.get("narration_path")
    if not path or not os.path.exists(path):
        return {"ok": False, "error": "Arquivo de transcrição não encontrado."}

    try:
        body = read_narration_body(path)
    except Exception as ex:
        return {"ok": False, "error": f"Erro ao ler transcrição: {ex}"}

    start = event.get("actual_start_epoch") or event.get("scheduled_epoch")
    dur = int(event.get("duration") or 0)
    live_start = datetime.fromtimestamp(start).strftime("%H:%M:%S") if start else "N/A"
    live_end = datetime.fromtimestamp(start + dur).strftime("%H:%M:%S") if (start and dur) else "N/A"
    live_date = datetime.fromtimestamp(start).strftime("%d/%m/%Y") if start else datetime.now().strftime("%d/%m/%Y")

    prompt = ANALYSIS_PROMPT_TMPL.format(
        channel=event.get("channel_name", "YouTube"),
        title=event.get("title", ""),
        live_start=live_start,
        live_end=live_end,
        duration=fmt_hms(dur) if dur else "N/A",
        live_date=live_date,
        narration=_compact_narration(body, limit=400_000),
    )

    log("🔍 Analisando transcrição com IA (verificando partida narrada, times e menções de marcas)...")
    try:
        raw = gemini_generate_text(api_key, model_id, [prompt], json_mode=True, log=log)
        data = _parse_json(raw)
    except Exception as ex:
        log(f"⚠️ Falha na análise inteligente da transcrição: {ex}")
        # Fallback por título caso a API oscile
        guessed = guess_match_from_title(event.get("title", ""))
        has_vs = bool(guessed.get("team1") and guessed.get("team2"))
        return {
            "ok": True,
            "is_match_narration": has_vs,
            "event_category": "Partida Narrada ao Vivo" if has_vs else "Programa / Transmissão",
            "classification_summary": (
                f"Partida identificada pelo título: {guessed.get('team1')} x {guessed.get('team2')}"
                if has_vs else "Não foi identificada uma partida narrada em tempo real no título."
            ),
            "team1": guessed.get("team1", ""),
            "team2": guessed.get("team2", ""),
            "competition": guessed.get("competition", "Brasileirão Série A"),
            "date": live_date,
            "detected_score": "",
            "narrator_info": "",
            "brands_summary": "",
            "brand_mentions": [],
        }

    guessed = guess_match_from_title(event.get("title", ""))
    is_match = bool(data.get("is_match_narration"))
    t1 = str(data.get("team1") or guessed.get("team1") or "").strip()
    t2 = str(data.get("team2") or guessed.get("team2") or "").strip()
    comp = str(data.get("competition") or guessed.get("competition") or "Brasileirão Série A").strip()
    dt = str(data.get("date") or live_date).strip()
    if not re.match(r"^\d{2}/\d{2}/\d{4}$", dt):
        dt = live_date

    b_mentions = [bm for bm in (data.get("brand_mentions") or []) if isinstance(bm, dict)]
    b_summary = str(data.get("brands_summary") or "").strip()
    if b_mentions and not b_summary:
        unique_brands = []
        for bm in b_mentions:
            bn = str(bm.get("brand") or "").strip()
            if bn and bn not in unique_brands:
                unique_brands.append(bn)
        if unique_brands:
            b_summary = f"{len(b_mentions)} menções comerciais identificadas ({', '.join(unique_brands[:10])})."

    return {
        "ok": True,
        "is_match_narration": is_match,
        "event_category": str(data.get("event_category") or ("Partida Narrada ao Vivo" if is_match else "Programa / Debate")).strip(),
        "classification_summary": str(data.get("classification_summary") or "").strip(),
        "team1": t1,
        "team2": t2,
        "competition": comp,
        "date": dt,
        "detected_score": str(data.get("detected_score") or "").strip(),
        "narrator_info": str(data.get("narrator_info") or "").strip(),
        "brands_summary": b_summary,
        "brand_mentions": b_mentions,
    }


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
        f"{' pelo ' + comp if comp else ''}{' em ' + d_h if d_h else ''}. Informe detalhadamente em tópicos: "
        "placar final; horário oficial (Brasília) do início do 1º tempo, fim do 1º tempo, início do 2º tempo e apito final; "
        "acréscimos de cada tempo; todos os gols com minuto, tempo (1ºT/2ºT) e autor; cartões amarelos e vermelhos; "
        "substituições; lances de VAR; estádio e arbitragem. Diga também se o canal "
        f"\"{event.get('channel_name', '')}\" realizou transmissão/narração dessa partida no YouTube."
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
        log(f"⚠️ Gemini Web indisponível ({r.get('error') or 'sem resposta'}). Complementando com análise direta do Gemini.")
    except Exception as ex:  # noqa: BLE001
        log(f"⚠️ Gemini Web falhou: {str(ex)[:160]}")
    return {}


PROMPT_TMPL = """Você é um auditor sênior de transmissões esportivas e publicidade. Abaixo está a TRANSCRIÇÃO COMPLETA de uma live do YouTube
do canal "{channel}" (título: "{title}"). Em muitos casos é uma NARRAÇÃO EM ESTÚDIO (rádio/webtv): o canal não exibe as imagens do jogo,
apenas narra e comenta lance a lance.

Cada linha da transcrição tem o formato [tempo no vídeo | horário real de Brasília] fala.
Início da live: {live_start} | Fim da live: {live_end} | Duração: {duration}

Dados identificados do jogo: {team1} x {team2} | Competição: {competition} | Data: {date}

INFORMAÇÕES OFICIAIS PESQUISADAS NA WEB (use como fonte prioritária para horários oficiais, placar, gols, cartões e substituições):
<<<WEB
{web}
WEB>>>

TRANSCRIÇÃO DA NARRAÇÃO:
<<<NARRACAO
{narration}
NARRACAO>>>

Tarefa: monte a cronologia técnica completa do jogo, identifique todas as menções comerciais/marcas durante a narração e elabore a análise técnica final do Gemini.
Responda SOMENTE com um JSON válido neste formato:
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
    {{"minute": 12, "type": "GOL", "time": "HH:MM:SS", "event": "Descrição completa (autor, time, assistência, placar parcial)", "confidence": 0.98}}
  ],
  "transcript_events": [
    {{"video_time": "HH:MM:SS", "real_time": "HH:MM:SS", "narration": "frase-chave dita na narração", "analysis": "o que aconteceu / relevância"}}
  ],
  "brands_summary": "Resumo executivo de todas as marcas, patrocinadores e anúncios citados durante a narração.",
  "brand_mentions": [
    {{"brand": "Nome da Marca", "video_time": "HH:MM:SS", "real_time": "HH:MM:SS", "type": "Merchan / Patrocínio / Anúncio", "quote": "O que foi anunciado pelo narrador/equipe"}}
  ],
  "broadcast_summary": "3-6 frases descrevendo a transmissão: tipo (estúdio, in loco, som ambiente), narrador/comentaristas citados, convidados, momentos marcantes.",
  "gemini_final_analysis": "Texto completo em múltiplos parágrafos e tópicos (com marcadores •) no padrão de Confirmação Oficial & Análise Técnica do Gemini: 1) Resumo da Partida e Placar Oficial; 2) Confirmação dos Horários Oficiais (Início 1ºT, Fim 1ºT, Início 2ºT, Apito Final e Acréscimos); 3) Detalhamento dos Gols, Cartões e Substituições; 4) Avaliação da Transmissão do Canal (equipe, jornada esportiva); 5) Relatório de Inserções Comerciais e Marcas Mencionadas durante a Narração.",
  "narration_type": "estudio | in_loco | som_ambiente | indefinido",
  "confidence_score": 0.98
}}
Regras:
- Horários do JOGO (first_half_start, half_time_start, second_half_start, match_end): prefira os horários oficiais da web; se ausentes, use o horário real da narração em que o narrador anuncia o apito inicial/final.
- Em technical_milestones inclua TODOS os gols, cartões amarelos/vermelhos, intervenções do VAR, pênaltis, substituições e acréscimos; "time" = horário real (Brasília).
- Em brand_mentions liste TODAS as menções a marcas, patrocinadores, casas de apostas, bancos, supermercados e anúncios feitos durante a narração com o horário no vídeo e horário real.
- Em gemini_final_analysis escreva uma análise completa, rica e estruturada em tópicos (•) para constar no fechamento do relatório PDF."""


def generate_narration_chronology(
    event: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
    *,
    api_key: Any,
    model_id: str = "gemini-2.5-flash",
    log: Optional[Callable[[str], None]] = None,
    use_web: bool = True,
) -> Dict[str, Any]:
    """Retorna um dict compatível com ReportGenerator.write_expert_report (ou {'error': ...})."""
    log = log or (lambda m: print(f"[CRONOLOGIA NARRAÇÃO] {m}"))
    path = event.get("narration_path")
    if not path or not os.path.exists(path):
        return {"error": "Narração ainda não transcrita."}
    try:
        body = read_narration_body(path)
    except Exception as ex:  # noqa: BLE001
        return {"error": f"Não foi possível ler a narração: {ex}"}

    start = event.get("actual_start_epoch") or event.get("scheduled_epoch")
    dur = int(event.get("duration") or 0)
    live_start = datetime.fromtimestamp(start).strftime("%H:%M:%S") if start else "N/A"
    live_end = datetime.fromtimestamp(start + dur).strftime("%H:%M:%S") if (start and dur) else "N/A"
    live_date = datetime.fromtimestamp(start).strftime("%d/%m/%Y") if start else datetime.now().strftime("%d/%m/%Y")

    # Combina metadados já extraídos pela análise da transcrição + título
    prev_analysis = event.get("transcript_analysis") or {}
    guessed = guess_match_from_title(event.get("title", ""))
    meta = dict(meta or event.get("meta") or {})
    if not meta.get("team1"):
        meta["team1"] = prev_analysis.get("team1") or guessed.get("team1") or ""
    if not meta.get("team2"):
        meta["team2"] = prev_analysis.get("team2") or guessed.get("team2") or ""
    if not meta.get("competition"):
        meta["competition"] = prev_analysis.get("competition") or guessed.get("competition") or "Brasileirão Série A"
    if not meta.get("date"):
        meta["date"] = prev_analysis.get("date") or live_date

    web = collect_web_info(meta, event, log) if use_web else {}

    prompt = PROMPT_TMPL.format(
        channel=event.get("channel_name", ""),
        title=event.get("title", ""),
        live_start=live_start,
        live_end=live_end,
        duration=fmt_hms(dur) if dur else "N/A",
        team1=meta.get("team1") or "A identificar na transcrição",
        team2=meta.get("team2") or "A identificar na transcrição",
        competition=meta.get("competition") or "A identificar na transcrição",
        date=meta.get("date") or live_date,
        web=(web.get("verdict_text") or "(pesquisa web indisponível — utilize os dados da transcrição e seu conhecimento oficial da partida)")[:20000],
        narration=_compact_narration(body),
    )
    log("🧠 Gemini analisando a narração completa, marcas citadas e montando a cronologia oficial...")
    try:
        raw = gemini_generate_text(api_key, model_id, [prompt], json_mode=True, log=log)
        data = _parse_json(raw)
    except Exception as ex:  # noqa: BLE001
        return {"error": f"Falha ao gerar cronologia: {ex}"}

    t1 = data.get("team1") or meta.get("team1") or "Time 1"
    t2 = data.get("team2") or meta.get("team2") or "Time 2"
    score = str(data.get("final_score") or prev_analysis.get("detected_score") or "").strip()
    milestones: List[Dict[str, Any]] = []
    for m in data.get("technical_milestones") or []:
        if isinstance(m, dict) and (m.get("event") or m.get("type")):
            milestones.append(m)

    # Consolida menções de marcas da análise prévia + cronologia
    brand_mentions: List[Dict[str, Any]] = []
    seen_brands = set()
    for bm in (data.get("brand_mentions") or []) + (prev_analysis.get("brand_mentions") or []):
        if isinstance(bm, dict) and bm.get("brand"):
            key = (str(bm.get("brand")).lower().strip(), str(bm.get("video_time") or "")[:5])
            if key not in seen_brands:
                seen_brands.add(key)
                brand_mentions.append(bm)

    brands_summary = str(data.get("brands_summary") or prev_analysis.get("brands_summary") or "").strip()
    if brand_mentions and not brands_summary:
        b_names = []
        for bm in brand_mentions:
            bn = str(bm.get("brand") or "").strip()
            if bn and bn not in b_names:
                b_names.append(bn)
        brands_summary = f"Foram identificadas {len(brand_mentions)} inserções/menções comerciais durante a narração: {', '.join(b_names)}."

    try:
        conf = float(data.get("confidence_score") or 0.95)
        conf = conf / 100.0 if conf > 1 else conf
    except Exception:
        conf = 0.95

    # Monta o parecer final do Gemini (sempre presente no final do relatório PDF, igual ao modelo oficial)
    gemini_analysis = str(data.get("gemini_final_analysis") or "").strip()
    web_verdict_text = str(web.get("verdict_text") or "").strip()
    if web_verdict_text and gemini_analysis:
        combined_verdict = f"{web_verdict_text}\n\nANÁLISE COMPLEMENTAR DA TRANSMISSÃO & MERCHANDISING (GEMINI):\n{gemini_analysis}"
    elif web_verdict_text:
        combined_verdict = web_verdict_text
        if brands_summary:
            combined_verdict += f"\n\n• Marcas e Anúncios na Narração: {brands_summary}"
    else:
        combined_verdict = gemini_analysis or data.get("broadcast_summary") or ""

    grounding_verdict = {
        "verdict_text": combined_verdict,
        "references": web.get("references") or [],
        "source": web.get("source") or "gemini_analysis",
    }

    result: Dict[str, Any] = {
        "match_display": f"{t1} x {t2}" + (f" ({score})" if score else ""),
        "team1": t1,
        "team2": t2,
        "competition": data.get("competition") or meta.get("competition") or "—",
        "date": data.get("date") or meta.get("date") or live_date,
        "platform": event.get("channel_name") or "YouTube",
        "confidence_score": conf,
        "duration": dur or None,
        "live_start_time": live_start if start else None,
        "live_end_time": live_end if (start and dur) else None,
        "technical_milestones": milestones,
        "transcript_events": [e for e in (data.get("transcript_events") or []) if isinstance(e, dict)],
        "brand_mentions": brand_mentions,
        "brands_summary": brands_summary,
        "stoppage_time_1t": data.get("stoppage_time_1t") or None,
        "stoppage_time_2t": data.get("stoppage_time_2t") or None,
        "report_title": "Relatório Consolidado de Cronologia Técnica (Expert)",
        "report_kind": "narration",
        "grounding_verdict": grounding_verdict,
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
            "brands_summary": brands_summary,
        },
    }
    for k in ("pre_game_start", "first_half_start", "half_time_start", "second_half_start", "match_end", "post_game_end"):
        v = str(data.get(k) or "").strip()
        if v and v.upper() != "N/A" and re.match(r"^\d{1,2}:\d{2}", v):
            result[k] = v[:8]

    log("✅ Cronologia oficial da narração e análise de marcas geradas com sucesso.")
    return result
