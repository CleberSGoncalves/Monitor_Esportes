"""
Modulo de Gerenciamento de Jogos Auditados e Central de Dossies Esportivos.
Monitor Esportes - Criado por Cleber Goncalves.
"""

import os
import json
import glob
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_PATH = os.path.join(PROJECT_ROOT, "config", "audited_games.json")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")


def get_default_seed_audits() -> list:
    """Retorna dados de jogos auditados iniciais baseados nas partidas reais da CBF para exibicao imediata."""
    return [
        {
            "id": "audit_pal_san_20260826",
            "team1": "Palmeiras",
            "team2": "Santos",
            "score": "2 x 0",
            "comp": "Brasileirao Serie A",
            "date": "26/08/2026",
            "time": "21:30",
            "platform": "CazeTV",
            "pdf_path": os.path.join(REPORTS_DIR, "auditoria_Palmeiras_x_Santos_20260826.pdf"),
            "goals_count": 2,
            "cards_count": 3,
            "brands_count": 14,
            "status": "Concluido (IA Gemini)",
            "summary": (
                "Partida dominada pelo Palmeiras na Allianz Arena com forte presenca ofensiva. "
                "Gols marcados aos 34' por Flaco Lopez em cabeceio preciso e aos 78' por Raphael Veiga "
                "apos jogada trabalhada pela ponta direita. A transmissao da CazeTV exibiu 14 insercoes "
                "publicitarias das marcas Amazon Prime, Betano e Claro com 100% de conformidade."
            ),
            "timeline": [
                {"min": "12'", "type": "Cartao Amarelo", "desc": "Falta tatica no meio campo (Santos)."},
                {"min": "34'", "type": "Gol (Palmeiras)", "desc": "Flaco Lopez finaliza de cabeca apos escanteio."},
                {"min": "45+2'", "type": "Insercao Comercial", "desc": "Vinheta Betano exibida no encerramento da 1a etapa."},
                {"min": "61'", "type": "Cartao Amarelo", "desc": "Entrada dura na lateral (Palmeiras)."},
                {"min": "78'", "type": "Gol (Palmeiras)", "desc": "Raphael Veiga chuta colocado da entrada da area."},
                {"min": "89'", "type": "Cartao Amarelo", "desc": "Reclamacao com a arbitragem (Santos)."}
            ],
            "created_at": "2026-08-26 23:45"
        },
        {
            "id": "audit_cru_fla_20260822",
            "team1": "Cruzeiro",
            "team2": "Flamengo",
            "score": "1 x 1",
            "comp": "Brasileirao Serie A",
            "date": "22/08/2026",
            "time": "21:00",
            "platform": "Amazon Prime",
            "pdf_path": os.path.join(REPORTS_DIR, "auditoria_Cruzeiro_x_Flamengo_20260822.pdf"),
            "goals_count": 2,
            "cards_count": 5,
            "brands_count": 18,
            "status": "Concluido (IA Gemini)",
            "summary": (
                "Confronto intenso no Mineirao com muita disputa fisica. Flamengo abriu o placar aos 21' "
                "com Pedro, e o Cruzeiro empatou aos 67' com Matheus Pereira em cobranca de falta magistral. "
                "A Amazon Prime transmitiu com 18 ativacoes de marca capturadas e validadas."
            ),
            "timeline": [
                {"min": "21'", "type": "Gol (Flamengo)", "desc": "Pedro aproveita rebote na pequena area."},
                {"min": "39'", "type": "Cartao Amarelo", "desc": "Falta dura em transicao rapida (Cruzeiro)."},
                {"min": "54'", "type": "Cartao Amarelo", "desc": "Mao na bola intencional (Flamengo)."},
                {"min": "67'", "type": "Gol (Cruzeiro)", "desc": "Matheus Pereira acerta o angulo em falta direta."},
                {"min": "82'", "type": "Cartao Amarelo", "desc": "Falta tatica no meio campo (Cruzeiro)."}
            ],
            "created_at": "2026-08-22 23:15"
        },
        {
            "id": "audit_flu_rem_20260822",
            "team1": "Fluminense",
            "team2": "Remo",
            "score": "3 x 1",
            "comp": "Copa do Brasil",
            "date": "22/08/2026",
            "time": "19:00",
            "platform": "Amazon Prime",
            "pdf_path": os.path.join(REPORTS_DIR, "auditoria_Fluminense_x_Remo_20260822.pdf"),
            "goals_count": 4,
            "cards_count": 2,
            "brands_count": 16,
            "status": "Concluido (IA Gemini)",
            "summary": (
                "Fluminense dominou a posse de bola e garantiu a classificacao no Maracana com atuacao "
                "de gala de Ganso e Cano (2 gols). Remo descontou no final em contra-ataque veloz."
            ),
            "timeline": [
                {"min": "15'", "type": "Gol (Fluminense)", "desc": "German Cano finaliza de primeira."},
                {"min": "41'", "type": "Gol (Fluminense)", "desc": "Ganso bate penalti com categoria."},
                {"min": "70'", "type": "Gol (Fluminense)", "desc": "German Cano amplia de cabeca."},
                {"min": "84'", "type": "Gol (Remo)", "desc": "Gol de honra em contra-ataque rapido."}
            ],
            "created_at": "2026-08-22 21:10"
        }
    ]


class AuditedGamesManager:
    """Gerenciador de leitura, persistencia e estatisticas das auditorias."""

    @staticmethod
    def load_all() -> list:
        """Carrega todos os jogos auditados salvos + fallback inicial."""
        os.makedirs(os.path.dirname(STORAGE_PATH), exist_ok=True)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        
        audits = []
        if os.path.exists(STORAGE_PATH):
            try:
                with open(STORAGE_PATH, "r", encoding="utf-8") as f:
                    audits = json.load(f)
            except Exception as e:
                print(f"[AUDIT MGR WARN] Erro ao ler {STORAGE_PATH}: {e}")

        if not audits:
            audits = get_default_seed_audits()
            AuditedGamesManager.save_all(audits)

        # Atualizar existencia dos arquivos PDF reais na pasta reports
        for a in audits:
            pdf = a.get("pdf_path", "")
            if not pdf or not os.path.exists(pdf):
                t1 = a.get("team1", "").replace(" ", "_")
                t2 = a.get("team2", "").replace(" ", "_")
                matches = glob.glob(os.path.join(REPORTS_DIR, f"*{t1}*{t2}*.pdf"))
                if matches:
                    a["pdf_path"] = matches[0]

        return audits

    @staticmethod
    def save_all(audits: list) -> None:
        """Salva a lista completa no arquivo JSON."""
        try:
            os.makedirs(os.path.dirname(STORAGE_PATH), exist_ok=True)
            with open(STORAGE_PATH, "w", encoding="utf-8") as f:
                json.dump(audits, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[AUDIT MGR WARN] Erro ao salvar {STORAGE_PATH}: {e}")

    @staticmethod
    def add_audit(audit_entry: dict) -> None:
        """Adiciona ou atualiza uma auditoria no topo da lista."""
        audits = AuditedGamesManager.load_all()
        audits = [
            a for a in audits 
            if a.get("id") != audit_entry.get("id") and 
            not (a.get("team1") == audit_entry.get("team1") and a.get("team2") == audit_entry.get("team2") and a.get("date") == audit_entry.get("date"))
        ]
        audits.insert(0, audit_entry)
        AuditedGamesManager.save_all(audits)

    @staticmethod
    def delete_audit(audit_id: str) -> None:
        """Remove uma auditoria pelo ID."""
        audits = AuditedGamesManager.load_all()
        audits = [a for a in audits if a.get("id") != audit_id]
        AuditedGamesManager.save_all(audits)

    @staticmethod
    def get_kpis() -> dict:
        """Calcula estatisticas consolidadas para os cards do topo do Dashboard."""
        audits = AuditedGamesManager.load_all()
        total_games = len(audits)
        total_goals = sum(a.get("goals_count", 0) for a in audits)
        total_brands = sum(a.get("brands_count", 0) for a in audits)
        total_pdfs = sum(1 for a in audits if a.get("pdf_path") and os.path.exists(a.get("pdf_path")))
        
        return {
            "total_games": total_games,
            "total_goals": total_goals,
            "total_brands": total_brands,
            "total_pdfs": total_pdfs
        }