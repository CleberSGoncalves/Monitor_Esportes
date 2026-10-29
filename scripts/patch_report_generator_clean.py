with open("modules/report_generator.py", "r", encoding="utf-8") as f:
    rg = f.read()

# 1. Patch write_expert_report text generation
target1 = """            for m in res.get("technical_milestones", []):
                lab = str(m.get("type", "EVENTO")).upper()
                is_milestone = any(k in lab for k in ["GOL", "CARTÃO", "SUBSTITU", "PENAL"])"""

replacement1 = """            is_narration = (res.get("report_kind") == "narration")
            for m in res.get("technical_milestones", []):
                lab = str(m.get("type", "EVENTO")).upper()
                if is_narration and any(k in lab for k in ["GOL", "CARTÃO", "AMARELO", "VERMELHO", "SUBSTITU", "SUBST", "FALTA", "IMPEDIMENTO", "VAR", "CHANCE", "PENAL"]):
                    continue
                is_milestone = any(k in lab for k in ["GOL", "CARTÃO", "SUBSTITU", "PENAL"])"""

# 2. Patch generate_consolidated_expert_report PDF rendering
target2 = """            for m in res.get("technical_milestones", []):
                try: 
                    m_min = int(m.get("minute", 0))
                except: m_min = 0
                lab = str(m.get("type", "EVENTO")).strip().upper()
                clk = str(m.get("time") or "").strip()
                
                # Chave única para evitar duplicidades exatas (horário + rótulo)
                item_key = (clk, lab)
                if item_key in seen_keys:
                    continue
                    
                to_render.append({"min": m_min, "lbl": lab, "clock": clk, "txt": m.get("event"), "conf": m.get("confidence") or m_conf})
                seen_keys.add(item_key)"""

replacement2 = """            is_narration = (res.get("report_kind") == "narration")
            for m in res.get("technical_milestones", []):
                try: 
                    m_min = int(m.get("minute", 0))
                except: m_min = 0
                lab = str(m.get("type", "EVENTO")).strip().upper()
                clk = str(m.get("time") or "").strip()
                
                # Filtrar poluidores em relatórios de canais/narração
                if is_narration and any(k in lab for k in ["GOL", "CARTÃO", "AMARELO", "VERMELHO", "SUBSTITU", "SUBST", "FALTA", "IMPEDIMENTO", "VAR", "CHANCE", "PENAL"]):
                    continue
                
                item_key = (clk, lab)
                if item_key in seen_keys:
                    continue
                    
                to_render.append({"min": m_min, "lbl": lab, "clock": clk, "txt": m.get("event"), "conf": m.get("confidence") or m_conf})
                seen_keys.add(item_key)"""

# 3. Patch transcript_events: omit in narration report to avoid pollution
target3 = """            # --- Marcos de Transcrição Detectados (Nacionais/Locais) ---
            t_events = res.get("transcript_events", [])
            if t_events:"""

replacement3 = """            # --- Marcos de Transcrição Detectados (Nacionais/Locais) ---
            t_events = res.get("transcript_events", [])
            # Oculta este bloco volumoso se for relatório de narração/canais para manter o PDF limpo e executivo
            if t_events and not is_narration:"""

rg_n = rg.replace("\r\n", "\n")
t1_n = target1.replace("\r\n", "\n")
r1_n = replacement1.replace("\r\n", "\n")
t2_n = target2.replace("\r\n", "\n")
r2_n = replacement2.replace("\r\n", "\n")
t3_n = target3.replace("\r\n", "\n")
r3_n = replacement3.replace("\r\n", "\n")

assert t1_n in rg_n, "target1 not found"
assert t2_n in rg_n, "target2 not found"
assert t3_n in rg_n, "target3 not found"

rg_n = rg_n.replace(t1_n, r1_n, 1)
rg_n = rg_n.replace(t2_n, r2_n, 1)
rg_n = rg_n.replace(t3_n, r3_n, 1)

with open("modules/report_generator.py", "w", encoding="utf-8") as f:
    f.write(rg_n.replace("\n", "\r\n"))

print("report_generator.py patched successfully!")
