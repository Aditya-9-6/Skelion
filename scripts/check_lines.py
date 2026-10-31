with open(r"skelion_agent/chat_routes.py", "r", encoding="utf-8") as f:
    raw = f.read()

# Check: if the file has \n\n between almost every line, let's see how many empty lines there are
lines = raw.split("\n")
print(f"Total lines: {len(lines)}")
empty_count = sum(1 for l in lines if not l.strip())
print(f"Empty lines: {empty_count}")
