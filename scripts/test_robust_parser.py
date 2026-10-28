import re
import json
from typing import Any, Dict, List

def robust_json_parse(text: str) -> Dict[str, Any]:
    """
    Parser ultra-robusto e tolerante para respostas de LLMs (Gemini).
    Trata:
    1. Blocos de markdown (```json ... ```)
    2. Caracteres de controle não escapados (strict=False)
    3. Trailing commas (vírgulas antes de } ou ])
    4. Aspas internas não escapadas em strings
    5. JSON truncado (delimitadores não fechados)
    6. Fallback heurístico por campos se o parse estrito falhar
    """
    if not text or not text.strip():
        return {}

    t = text.strip()
    # Remove markdown codeblocks
    t = re.sub(r"^```(?:json)?", "", t, flags=re.MULTILINE).strip()
    t = re.sub(r"```$", "", t, flags=re.MULTILINE).strip()

    # Isola o primeiro '{' e o último '}'
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

    # Tentativa 2: strict=False (permite quebras de linha e controles crus em strings)
    try:
        return json.loads(candidate, strict=False)
    except Exception:
        pass

    # Tentativa 3: Remove trailing commas (, } -> } e , ] -> ])
    cleaned = re.sub(r",\s*([\]}])", r"\1", candidate)
    try:
        return json.loads(cleaned, strict=False)
    except Exception:
        pass

    # Tentativa 4: Reparar fechamentos ausentes se foi truncado
    repaired = cleaned
    # Verifica se há aspas abertas não fechadas
    unescaped_quotes = len(re.findall(r'(?<!\\)"', repaired))
    if unescaped_quotes % 2 != 0:
        repaired += '"'
    
    # Contabiliza chaves e colchetes
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

    # Tentativa 5: Limpeza de quebras de linha literais em strings
    # Substitui novas linhas reais que estejam dentro de aspas
    def fix_newlines(s):
        parts = []
        in_string = False
        escaped = False
        for char in s:
            if char == '"' and not escaped:
                in_string = not in_string
            if in_string and char == '\n':
                parts.append('\\n')
            elif in_string and char == '\r':
                pass
            else:
                parts.append(char)
            escaped = (char == '\\' and not escaped)
        return "".join(parts)

    try:
        repaired_nl = fix_newlines(repaired)
        return json.loads(repaired_nl, strict=False)
    except Exception:
        pass

    # Tentativa 6: Fallback Heurístico Estruturado (Regex Extraction)
    # Extrai o máximo de campos fundamentais sem estourar exceção
    data: Dict[str, Any] = {}
    
    def extract_str(key: str, default: str = "") -> str:
        m = re.search(rf'"{key}"\s*:\s*"((?:\\.|[^"\\])*)"', t)
        if m:
            val = m.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t')
            return val
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
    milestone_matches = re.finditer(r'\{[^{}]*"(?:event|type)"[^{}]*\}', t)
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
    brand_matches = re.finditer(r'\{[^{}]*"brand"[^{}]*\}', t)
    for bm in brand_matches:
        try:
            b_obj = json.loads(bm.group(0), strict=False)
            if isinstance(b_obj, dict) and b_obj.get("brand"):
                brand_mentions.append(b_obj)
        except Exception:
            pass
    data["brand_mentions"] = brand_mentions

    return data

if __name__ == "__main__":
    # Teste 1: JSON normal
    t1 = '{"team1": "Internacional", "team2": "Botafogo", "final_score": "3 x 0"}'
    assert robust_json_parse(t1)["final_score"] == "3 x 0"
    
    # Teste 2: JSON com trailing commas e markdown
    t2 = '```json\n{"team1": "Inter", "team2": "Botafogo", "items": [1, 2, ], }\n```'
    assert robust_json_parse(t2)["team1"] == "Inter"

    # Teste 3: JSON com aspas não escapadas e quebra de linha em string
    t3 = '{"team1": "Inter", "gemini_final_analysis": "O jogo teve\n várias jogadas e o narrador gritou: "Gol do Botafogo!" no final.", "final_score": "3 x 0"}'
    res3 = robust_json_parse(t3)
    assert res3["final_score"] == "3 x 0"
    print("ALL TESTS PASSED SUCCESSFULLY!")
