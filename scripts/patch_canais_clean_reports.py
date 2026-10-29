# Patch live_channel_monitor.py: disable auto sharepoint sync for youtube channels
with open("modules/live_channel_monitor.py", "r", encoding="utf-8") as f:
    lcm = f.read()

target_lcm = """        # Sincronização com SharePoint e disparo de E-mail desacoplados em segundo plano
        def _bg_sync():
            try:
                plog("☁️ Sincronizando relatório com SharePoint...")
                self.sync_event_to_sharepoint(vid)
            except Exception as ex_sp:
                self.log(f"⚠️ Aviso SharePoint: {ex_sp}")"""

replacement_lcm = """        # Disparo desacoplado em segundo plano (SharePoint NÃO é automático para Canais Live, conforme solicitado)
        def _bg_sync():
            # Nota: Sincronização com SharePoint em Canais Live é estritamente sob demanda via botão na interface"""

lcm_n = lcm.replace("\r\n", "\n")
t_lcm_n = target_lcm.replace("\r\n", "\n")
r_lcm_n = replacement_lcm.replace("\r\n", "\n")

if t_lcm_n in lcm_n:
    lcm_n = lcm_n.replace(t_lcm_n, r_lcm_n, 1)
    with open("modules/live_channel_monitor.py", "w", encoding="utf-8") as f:
        f.write(lcm_n.replace("\n", "\r\n"))
    print("live_channel_monitor.py patched!")
else:
    print("target_lcm not found")

# Patch narration_chronology.py: prompt must be concise, NO yellow cards, goals, fouls
with open("modules/narration_chronology.py", "r", encoding="utf-8") as f:
    nc = f.read()

target_nc = '- Em technical_milestones inclua TODOS os gols, cartões amarelos/vermelhos, intervenções do VAR, pênaltis, substituições e acréscimos; "time" = horário real (Brasília).'
replacement_nc = """- Em technical_milestones inclua EXCLUSIVAMENTE os marcos regulamentares da transmissão e do jogo:
  1. Abertura do Sinal / Início do Pré-Jogo
  2. Início do Jogo (1º Tempo / Bola Rolando)
  3. Acréscimos (1º Tempo)
  4. Intervalo (Halftime) / Fim do 1º Tempo
  5. Início do 2º Tempo / Volta do Intervalo
  6. Acréscimos (2º Tempo)
  7. Apito Final / Encerramento do Jogo
  8. Encerramento da Transmissão (Pós-Jogo)
  IMPORTANTE: NÃO inclua cartões amarelos, cartões vermelhos, gols, substituições ou faltas para manter o relatório executivo, limpo e sucinto."""

nc_n = nc.replace("\r\n", "\n")
t_nc_n = target_nc.replace("\r\n", "\n")
r_nc_n = replacement_nc.replace("\r\n", "\n")

if t_nc_n in nc_n:
    nc_n = nc_n.replace(t_nc_n, r_nc_n, 1)
    with open("modules/narration_chronology.py", "w", encoding="utf-8") as f:
        f.write(nc_n.replace("\n", "\r\n"))
    print("narration_chronology.py patched!")
else:
    print("target_nc not found")
