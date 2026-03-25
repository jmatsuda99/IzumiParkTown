from pathlib import Path
import re

path = Path("app.py")
text = path.read_text(encoding="utf-8")

pattern = re.compile(
    r"from db import \(\s*.*?\)",
    flags=re.DOTALL
)

replacement = """from db import (
    init_db,
    calc_file_hash,
    dataset_exists,
    insert_dataset,
    load_dataset_by_id,
    list_datasets,
    pv_dataset_exists,
    insert_pv_profile_dataset,
    load_pv_profile_by_id,
    list_pv_profile_datasets,
    load_latest_pv_profile,
)"""

if not pattern.search(text):
    raise SystemExit("from db import block not found")

text = pattern.sub(replacement, text, count=1)
path.write_text(text, encoding="utf-8")
print("replaced db import block successfully")
