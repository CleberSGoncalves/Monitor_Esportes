with open('modules/report_generator.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = 'm_proofs = res.get("milestone_proofs") or []'
replacement = '''m_proofs = res.get("milestone_proofs") or res.get("visual_proofs") or []
            if m_proofs:
                for stg in m_proofs:
                    if "image_path" not in stg and "frame_path" in stg:
                        stg["image_path"] = stg["frame_path"]
                    if "label" not in stg and "title" in stg:
                        stg["label"] = stg["title"]
                    if "clock" not in stg and "clock_time" in stg:
                        stg["clock"] = stg["clock_time"]
                    if "clock" not in stg and "time" in stg:
                        stg["clock"] = stg["time"]
                    if "description" not in stg and "desc" in stg:
                        stg["description"] = stg["desc"]'''

if target in content:
    content = content.replace(target, replacement, 1)
    with open('modules/report_generator.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Atualizado modules/report_generator.py com sucesso!")
else:
    print("Alvo não encontrado em modules/report_generator.py")
