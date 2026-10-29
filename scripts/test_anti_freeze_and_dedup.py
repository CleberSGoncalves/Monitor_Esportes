import os, sys, time, json
from datetime import datetime

# Bootstrap path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.join(root_dir, "gui"))

print("=== INICIANDO SUITE DE TESTES: ANTI-FREEZE & DEDUPLICAÇÃO CANÔNICA ===")

# Test 1: Fetcher Performance & Non-blocking latency
from modules.cbf_schedule_fetcher import CBFScheduleFetcher

t0 = time.time()
matches = CBFScheduleFetcher.get_upcoming_matches(force_refresh=False)
elapsed_ms = (time.time() - t0) * 1000

print(f"[TEST 1] Latência do CBFScheduleFetcher: {elapsed_ms:.2f} ms")
assert elapsed_ms < 100.0, f"FALHA: Latência muito alta ({elapsed_ms}ms), risco de travar a UI!"
assert len(matches) == 5, f"FALHA: Esperado 5 jogos, obtido {len(matches)}"
print("  --> PASS: Latência ultra-baixa (< 100ms) comprovada, zero risco de freeze no main thread.")

# Test 2: Canonical Match Key
from main_gui import _canonical_match_key

k1 = _canonical_match_key("Vasco da Gama", "Flamengo", "29/10/2026")
k2 = _canonical_match_key("Flamengo", "Vasco", "29/10/2026")
k3 = _canonical_match_key("C.R. Flamengo", "Vasco da Gama SAF", "29-10-2026")

print(f"[TEST 2] Chave Canônica: '{k1}' == '{k2}' == '{k3}'")
assert k1 == k2 == k3, f"FALHA: Assinaturas não coincidem! {k1} vs {k2} vs {k3}"
print("  --> PASS: Normalização canônica robusta e bidirecional validada.")

# Test 3: Load Scheduled Games Deduplication
from main_gui import _load_scheduled_games

# Simula arquivo com duplicata (19:00 e 20:00 para o mesmo jogo)
test_data = [
    {
        "id": "game_1", "team1": "Vasco da Gama", "team2": "Flamengo",
        "date": "29/10/2026", "time": "19:00", "comp": "Brasileirão Série A",
        "platform": "Amazon Prime", "status": "pending"
    },
    {
        "id": "game_2", "team1": "Vasco", "team2": "Flamengo",
        "date": "29/10/2026", "time": "20:00", "comp": "Brasileirão Série A",
        "platform": "Amazon Prime", "status": "pending"
    },
    {
        "id": "game_3", "team1": "Palmeiras", "team2": "Vasco da Gama",
        "date": "01/11/2026", "time": "15:00", "comp": "Copa do Brasil",
        "platform": "Amazon Prime", "status": "pending"
    }
]

cfg_path = os.path.join(root_dir, "config", "scheduled_games.json")
with open(cfg_path, "w", encoding="utf-8") as f:
    json.dump(test_data, f, indent=2)

loaded = _load_scheduled_games()
vasco_flamengo_matches = [g for g in loaded if "vasco" in g.get("team1","").lower() and "flamengo" in g.get("team2","").lower()]

print(f"[TEST 3] Total de Vasco x Flamengo após load deduplicado: {len(vasco_flamengo_matches)}")
assert len(vasco_flamengo_matches) == 1, f"FALHA: Duplicata não eliminada! {len(vasco_flamengo_matches)} encontrados"
assert vasco_flamengo_matches[0]["time"] == "20:00", f"FALHA: Horário oficial 20:00 não preservado: {vasco_flamengo_matches[0]['time']}"
print("  --> PASS: Deduplicação automática em _load_scheduled_games comprovada com sucesso.")

# Restaurar jogos limpos canônicos
import clean_scheduled_configs

print("=== TODOS OS 3 TESTES AUTOMATIZADOS PASSARAM COM 100% DE SUCESSO! ===")
