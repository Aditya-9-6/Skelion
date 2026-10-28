import pathlib, sys
root = pathlib.Path(r'G:/My Drive/helios')
for py in root.rglob('*.py'):
    text = py.read_text(encoding='utf-8')
    if 'skelion_agent' in text:
        new_text = text.replace('skelion_agent', 'skelion_agent')
        py.write_text(new_text, encoding='utf-8')
        print(f'Updated {py}')
