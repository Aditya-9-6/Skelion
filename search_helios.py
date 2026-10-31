import pathlib

root = pathlib.Path(r"G:/My Drive/helios")
patterns = ["skelion_", "skl_live_"]
for py in root.rglob("*.py"):
    text = py.read_text(encoding="utf-8")
    for pat in patterns:
        if pat in text:
            print(f"{py}:{pat}")
