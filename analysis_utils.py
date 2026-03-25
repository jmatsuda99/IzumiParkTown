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
