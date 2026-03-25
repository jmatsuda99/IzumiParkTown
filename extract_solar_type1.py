# -*- coding: utf-8 -*-
import argparse
import io
import zipfile
from pathlib import Path
import pandas as pd

def load_excel_raw(input_path):
    input_path = Path(input_path)

    if input_path.suffix.lower() == ".xlsx":
        return pd.read_excel(input_path, header=None)

    if input_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(input_path, "r") as z:
            files = [n for n in z.namelist() if n.lower().endswith(".xlsx")]
            if not files:
                raise FileNotFoundError("Zip内にxlsxがない")
            with z.open(files[0]) as f:
                return pd.read_excel(io.BytesIO(f.read()), header=None)

    raise ValueError("xlsx or zip only")

def find_header_row(df_raw):
    for i in range(min(len(df_raw), 20)):
        row = [str(x).strip() for x in df_raw.iloc[i].tolist()]
        if "type" in row and "月" in row and "日" in row:
            return i
    raise ValueError("ヘッダ行(type, 月, 日)が見つかりません")

def build_dataframe(df_raw, header_row):
    header = [str(x).strip() for x in df_raw.iloc[header_row].tolist()]
    df = df_raw.iloc[header_row + 1:].copy()
    df.columns = header
    df = df.reset_index(drop=True)
    return df

def normalize_time_label(name):
    s = str(name).strip()
    parts = s.split(":")
    if len(parts) == 2:
        hh, mm = parts
        ss = "00"
    elif len(parts) == 3:
        hh, mm, ss = parts
    else:
        return None

    if not (hh.isdigit() and mm.isdigit() and ss.isdigit()):
        return None

    hh_i = int(hh)
    mm_i = int(mm)
    ss_i = int(ss)

    if 0 <= hh_i <= 23 and mm_i == 0 and ss_i == 0:
        return f"{hh_i}:00"

    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-o", "--output", default="solar.csv")
    args = parser.parse_args()

    df_raw = load_excel_raw(args.input)
    header_row = find_header_row(df_raw)
    print("header_row:", header_row)

    df = build_dataframe(df_raw, header_row)
    print("columns:", df.columns.tolist())

    df["type"] = pd.to_numeric(df["type"], errors="coerce")
    df["月"] = pd.to_numeric(df["月"], errors="coerce")
    df["日"] = pd.to_numeric(df["日"], errors="coerce")

    rename_map = {}
    time_cols = []

    for c in df.columns:
        norm = normalize_time_label(c)
        if norm is not None:
            rename_map[c] = norm
            time_cols.append(c)

    print("raw time_cols:", time_cols)

    out = df.loc[df["type"] == 1, ["月", "日"] + time_cols].copy()
    out = out.rename(columns=rename_map)
    out = out.reset_index(drop=True)

    ordered_time_cols = [f"{h}:00" for h in range(24) if f"{h}:00" in out.columns]
    out = out[["月", "日"] + ordered_time_cols]

    print("normalized time_cols:", ordered_time_cols)
    print("rows:", len(out))

    out.to_csv(args.output, index=False, encoding="utf-8-sig")
    print("saved:", args.output)

if __name__ == "__main__":
    main()
