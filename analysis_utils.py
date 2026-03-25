import pandas as pd
import jpholiday


def is_holiday_or_weekend(ts) -> bool:
    date_value = pd.Timestamp(ts).date()
    return pd.Timestamp(ts).weekday() >= 5 or jpholiday.is_holiday(date_value)


def prepare_power_views(df: pd.DataFrame):
    prepared = df.copy()
    prepared["datetime"] = pd.to_datetime(prepared["datetime"])
    prepared["date_ts"] = prepared["datetime"].dt.normalize()
    prepared["date"] = prepared["datetime"].dt.date
    prepared["month"] = prepared["datetime"].dt.to_period("M").astype(str)
    prepared["time"] = prepared["datetime"].dt.strftime("%H:%M")
    prepared["kw"] = prepared["kwh"] / 0.5
    prepared["is_holiday"] = prepared["date_ts"].apply(is_holiday_or_weekend)

    daily_df = create_daily_totals(prepared)
    monthly_df = create_monthly_totals(daily_df)
    return prepared, daily_df, monthly_df


def create_daily_totals(df: pd.DataFrame) -> pd.DataFrame:
    daily_df = df.groupby("date_ts", as_index=False)["kwh"].sum()
    daily_df["date"] = daily_df["date_ts"].dt.date
    daily_df["month"] = daily_df["date_ts"].dt.to_period("M").astype(str)
    daily_df["is_holiday"] = daily_df["date_ts"].apply(is_holiday_or_weekend)
    return daily_df


def create_monthly_totals(daily_df: pd.DataFrame) -> pd.DataFrame:
    monthly_df = daily_df.groupby("month", as_index=False)["kwh"].sum()
    monthly_df["month_dt"] = pd.to_datetime(monthly_df["month"] + "-01")
    return monthly_df.sort_values("month_dt").reset_index(drop=True)


def build_pv_long_df(pv_norm_df: pd.DataFrame, factor: float, base_year: int = 2025) -> pd.DataFrame:
    if pv_norm_df is None or pv_norm_df.empty:
        return pd.DataFrame()

    time_cols = [column for column in pv_norm_df.columns if column not in ["月", "日"]]
    records = []

    for _, row in pv_norm_df.iterrows():
        month = int(row["月"])
        day = int(row["日"])

        try:
            date_value = pd.Timestamp(year=base_year, month=month, day=day)
        except Exception:
            continue

        is_holiday = is_holiday_or_weekend(date_value)

        for time_value in time_cols:
            try:
                pv_kw = float(row[time_value]) * factor
            except Exception:
                pv_kw = 0.0

            records.append(
                {
                    "month_num": month,
                    "month": f"{base_year}-{month:02d}",
                    "day": day,
                    "time": time_value,
                    "pv_kw": pv_kw,
                    "is_holiday": is_holiday,
                }
            )

    pv_long_df = pd.DataFrame(records)
    if pv_long_df.empty:
        return pv_long_df

    pv_long_df["sort_key"] = pd.to_datetime(pv_long_df["time"], format="%H:%M", errors="coerce")
    return pv_long_df


def get_pv_profile_for_date(
    pv_norm_df: pd.DataFrame,
    pv_time_cols,
    target_date,
    factor: float,
):
    if pv_norm_df is None:
        return None

    row = pv_norm_df[(pv_norm_df["月"] == target_date.month) & (pv_norm_df["日"] == target_date.day)]
    if row.empty:
        return None

    values = row.iloc[0][pv_time_cols].astype(float).values * factor
    return pd.DataFrame({"time": pv_time_cols, "pv_kw": values})


def merge_pv_into_time_series(load_df: pd.DataFrame, pv_df: pd.DataFrame | None = None) -> pd.DataFrame:
    merged = load_df.copy()

    if pv_df is not None and not pv_df.empty:
        if "pv_kw" in merged.columns:
            merged = merged.drop(columns=["pv_kw"])
        merged = merged.merge(pv_df[["time", "pv_kw"]], on="time", how="left")
        merged["pv_kw"] = merged["pv_kw"].fillna(0.0)
    elif "pv_kw" not in merged.columns:
        merged["pv_kw"] = 0.0
    else:
        merged["pv_kw"] = pd.to_numeric(merged["pv_kw"], errors="coerce").fillna(0.0)

    if "kwh" not in merged.columns and "kw" in merged.columns:
        merged["kwh"] = merged["kw"] * 0.5

    merged["net_kw"] = merged["kw"] - merged["pv_kw"]
    merged["pv_kwh"] = merged["pv_kw"] * 0.5
    merged["net_kwh"] = merged["kwh"] - merged["pv_kwh"]
    return merged


def build_selected_day_data(
    df: pd.DataFrame,
    target_date,
    pv_norm_df: pd.DataFrame | None,
    pv_time_cols,
    pv_factor: float,
    use_pv: bool,
):
    work_df = df[df["date"] == target_date].copy()
    if work_df.empty:
        return None, None

    work_df["sort_key"] = pd.to_datetime(work_df["time"], format="%H:%M", errors="coerce")
    work_df = work_df.sort_values("sort_key")

    pv_df = None
    if use_pv and pv_norm_df is not None:
        pv_df = get_pv_profile_for_date(pv_norm_df, pv_time_cols, target_date, pv_factor)

    merged_df = merge_pv_into_time_series(work_df[["time", "kw", "kwh"]], pv_df)
    summary = {
        "day_total_kwh": float(work_df["kwh"].sum()),
        "day_avg_kw": float(work_df["kw"].mean()),
        "day_max_kw": float(work_df["kw"].max()),
        "pv_total_kwh": float(merged_df["pv_kwh"].sum()),
        "pv_max_kw": float(merged_df["pv_kw"].max()),
        "net_total_kwh": float(merged_df["net_kwh"].sum()),
        "net_max_kw": float(merged_df["net_kw"].max()),
        "holiday_label": "休祝日" if is_holiday_or_weekend(pd.Timestamp(target_date)) else "平日",
        "pv_applied": pv_df is not None,
    }
    return merged_df, summary


def build_monthly_time_profile_data(
    df: pd.DataFrame,
    selected_months,
    daytype: str,
    pv_norm_df: pd.DataFrame | None,
    pv_factor: float,
):
    load_work_df = df.copy()
    if daytype == "平日":
        load_work_df = load_work_df[load_work_df["is_holiday"] == False]
    elif daytype == "休祝日":
        load_work_df = load_work_df[load_work_df["is_holiday"] == True]
    load_work_df = load_work_df[load_work_df["month"].isin(selected_months)].copy()

    load_profile_df = load_work_df.groupby(["month", "time"], as_index=False)["kw"].mean()
    load_profile_df["sort_key"] = pd.to_datetime(load_profile_df["time"], format="%H:%M", errors="coerce")

    pv_profile_df = pd.DataFrame(columns=["month", "time", "pv_kw", "sort_key"])
    if pv_norm_df is not None and not pv_norm_df.empty:
        pv_long_df = build_pv_long_df(pv_norm_df, pv_factor)
        if not pv_long_df.empty:
            if daytype == "平日":
                pv_long_df = pv_long_df[pv_long_df["is_holiday"] == False]
            elif daytype == "休祝日":
                pv_long_df = pv_long_df[pv_long_df["is_holiday"] == True]

            pv_long_df = pv_long_df[pv_long_df["month"].isin(selected_months)].copy()
            if not pv_long_df.empty:
                pv_profile_df = pv_long_df.groupby(["month", "time"], as_index=False)["pv_kw"].mean()
                pv_profile_df["sort_key"] = pd.to_datetime(pv_profile_df["time"], format="%H:%M", errors="coerce")

    monthly_frames = []
    monthly_stats = []
    for month in selected_months:
        load_sub_df = load_profile_df[load_profile_df["month"] == month].copy().sort_values("sort_key")
        pv_sub_df = pv_profile_df[pv_profile_df["month"] == month].copy().sort_values("sort_key")

        merged_df = pd.merge(
            load_sub_df[["time", "kw", "sort_key"]],
            pv_sub_df[["time", "pv_kw"]],
            on="time",
            how="left",
        )
        merged_df = merge_pv_into_time_series(merged_df, None)
        merged_df = merged_df.rename(columns={"net_kw": "recv_kw", "net_kwh": "recv_kwh"})
        merged_df = merged_df.sort_values("sort_key")
        merged_df["month"] = month
        monthly_frames.append(merged_df)
        monthly_stats.append(
            {
                "month": month,
                "load_mean": float(merged_df["kw"].mean()) if not merged_df.empty else 0.0,
                "pv_mean": float(merged_df["pv_kw"].mean()) if not merged_df.empty else 0.0,
                "recv_mean": float(merged_df["recv_kw"].mean()) if not merged_df.empty else 0.0,
            }
        )

    export_df = pd.concat(monthly_frames, ignore_index=True) if monthly_frames else pd.DataFrame()
    stats_df = pd.DataFrame(monthly_stats)
    return export_df, stats_df


def build_export_frames(df: pd.DataFrame, daily_df: pd.DataFrame, monthly_df: pd.DataFrame):
    export_daily_df = daily_df.copy()
    export_daily_df["avg_kw"] = (export_daily_df["kwh"] / 48.0) / 0.5

    monthly_daytype_df = daily_df.copy()
    monthly_daytype_df["day_type"] = monthly_daytype_df["is_holiday"].map({False: "平日", True: "休祝日"})
    monthly_daytype_df = (
        monthly_daytype_df.groupby(["month", "day_type"], as_index=False)["kwh"]
        .mean()
        .rename(columns={"kwh": "avg_kwh_per_day"})
    )
    monthly_daytype_df["avg_kw"] = (monthly_daytype_df["avg_kwh_per_day"] / 48.0) / 0.5

    monthly_time_profile_df = df.groupby(["month", "is_holiday", "time"], as_index=False)["kw"].mean()
    monthly_time_profile_df["day_type"] = monthly_time_profile_df["is_holiday"].map({False: "平日", True: "休祝日"})

    return {
        "long_df": df.copy(),
        "daily_df": export_daily_df,
        "monthly_df": monthly_df.copy(),
        "monthly_daytype_df": monthly_daytype_df,
        "monthly_time_profile_df": monthly_time_profile_df,
    }
