import json

with open(r'C:\Users\adity\.gemini\antigravity\brain\5b2cce19-829f-47e8-a475-c50d0b5847f8\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f):
        if idx > 6500 and idx < 7200:
            if 'write_file' in line:
                obj = json.loads(line)
                for tc in obj.get('tool_calls', []):
                    if tc.get('name') == 'write_file':
                        p = tc.get('args', {}).get('Path')
                        print(f"Line {idx+1}: {p}")
