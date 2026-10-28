import pathlib, sys
root = pathlib.Path(r'G:/My Drive/helios')
for py in root.rglob('*.py'):
    text = py.read_text(encoding='utf-8')
    new_text = text.replace('skelion_', 'skelion_').replace('skl_live_', 'skl_live_')
    if new_text != text:
        py.write_text(new_text, encoding='utf-8')
        print(f'Updated {py}')
