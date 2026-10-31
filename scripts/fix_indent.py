with open(r"skelion_agent/chat_routes.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

in_func = False
fixed_lines = []
for i, l in enumerate(lines):
    if "async def generate_smart_ai_response" in l:
        in_func = True
        fixed_lines.append(l)
        continue
    if '@router.post("/chat")' in l:
        in_func = False
        fixed_lines.append(l)
        continue
    if in_func:
        stripped = l.strip()
        if stripped and not l.startswith(("    ", "\t")):
            # If line is part of Groq inner loop:
            if stripped.startswith("for gr_key in groq_pool:"):
                fixed_lines.append("        " + stripped + "\n")
            elif stripped.startswith("for g_model in groq_candidate_models:"):
                fixed_lines.append("            " + stripped + "\n")
            else:
                fixed_lines.append("    " + l)
        else:
            fixed_lines.append(l)
    else:
        fixed_lines.append(l)

with open(r"skelion_agent/chat_routes.py", "w", encoding="utf-8", newline="\r\n") as f:
    f.writelines(fixed_lines)

import py_compile

try:
    py_compile.compile(r"skelion_agent/chat_routes.py", doraise=True)
    print("SUCCESSFULLY COMPILED chat_routes.py!")
except py_compile.PyCompileError as e:
    print("Compile error:", e)
