from pathlib import Path

path = Path("db.py")
text = path.read_text(encoding="utf-8")

append_parts = []

if "def list_pv_profile_datasets(" not in text:
    append_parts.append("""

def list_pv_profile_datasets():
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(
            \"\"\"
            SELECT id, source_name, imported_at, record_count
            FROM pv_profile_datasets
            ORDER BY id DESC
            \"\"\",
            conn
        )
    finally:
        conn.close()
""")

if "def load_latest_pv_profile(" not in text:
    append_parts.append("""

def load_latest_pv_profile():
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            \"\"\"
            SELECT id
            FROM pv_profile_datasets
            ORDER BY id DESC
            LIMIT 1
            \"\"\"
        ).fetchone()
        if not row:
            return None, pd.DataFrame()
        dataset_id = int(row[0])
    finally:
        conn.close()

    return dataset_id, load_pv_profile_by_id(dataset_id)
""")

if append_parts:
    text = text.rstrip() + "\n" + "".join(append_parts) + "\n"
    path.write_text(text, encoding="utf-8")
    print("appended missing PV functions to db.py")
else:
    print("no missing PV functions found")
