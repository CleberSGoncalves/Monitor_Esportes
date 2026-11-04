import json

t_path = r'C:\Users\Cleber\.gemini\antigravity\brain\4349b494-c0ce-4e02-8f40-71dee7388ad6\.system_generated\logs\transcript.jsonl'
with open(t_path, 'r', encoding='utf-8') as f:
    for idx, l in enumerate(f, 1):
        if 11045 <= idx <= 11090:
            d = json.loads(l)
            c = str(d.get('content') or d.get('tool_calls') or '')[:120]
            print(f"{idx} [{d.get('type')}] {c}")
