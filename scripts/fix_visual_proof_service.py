with open('modules/visual_proof_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'media_1793733808428_d4ad60b6' in line:
        continue
    new_lines.append(line)

with open('modules/visual_proof_service.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Linha removida de visual_proof_service.py com sucesso!")
