import json

with open(r'C:\Users\adity\.gemini\antigravity\brain\5b2cce19-829f-47e8-a475-c50d0b5847f8\.system_generated\logs\transcript_full.jsonl', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f):
        if idx >= 7100 and idx <= 7175:
            if 'chat_routes.py' in line:
                obj = json.loads(line)
                for tc in obj.get('tool_calls', []):
                    print(f"Line {idx+1}: {tc.get('name')} {tc.get('args', {}).get('Path')}")
