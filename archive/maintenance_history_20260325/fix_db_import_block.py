from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

start = text.find("from db import (")
if start == -1:
    raise SystemExit("from db import block start not found")

end = text.find(")\n", start)
if end == -1:
    raise SystemExit("from db import block end not found")

end = end + 2  # include closing ) and newline

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
)
"""

text = text[:start] + replacement + text[end:]
path.write_text(text, encoding="utf-8")
print("fixed db import block")
