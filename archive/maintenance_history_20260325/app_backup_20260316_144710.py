import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import zipfile
import tempfile
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import font_manager

from db import (
    init_db,
    calc_file_hash,
    dataset_exists,
    insert_dataset,
    load_dataset_by_id,
    list_datasets,
)


def setup_matplotlib_japanese_font():
    preferred_fonts = [
        "Noto Sans CJK JP",
        "Noto Sans JP",
        "Yu Gothic",
        "Meiryo",
        "MS Gothic",
        "IPAexGothic",
        "IPAGothic",
    ]

    available = {f.name for f in font_manager.fontManager.ttflist}
    for font_name in preferred_fonts:
        if font_name in available:
            plt.rcParams["font.family"] = font_name
            break

    plt.rcParams["axes.unicode_minus"] = False


def kwh_to_kw(series):
    return series / 0.5


class IzumiPowerAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Izumi Park Town 30分値解析ツール")
        self.root.geometry("1380x840")

        setup_matplotlib_japanese_font()
        init_db()

        self.df = None
        self.daily_df = None
        self.monthly_df = None
        self.current_file = None
        self.current_dataset_id = None
        self.figure = None
        self.canvas = None

        self._build_ui()

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        top = ttk.Frame(main)
        top.pack(fill="x")

        ttk.Button(top, text="Excel/ZIP読込→DB保存", command=self.load_file).pack(side="left", padx=4)
        ttk.Button(top, text="DB一覧", command=self.show_db_list).pack(side="left", padx=4)
        ttk.Button(top, text="最新DBを読込", command=self.load_latest_from_db).pack(side="left", padx=4)
        ttk.Button(top, text="年間概要", command=self.show_summary).pack(side="left", padx=4)
        ttk.Button(top, text="日別負荷", command=self.show_daily_profile).pack(side="left", padx=4)
        ttk.Button(top, text="月別集計", command=self.show_monthly_usage).pack(side="left", padx=4)
        ttk.Button(top, text="ヒートマップ", command=self.show_heatmap).pack(side="left", padx=4)
        ttk.Button(top, text="CSV出力", command=self.export_csv).pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="未読込")
        ttk.Label(top, textvariable=self.status_var).pack(side="right")

        body = ttk.Panedwindow(main, orient="horizontal")
        body.pack(fill="both", expand=True, pady=10)

        left = ttk.Frame(body, width=420)
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=3)

        ttk.Label(left, text="解析結果 / DB情報", font=("Meiryo UI", 11, "bold")).pack(anchor="w", pady=(0, 6))

        self.text = tk.Text(left, wrap="word", width=50)
        self.text.pack(fill="both", expand=True)

        self.plot_frame = ttk.Frame(right)
        self.plot_frame.pack(fill="both", expand=True)

    def log(self, msg):
        self.text.insert("end", msg + "\n")
        self.text.see("end")

    def clear_plot(self):
        for widget in self.plot_frame.winfo_children():
            widget.destroy()
        self.figure = None
        self.canvas = None

    def draw_figure(self, fig):
        self.clear_plot()
        self.figure = fig
        self.canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def prepare_views(self):
        self.daily_df = self._create_daily_totals(self.df)
        self.monthly_df = self._create_monthly_totals(self.daily_df)

    def load_file(self):
        path = filedialog.askopenfilename(
            title="30分値データを選択",
            filetypes=[("Excel or Zip", "*.xlsx;*.zip"), ("Excel", "*.xlsx"), ("Zip", "*.zip")]
        )
        if not path:
            return

        try:
            file_hash = calc_file_hash(path)
            existing = dataset_exists(file_hash)

            self.text.delete("1.0", "end")

            if existing:
                dataset_id, source_name, imported_at, record_count, total_kwh = existing
                self.df = load_dataset_by_id(dataset_id)
                self.current_dataset_id = dataset_id
                self.current_file = source_name
                self.prepare_views()

                self.status_var.set(f"既存DB読込: dataset_id={dataset_id}")
                self.log("同一ファイルは既にDB登録済です。")
                self.log(f"dataset_id: {dataset_id}")
                self.log(f"source_name: {source_name}")
                self.log(f"imported_at: {imported_at}")
                self.log(f"record_count: {record_count}")
                self.log(f"total_kwh: {total_kwh:,.1f}")
                self.show_summary()
                return

            self.current_file = path
            self.df = self._load_dataset(Path(path))
            self.prepare_views()

            dataset_id = insert_dataset(Path(path).name, file_hash, self.df)
            self.current_dataset_id = dataset_id

            self.status_var.set(f"新規DB保存: dataset_id={dataset_id}")
            self.log(f"新規登録完了: {Path(path).name}")
            self.log(f"dataset_id: {dataset_id}")
            self.log(f"レコード数: {len(self.df):,}")
            self.log(f"期間: {self.df['datetime'].min()} ～ {self.df['datetime'].max()}")
            self.log(f"総使用電力量: {self.df['kwh'].sum():,.1f} kWh")

            self.show_summary()

        except Exception as e:
            messagebox.showerror("読込エラー", str(e))

    def show_db_list(self):
        try:
            df = list_datasets()
            self.text.delete("1.0", "end")
            self.log("=== DB登録済みデータ一覧 ===")
            if df.empty:
                self.log("登録データはありません。")
                return

            for row in df.itertuples(index=False):
                self.log(
                    f"id={row.id} | {row.source_name} | {row.imported_at} | "
                    f"{row.record_count}件 | {row.total_kwh:,.1f} kWh"
                )
        except Exception as e:
            messagebox.showerror("DB一覧エラー", str(e))

    def load_latest_from_db(self):
        try:
            df_list = list_datasets()
            if df_list.empty:
                messagebox.showwarning("DB未登録", "DBにデータがありません。先に読込してください。")
                return

            dataset_id = int(df_list.iloc[0]["id"])
            self.df = load_dataset_by_id(dataset_id)
            self.current_dataset_id = dataset_id
            self.current_file = df_list.iloc[0]["source_name"]
            self.prepare_views()

            self.status_var.set(f"DB読込: dataset_id={dataset_id}")
            self.text.delete("1.0", "end")
            self.log(f"最新DB読込完了: dataset_id={dataset_id}")
            self.log(f"source_name: {self.current_file}")
            self.log(f"レコード数: {len(self.df):,}")
            self.show_summary()

        except Exception as e:
            messagebox.showerror("DB読込エラー", str(e))

    def _load_dataset(self, path: Path):
        if path.suffix.lower() == ".zip":
            with tempfile.TemporaryDirectory() as td:
                with zipfile.ZipFile(path, "r") as zf:
                    xlsx_list = [n for n in zf.namelist() if n.lower().endswith(".xlsx")]
                    if not xlsx_list:
                        raise ValueError("ZIP内にxlsxが見つかりません。")
                    xlsx_name = xlsx_list[0]
                    zf.extract(xlsx_name, td)
                    xlsx_path = Path(td) / xlsx_name
                    return self._load_excel(xlsx_path)
        elif path.suffix.lower() == ".xlsx":
            return self._load_excel(path)
        else:
            raise ValueError("対応形式は .xlsx または .zip です。")

    def _load_excel(self, path: Path):
        xls = pd.ExcelFile(path)
        sheet = xls.sheet_names[0]
        raw = pd.read_excel(path, sheet_name=sheet, header=None)

        date_row_idx = None
        time_col_idx = None

        for i in range(min(20, len(raw))):
            row = raw.iloc[i]
            date_like = 0
            for v in row:
                try:
                    if pd.notna(v):
                        pd.to_datetime(v)
                        date_like += 1
                except:
                    pass
            if date_like >= 5:
                date_row_idx = i
                break

        if date_row_idx is None:
            raise ValueError("日付ヘッダ行を特定できませんでした。")

        for c in range(min(5, raw.shape[1])):
            sample = raw.iloc[date_row_idx + 1: date_row_idx + 10, c].astype(str).tolist()
            hit = sum((":" in s) for s in sample)
            if hit >= 3:
                time_col_idx = c
                break

        if time_col_idx is None:
            time_col_idx = 0

        dates = raw.iloc[date_row_idx, time_col_idx + 1:].tolist()
        times = raw.iloc[date_row_idx + 1:, time_col_idx].tolist()
        values = raw.iloc[date_row_idx + 1:, time_col_idx + 1:]

        valid_dates = []
        valid_cols = []
        for idx, d in enumerate(dates):
            try:
                dd = pd.to_datetime(d).date()
                valid_dates.append(dd)
                valid_cols.append(idx)
            except:
                pass

        values = values.iloc[:, valid_cols]

        records = []
        for r_idx, t in enumerate(times):
            if pd.isna(t):
                continue
            t_str = str(t).strip()
            if ":" not in t_str:
                continue

            for c_idx, d in enumerate(valid_dates):
                v = values.iloc[r_idx, c_idx]
                if pd.isna(v):
                    continue
                try:
                    if t_str == "24:00":
                        dt = pd.Timestamp(d) + pd.Timedelta(days=1)
                    else:
                        hh, mm = t_str.split(":")
                        dt = pd.Timestamp(
                            year=d.year,
                            month=d.month,
                            day=d.day,
                            hour=int(hh),
                            minute=int(mm)
                        )
                    records.append([dt, float(v)])
                except:
                    continue

        if not records:
            raise ValueError("30分値データを抽出できませんでした。")

        df = pd.DataFrame(records, columns=["datetime", "kwh"]).sort_values("datetime").reset_index(drop=True)
        df["date"] = df["datetime"].dt.date
        df["month"] = df["datetime"].dt.to_period("M").astype(str)
        df["time"] = df["datetime"].dt.strftime("%H:%M")
        return df

    def _create_daily_totals(self, df):
        daily = df.groupby("date", as_index=False)["kwh"].sum()
        daily["date"] = pd.to_datetime(daily["date"])
        daily["month"] = daily["date"].dt.to_period("M").astype(str)
        return daily

    def _create_monthly_totals(self, daily_df):
        monthly = daily_df.groupby("month", as_index=False)["kwh"].sum()
        monthly["month_dt"] = pd.to_datetime(monthly["month"] + "-01")
        monthly = monthly.sort_values("month_dt").reset_index(drop=True)
        return monthly

    def require_data(self):
        if self.df is None:
            messagebox.showwarning("未読込", "先にExcel/ZIP読込またはDB読込を行ってください。")
            return False
        return True

    def show_summary(self):
        if not self.require_data():
            return

        self.text.delete("1.0", "end")
        total = self.df["kwh"].sum()
        avg_30m_kwh = self.df["kwh"].mean()
        max_30m_kwh = self.df["kwh"].max()
        min_30m_kwh = self.df["kwh"].min()
        avg_30m_kw = avg_30m_kwh / 0.5
        max_30m_kw = max_30m_kwh / 0.5
        min_30m_kw = min_30m_kwh / 0.5
        avg_day = self.daily_df["kwh"].mean()
        max_day = self.daily_df["kwh"].max()
        min_day = self.daily_df["kwh"].min()

        self.log("=== 年間概要 ===")
        self.log(f"dataset_id: {self.current_dataset_id}")
        self.log(f"ソース: {self.current_file}")
        self.log(f"期間: {self.df['datetime'].min()} ～ {self.df['datetime'].max()}")
        self.log(f"総使用電力量: {total:,.1f} kWh")
        self.log(f"30分平均: {avg_30m_kw:,.2f} kW")
        self.log(f"30分最大: {max_30m_kw:,.2f} kW")
        self.log(f"30分最小: {min_30m_kw:,.2f} kW")
        self.log(f"日平均: {avg_day:,.2f} kWh/日")
        self.log(f"日最大: {max_day:,.2f} kWh/日")
        self.log(f"日最小: {min_day:,.2f} kWh/日")

        plot_y = kwh_to_kw(self.daily_df["kwh"] / 48.0)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(self.daily_df["date"], plot_y)
        ax.set_title("日平均需要電力")
        ax.set_xlabel("Date")
        ax.set_ylabel("kW")
        ax.grid(True)
        fig.tight_layout()
        self.draw_figure(fig)

    def show_daily_profile(self):
        if not self.require_data():
            return

        profile = self.df.groupby("time", as_index=False)["kwh"].mean()
        profile["kw"] = kwh_to_kw(profile["kwh"])
        profile["sort_key"] = pd.to_datetime(profile["time"], format="%H:%M", errors="coerce")
        profile = profile.sort_values("sort_key")

        self.text.delete("1.0", "end")
        self.log("=== 平均日負荷カーブ ===")
        for _, row in profile.head(10).iterrows():
            self.log(f"{row['time']} : {row['kw']:.2f} kW")

        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(profile["time"], profile["kw"])
        ax.set_title("平均日負荷カーブ")
        ax.set_xlabel("Time")
        ax.set_ylabel("kW")
        ax.tick_params(axis="x", rotation=90)
        ax.grid(True)
        fig.tight_layout()
        self.draw_figure(fig)

    def show_monthly_usage(self):
        if not self.require_data():
            return

        self.text.delete("1.0", "end")
        self.log("=== 月別使用電力量 ===")
        for _, row in self.monthly_df.iterrows():
            self.log(f"{row['month']} : {row['kwh']:,.1f} kWh")

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(self.monthly_df["month"], self.monthly_df["kwh"])
        ax.set_title("月別使用電力量")
        ax.set_xlabel("Month")
        ax.set_ylabel("kWh")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()
        self.draw_figure(fig)

    def show_heatmap(self):
        if not self.require_data():
            return

        work = self.df.copy()
        work["kw"] = kwh_to_kw(work["kwh"])
        work["date_str"] = work["datetime"].dt.strftime("%Y-%m-%d")
        pivot = work.pivot_table(index="time", columns="date_str", values="kw", aggfunc="mean")
        pivot = pivot.sort_index()

        self.text.delete("1.0", "end")
        self.log("=== 30分値ヒートマップ ===")
        self.log(f"行数: {pivot.shape[0]}")
        self.log(f"列数: {pivot.shape[1]}")

        fig, ax = plt.subplots(figsize=(14, 6))
        im = ax.imshow(pivot.values, aspect="auto", interpolation="nearest")
        ax.set_title("30分値需要電力ヒートマップ")
        ax.set_xlabel("Date")
        ax.set_ylabel("Time")
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)
        fig.colorbar(im, ax=ax, label="kW")
        fig.tight_layout()
        self.draw_figure(fig)

    def export_csv(self):
        if not self.require_data():
            return

        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)

        export_df = self.df.copy()
        export_df["kw"] = export_df["kwh"] / 0.5

        export_daily = self.daily_df.copy()
        export_daily["avg_kw"] = (export_daily["kwh"] / 48.0) / 0.5

        self.df.to_csv(out_dir / "izumi_30min_long.csv", index=False, encoding="utf-8-sig")
        export_df.to_csv(out_dir / "izumi_30min_long_with_kw.csv", index=False, encoding="utf-8-sig")
        export_daily.to_csv(out_dir / "izumi_daily_totals.csv", index=False, encoding="utf-8-sig")
        self.monthly_df.to_csv(out_dir / "izumi_monthly_totals.csv", index=False, encoding="utf-8-sig")

        messagebox.showinfo("出力完了", f"CSVを {out_dir.resolve()} に出力しました。")


def main():
    root = tk.Tk()
    app = IzumiPowerAnalyzer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
