from pathlib import Path
import re

path = Path("db.py")
text = path.read_text(encoding="utf-8")

m = re.search(r"def init_db\s*\(\s*\):(?P<body>.*?)(?=^def\s+\w+\s*\(|\Z)", text, flags=re.DOTALL | re.MULTILINE)
if not m:
    raise SystemExit("repair failed: init_db() not found")

init_full = m.group(0)
init_body = m.group("body")

# PV用 executescript ブロックを検出
pv_block_re = re.compile(
    r'\n(?P<indent>[ \t]*)conn\.executescript\(\s*""".*?pv_profile_datasets.*?pv_profile_records.*?"""\s*\)\s*',
    flags=re.DOTALL
)
pv_match = pv_block_re.search(init_body)
if not pv_match:
    print("No PV executescript block found in init_db(). Nothing to move.")
    raise SystemExit(0)

pv_block = pv_match.group(0)
indent = pv_match.group("indent")

# 一旦削除
body_without_pv = init_body[:pv_match.start()] + init_body[pv_match.end():]

# conn.close() の直前へ挿入
close_re = re.compile(r'^(?P<indent>[ \t]*)conn\.close\(\)\s*$', flags=re.MULTILINE)
close_match = close_re.search(body_without_pv)
if not close_match:
    raise SystemExit("repair failed: conn.close() not found inside init_db()")

insert_pos = close_match.start()
new_body = body_without_pv[:insert_pos] + pv_block + "\n" + body_without_pv[insert_pos:]

new_init = "def init_db():" + new_body
new_text = text[:m.start()] + new_init + text[m.end():]

path.write_text(new_text, encoding="utf-8")
print("repaired db.py: moved PV executescript before conn.close()")
