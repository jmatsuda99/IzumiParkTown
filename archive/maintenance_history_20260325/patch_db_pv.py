from pathlib import Path
import re

path = Path("db.py")
text = path.read_text(encoding="utf-8")

# -------------------------------------------------
# 1) import 補完
# -------------------------------------------------
if "import sqlite3" not in text:
    text = "import sqlite3\n" + text

if "import pandas as pd" not in text:
    text = "import pandas as pd\n" + text

if "from pathlib import Path" not in text:
    text = "from pathlib import Path\n" + text

# -------------------------------------------------
# 2) DB_PATH 補完
# -------------------------------------------------
if "DB_PATH" not in text:
    text = 'DB_PATH = Path("izumi_power.db")\n\n' + text

# -------------------------------------------------
# 3) init_db にテーブル追加（安全方式）
# -------------------------------------------------
if "pv_profile_datasets" not in text:

    insert_sql = '''
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS pv_profile_datasets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT NOT NULL,
        file_hash TEXT NOT NULL UNIQUE,
        imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        record_count INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS pv_profile_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_id INTEGER NOT NULL,
        month INTEGER NOT NULL,
        day INTEGER NOT NULL,
        time TEXT NOT NULL,
        norm_value REAL NOT NULL,
        FOREIGN KEY (dataset_id) REFERENCES pv_profile_datasets(id)
    );

    CREATE INDEX IF NOT EXISTS idx_pv_profile_records_dataset_id
    ON pv_profile_records(dataset_id);

    CREATE INDEX IF NOT EXISTS idx_pv_profile_records_month_day_time
    ON pv_profile_records(month, day, time);
    """)
    '''

    # init_db の末尾に挿入
    m = re.search(r"(def init_db\s*\(\s*\):.*?)(\n\s*def |\Z)", text, flags=re.DOTALL)
    if not m:
        raise SystemExit("patch failed: init_db not found")

    init_block = m.group(1)
    rest = text[m.start(2):]

    if "conn.executescript" in init_block:
        # 既存SQLの後ろに追加
        init_block = init_block.rstrip() + "\n" + insert_sql + "\n"
    else:
        # なければそのまま追加
        init_block = init_block.rstrip() + "\n" + insert_sql + "\n"

    text = text[:m.start(1)] + init_block + rest

# -------------------------------------------------
# 4) 関数追加
# -------------------------------------------------
if "def pv_dataset_exists" not in text:

    append_block = '''

def pv_dataset_exists(file_hash):
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            """
            SELECT id, source_name, imported_at, record_count
            FROM pv_profile_datasets
            WHERE file_hash = ?
            """,
            (file_hash,)
        ).fetchone()
        return row
    finally:
        conn.close()


def insert_pv_profile_dataset(source_name, file_hash, pv_df):
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO pv_profile_datasets (source_name, file_hash, record_count)
            VALUES (?, ?, ?)
            """,
            (source_name, file_hash, len(pv_df))
        )
        dataset_id = cur.lastrowid

        time_cols = [c for c in pv_df.columns if c not in ["月", "日"]]

        rows = []
        for _, row in pv_df.iterrows():
            for t in time_cols:
                rows.append((
                    dataset_id,
                    int(row["月"]),
                    int(row["日"]),
                    t,
                    float(row[t])
                ))

        cur.executemany(
            """
            INSERT INTO pv_profile_records (dataset_id, month, day, time, norm_value)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows
        )

        conn.commit()
        return dataset_id
    finally:
        conn.close()


def load_pv_profile_by_id(dataset_id):
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(
            """
            SELECT month, day, time, norm_value
            FROM pv_profile_records
            WHERE dataset_id = ?
            ORDER BY month, day, time
            """,
            conn,
            params=(dataset_id,)
        )

        if df.empty:
            return pd.DataFrame()

        pivot = df.pivot(index=["month","day"], columns="time", values="norm_value").reset_index()
        pivot = pivot.rename(columns={"month":"月","day":"日"})

        return pivot
    finally:
        conn.close()


def load_latest_pv_profile():
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute(
            "SELECT id FROM pv_profile_datasets ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None, pd.DataFrame()
        dataset_id = row[0]
    finally:
        conn.close()

    return dataset_id, load_pv_profile_by_id(dataset_id)
'''

    text = text.rstrip() + "\n" + append_block + "\n"

# -------------------------------------------------
# 保存
# -------------------------------------------------
path.write_text(text, encoding="utf-8")
print("patched db.py successfully")
