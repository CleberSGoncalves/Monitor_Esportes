import re
import json

bad_json = '''{
  "team1": "Coritiba"
  "team2": "Grêmio"
  "final_score": "1 x 0"
  "technical_milestones": [
    {"event": "Gol 1", "minute": 10}
    {"event": "Gol 2", "minute": 20}
  ]
}'''

try:
    json.loads(bad_json)
except Exception as e:
    print('Erro original:', e)

# Reparo de virgulas faltantes entre linhas
repaired = re.sub(r'([\"\d]|true|false|null|\}|\])\s*\n+(\s*[\"\{\[])', r'\1,\n\2', bad_json)
print('Reparado:')
print(repaired)
res = json.loads(repaired)
print('Parse OK! team1 =', res['team1'], '| milestones =', len(res['technical_milestones']))
