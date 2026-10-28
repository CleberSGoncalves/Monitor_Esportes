path = "modules/narration_chronology.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old_pat = """NON_MATCH_PATTERNS = [
    r"\\b(debate|elei[çc][õo]es?|lula|bolsonaro|sabatina|governador|prefeito|senado)\\b",
    r"\\b(night\\s*show|resenha|bate[- ]bola|radar\\s*de\\s*bagre|bom\\s*dia|boa\\s*noite)\\b",
    r"\\b(resenha\\s*fora\\s*da\\s*sala|mesa\\s*redonda|coletiva|entrevista\\s*coletiva)\\b",
    r"\\b(p[óo]s[- ]jogo|pre[- ]jogo|pr[ée][- ]jogo|bastidores|treino|boletim|not[íi]cias?)\\b",
    r"\\b(react|opini[ãa]o|coment[áa]rios?|pos\\s*jogo|pre\\s*jogo|an[áa]lise)\\b",
]"""

new_pat = """NON_MATCH_PATTERNS = [
    r"\\b(debate|elei[çc][õo]es?|lula|bolsonaro|sabatina|governador|prefeito|senado)\\b",
    r"\\b(night\\s*show|resenha|bate[- ]bola|radar\\s*de\\s*bagre|bom\\s*dia|boa\\s*noite)\\b",
    r"\\b(resenha\\s*fora\\s*da\\s*sala|mesa\\s*redonda|coletiva|entrevista\\s*coletiva)\\b",
    r"\\b(p[óo]s[- ]jogo|pre[- ]jogo|pr[ée][- ]jogo|bastidores|treino|boletim|not[íi]cias?)\\b",
    r"\\b(react|opini[ãa]o|coment[áa]rios?|pos\\s*jogo|pre\\s*jogo|an[áa]lise)\\b",
    r"\\b(esportes\\s*ao\\s*meio[- ]dia|correspondente\\s*ga[úu]cha|central\\s*do\\s*torcedor)\\b",
    r"\\b(mercado\\s*da\\s*bola|mercado\\s*faz\\s*promessa|despista\\s*sobre\\s*o\\s*futuro)\\b",
    r"\\b(vamo,\\s*colorado|vamo\\s*colorado|tudo\\s*sobre\\s+|previs[ãa]o\\s*do\\s*tempo|tr[âa]nsito)\\b",
    r"\\b(bag[ée]tv\\s*news|not[íi]cias?\\s*do\\s*rs|jornal\\s*da\\s*manh[ãa]|primeira\\s*edi[çc][ãa]o)\\b",
    r"\\b(podcast|videocast|entrevista|coletiva|boletim\\s*m[ée]dico|treino\\s*aberto)\\b",
]

def is_likely_match(title: str, duration_s: int = 0) -> bool:
    \"\"\"Determina se o evento tem alta probabilidade de ser uma transmissão de jogo de futebol real.\"\"\"
    if not title:
        return False
    is_non, _ = is_definitely_non_match(title)
    if is_non:
        return False
    # Vídeo muito curto (< 40 min) não é transmissão de partida inteira
    if 0 < duration_s < 2400:
        return False
    guessed = guess_match_from_title(title)
    if not (guessed.get("team1") and guessed.get("team2")):
        return False
    return True"""

if old_pat in content:
    content = content.replace(old_pat, new_pat)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("NON_MATCH_PATTERNS e is_likely_match atualizados com sucesso!")
else:
    # tenta com CRLF
    old_crlf = old_pat.replace("\n", "\r\n")
    new_crlf = new_pat.replace("\n", "\r\n")
    if old_crlf in content:
        content = content.replace(old_crlf, new_crlf)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("NON_MATCH_PATTERNS e is_likely_match atualizados com sucesso (crlf)!")
    else:
        print("Padrao old_pat nao encontrado!")
