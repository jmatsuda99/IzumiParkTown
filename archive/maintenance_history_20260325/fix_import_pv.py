from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

# db import を探す
if "from db import" not in text:
    raise SystemExit("db import block not found")

# すでに入ってるか確認
if "pv_dataset_exists" in text:
    print("already imported")
    raise SystemExit(0)

# 置換
text = text.replace(
    "from db import (",
    """from db import (
    pv_dataset_exists,
    insert_pv_profile_dataset,
    load_pv_profile_by_id,"""
)

path.write_text(text, encoding="utf-8")

print("fixed import successfully")
