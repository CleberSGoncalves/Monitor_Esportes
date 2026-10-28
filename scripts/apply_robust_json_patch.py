import re

path = "modules/narration_chronology.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = """def _parse_json(text: str) -> Dict[str, Any]:
    t = text.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.MULTILINE).strip()
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"\\{.*\\}", t, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise"""

replacement = '''def _parse_json(text: str) -> Dict[str, Any]:
    """
    Parser ultra-robusto e tolerante para respostas de LLMs (Gemini).
    Trata markdown, controles crus (strict=False), vírgulas extras, aspas internas,
    JSON truncado e possui fallback por extração heurística estruturada para nunca quebrar.
    """
    if not text or not text.strip():
        return {}

    t = text.strip()
    # Remove markdown codeblocks
    t = re.sub(r"^```(?:json)?", "", t, flags=re.MULTILINE).strip()
    t = re.sub(r"```$", "", t, flags=re.MULTILINE).strip()

    first_brace = t.find("{")
    last_brace = t.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = t[first_brace:last_brace + 1]
    else:
        candidate = t

    # Tentativa 1: json.loads padrão
    try:
        return json.loads(candidate)
    except Exception:
        pass

    # Tentativa 2: strict=False (aceita quebras de linha/controles crus dentro de strings)
    try:
        return json.loads(candidate, strict=False)
    except Exception:
        pass

    # Tentativa 3: Remove trailing commas (, } -> } e , ] -> ])
    cleaned = re.sub(r",\\s*([\\]\\}])", r"\\1", candidate)
    try:
        return json.loads(cleaned, strict=False)
    except Exception:
        pass

    # Tentativa 4: Reparar fechamento se foi truncado por limite de tokens
    repaired = cleaned
    unescaped_quotes = len(re.findall(r'(?<!\\\\)"', repaired))
    if unescaped_quotes % 2 != 0:
        repaired += '"'
    open_curly = repaired.count("{") - repaired.count("}")
    open_square = repaired.count("[") - repaired.count("]")
    if open_square > 0:
        repaired += "]" * open_square
    if open_curly > 0:
        repaired += "}" * open_curly
    try:
        return json.loads(repaired, strict=False)
    except Exception:
        pass

    # Tentativa 5: Limpeza de quebras de linha literais dentro de strings
    def fix_newlines(s: str) -> str:
        parts = []
        in_string = False
        escaped = False
        for char in s:
            if char == '"' and not escaped:
                in_string = not in_string
            if in_string and char == '\\n':
                parts.append('\\\\n')
            elif in_string and char == '\\r':
                pass
            else:
                parts.append(char)
            escaped = (char == '\\\\' and not escaped)
        return "".join(parts)

    try:
        repaired_nl = fix_newlines(repaired)
        return json.loads(repaired_nl, strict=False)
    except Exception:
        pass

    # Tentativa 6: Fallback Heurístico Estruturado (Regex Extraction) - Garante que NUNCA quebra com JSONDecodeError
    data: Dict[str, Any] = {}

    def extract_str(key: str, default: str = "") -> str:
        m = re.search(rf'"{key}"\\s*:\\s*"((?:\\\\.|[^"\\\\])*)"', t)
        if m:
            val = m.group(1).replace('\\\\"', '"').replace('\\\\n', '\\n').replace('\\\\t', '\\t')
            return val.strip()
        return default

    data["team1"] = extract_str("team1")
    data["team2"] = extract_str("team2")
    data["competition"] = extract_str("competition", "Brasileirão Série A")
    data["date"] = extract_str("date")
    data["final_score"] = extract_str("final_score")
    data["pre_game_start"] = extract_str("pre_game_start")
    data["first_half_start"] = extract_str("first_half_start")
    data["half_time_start"] = extract_str("half_time_start")
    data["second_half_start"] = extract_str("second_half_start")
    data["match_end"] = extract_str("match_end")
    data["post_game_end"] = extract_str("post_game_end")
    data["times_source"] = extract_str("times_source", "misto")
    data["brands_summary"] = extract_str("brands_summary")
    data["broadcast_summary"] = extract_str("broadcast_summary")
    data["gemini_final_analysis"] = extract_str("gemini_final_analysis")
    data["narration_type"] = extract_str("narration_type", "estudio")
    data["is_match_narration"] = True if '"is_match_narration": true' in t.lower() else False

    # Extrai technical_milestones individuais
    milestones: List[Dict[str, Any]] = []
    milestone_matches = re.finditer(r'\\{[^{}]*"(?:event|type)"[^{}]*\\}', t)
    for mm in milestone_matches:
        try:
            m_obj = json.loads(mm.group(0), strict=False)
            if isinstance(m_obj, dict) and (m_obj.get("event") or m_obj.get("type")):
                milestones.append(m_obj)
        except Exception:
            pass
    data["technical_milestones"] = milestones

    # Extrai brand_mentions individuais
    brand_mentions: List[Dict[str, Any]] = []
    brand_matches = re.finditer(r'\\{[^{}]*"brand"[^{}]*\\}', t)
    for bm in brand_matches:
        try:
            b_obj = json.loads(bm.group(0), strict=False)
            if isinstance(b_obj, dict) and b_obj.get("brand"):
                brand_mentions.append(b_obj)
        except Exception:
            pass
    data["brand_mentions"] = brand_mentions

    return data'''

# Usa regex para substituir a definicao da funcao
pat = r"def _parse_json\(text: str\) -> Dict\[str, Any\]:.*?(?=\n\n\nANALYSIS_PROMPT_TMPL)"
new_content, count = re.subn(pat, lambda m: replacement, content, flags=re.DOTALL)
print(f"Substituicoes realizadas: {count}")
if count > 0:
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Sucesso!")
else:
    print("Padrao nao encontrado!")
