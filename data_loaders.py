from pathlib import Path
import tempfile
import zipfile

import pandas as pd


def load_dataset(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(path, "r") as zip_file:
                xlsx_list = [name for name in zip_file.namelist() if name.lower().endswith(".xlsx")]
                if not xlsx_list:
                    raise ValueError("ZIP内にxlsxが見つかりません。")
                xlsx_name = xlsx_list[0]
                zip_file.extract(xlsx_name, temp_dir)
                return load_excel_30min(Path(temp_dir) / xlsx_name)

    if path.suffix.lower() == ".xlsx":
        return load_excel_30min(path)

    raise ValueError("対応形式は .xlsx または .zip です。")


def load_pv_profile_dataset(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(path, "r") as zip_file:
                csv_list = [name for name in zip_file.namelist() if name.lower().endswith(".csv")]
                if not csv_list:
                    raise ValueError("ZIP内にCSVが見つかりません。")
                csv_name = csv_list[0]
                zip_file.extract(csv_name, temp_dir)
                return load_pv_profile_csv(Path(temp_dir) / csv_name)

    if path.suffix.lower() == ".csv":
        return load_pv_profile_csv(path)

    raise ValueError("PVプロファイルは .csv または .zip に対応しています。")


def load_pv_profile_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    required = {"月", "日"}
    if not required.issubset(df.columns):
        raise ValueError("PVプロファイルCSVには '月' と '日' 列が必要です。")

    time_cols = [column for column in df.columns if column not in ["月", "日"]]
    if len(time_cols) != 48:
        raise ValueError(f"PVプロファイルCSVの時刻列は48個必要です。現在: {len(time_cols)} 個")

    normalized_map = {}
    for column in time_cols:
        try:
            time_value = pd.to_datetime(str(column), format="%H:%M", errors="raise")
            normalized_map[column] = time_value.strftime("%H:%M")
        except Exception:
            try:
                hour, minute = str(column).split(":")
                normalized_map[column] = f"{int(hour):02d}:{int(minute):02d}"
            except Exception as exc:
                raise ValueError(f"時刻列の形式が不正です: {column}") from exc

    df = df.rename(columns=normalized_map)
    normalized_time_cols = sorted(
        [column for column in df.columns if column not in ["月", "日"]],
        key=lambda value: pd.to_datetime(value, format="%H:%M", errors="coerce"),
    )

    df["月"] = pd.to_numeric(df["月"], errors="coerce").astype("Int64")
    df["日"] = pd.to_numeric(df["日"], errors="coerce").astype("Int64")

    for column in normalized_time_cols:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)

    df = df.dropna(subset=["月", "日"]).copy()
    df["月"] = df["月"].astype(int)
    df["日"] = df["日"].astype(int)
    return df


def load_excel_30min(path: Path) -> pd.DataFrame:
    xls = pd.ExcelFile(path)
    sheet = xls.sheet_names[0]
    raw = pd.read_excel(path, sheet_name=sheet, header=None)

    records = []
    nrows, ncols = raw.shape
    row_index = 0

    while row_index < nrows:
        row = raw.iloc[row_index]

        candidate_dates = []
        for column_index in range(1, ncols):
            value = row.iloc[column_index]
            try:
                if pd.notna(value):
                    date_value = pd.to_datetime(value)
                    if 2024 <= date_value.year <= 2030:
                        candidate_dates.append((column_index, date_value.date()))
            except Exception:
                continue

        if len(candidate_dates) >= 5:
            valid_cols = [column_index for column_index, _ in candidate_dates]
            valid_dates = [date_value for _, date_value in candidate_dates]

            for scan_row in range(row_index + 1, min(row_index + 49, nrows)):
                time_value = raw.iloc[scan_row, 0]
                if pd.isna(time_value):
                    continue

                time_text = str(time_value).strip()
                if ":" not in time_text:
                    continue

                for idx, column_index in enumerate(valid_cols):
                    cell_value = raw.iloc[scan_row, column_index]
                    if pd.isna(cell_value):
                        continue

                    try:
                        date_value = valid_dates[idx]
                        if time_text == "24:00":
                            dt = pd.Timestamp(date_value) + pd.Timedelta(days=1)
                        else:
                            hour, minute = time_text.split(":")
                            dt = pd.Timestamp(
                                year=date_value.year,
                                month=date_value.month,
                                day=date_value.day,
                                hour=int(hour),
                                minute=int(minute),
                            )
                        records.append([dt, float(cell_value)])
                    except Exception:
                        continue

            row_index += 49
            continue

        row_index += 1

    if not records:
        raise ValueError("30分値データを抽出できませんでした。")

    df = pd.DataFrame(records, columns=["datetime", "kwh"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df.drop_duplicates(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
