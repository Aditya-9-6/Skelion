with open(r"skelion_agent/chat_routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

in_func = False
unindented = []
for i, l in enumerate(lines):
    if "async def generate_smart_ai_response" in l:
        in_func = True
        continue
    if '@router.post("/chat")' in l:
        in_func = False
        break
    if in_func:
        stripped = l.strip()
        if stripped and not l.startswith(("    ", "\t")):
            unindented.append((i + 1, l.rstrip()))

print(f"Total unindented lines inside generate_smart_ai_response: {len(unindented)}")
for line_no, text in unindented[:25]:
    print(f"{line_no}: {text}")
