from pathlib import Path
import io
import zipfile

import pandas as pd


def load_excel_raw(input_path):
    input_path = Path(input_path)

    if input_path.suffix.lower() == ".xlsx":
        return pd.read_excel(input_path, header=None)

    if input_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(input_path, "r") as zip_file:
            files = [name for name in zip_file.namelist() if name.lower().endswith(".xlsx")]
            if not files:
                raise FileNotFoundError("Zip内にxlsxがない")
            with zip_file.open(files[0]) as file_obj:
                return pd.read_excel(io.BytesIO(file_obj.read()), header=None)

    raise ValueError("xlsx or zip only")


def find_header_row(df_raw):
    for index in range(min(len(df_raw), 20)):
        row = [str(x).strip() for x in df_raw.iloc[index].tolist()]
        if "type" in row and "月" in row and "日" in row:
            return index
    raise ValueError("ヘッダ行(type, 月, 日)が見つかりません")


def build_dataframe(df_raw, header_row):
    header = [str(x).strip() for x in df_raw.iloc[header_row].tolist()]
    df = df_raw.iloc[header_row + 1:].copy()
    df.columns = header
    return df.reset_index(drop=True)


def normalize_time_label(name):
    text = str(name).strip()
    parts = text.split(":")
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


def extract_type1_dataframe(input_path):
    df_raw = load_excel_raw(input_path)
    header_row = find_header_row(df_raw)
    df = build_dataframe(df_raw, header_row)

    df["type"] = pd.to_numeric(df["type"], errors="coerce")
    df["月"] = pd.to_numeric(df["月"], errors="coerce")
    df["日"] = pd.to_numeric(df["日"], errors="coerce")

    rename_map = {}
    time_cols = []
    for column in df.columns:
        normalized = normalize_time_label(column)
        if normalized is not None:
            rename_map[column] = normalized
            time_cols.append(column)

    out_df = df.loc[df["type"] == 1, ["月", "日"] + time_cols].copy()
    out_df = out_df.rename(columns=rename_map).reset_index(drop=True)

    ordered_time_cols = [f"{hour}:00" for hour in range(24) if f"{hour}:00" in out_df.columns]
    out_df = out_df[["月", "日"] + ordered_time_cols]
    return out_df, header_row, ordered_time_cols


def extract_type1_to_csv(input_path, output_path):
    out_df, header_row, ordered_time_cols = extract_type1_dataframe(input_path)
    out_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return {
        "output_path": str(output_path),
        "header_row": header_row,
        "rows": len(out_df),
        "time_cols": ordered_time_cols,
    }


def interpolate_30min_dataframe(input_path):
    df = pd.read_csv(input_path)
    hour_cols = [f"{hour}:00" for hour in range(24)]
    for column in hour_cols:
        if column not in df.columns:
            raise KeyError(f"列が見つかりません: {column}")

    out_df = df[["月", "日"]].copy()
    for hour in range(24):
        c0 = f"{hour}:00"
        v0 = pd.to_numeric(df[c0], errors="coerce")
        out_df[c0] = v0

        c30 = f"{hour}:30"
        if hour < 23:
            c1 = f"{hour + 1}:00"
            v1 = pd.to_numeric(df[c1], errors="coerce")
            out_df[c30] = (v0 + v1) / 2.0
        else:
            out_df[c30] = 0.0

    ordered_cols = ["月", "日"]
    for hour in range(24):
        ordered_cols += [f"{hour}:00", f"{hour}:30"]
    return out_df[ordered_cols]


def interpolate_30min_to_csv(input_path, output_path):
    out_df = interpolate_30min_dataframe(input_path)
    out_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return {
        "output_path": str(output_path),
        "rows": len(out_df),
        "cols": len(out_df.columns),
    }


def normalize_solar_dataframe(input_path):
    df = pd.read_csv(input_path)
    time_cols = [column for column in df.columns if ":" in column]
    for column in time_cols:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    max_val = df[time_cols].max().max()
    if max_val == 0 or pd.isna(max_val):
        raise ValueError("最大値が0またはNaNです")

    df[time_cols] = df[time_cols] / max_val
    return df, float(max_val)


def normalize_solar_to_csv(input_path, output_path):
    out_df, max_val = normalize_solar_dataframe(input_path)
    out_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return {
        "output_path": str(output_path),
        "max_val": max_val,
        "rows": len(out_df),
    }
