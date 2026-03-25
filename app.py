import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import font_manager
from analysis_utils import (
    build_export_frames,
    build_monthly_time_profile_data,
    build_selected_day_data,
    prepare_power_views,
)
from data_loaders import load_dataset, load_pv_profile_dataset

from db import (
    init_db,
    calc_file_hash,
    dataset_exists,
    insert_dataset,
    load_dataset_by_id,
    list_datasets,
    pv_dataset_exists,
    insert_pv_profile_dataset,
    load_pv_profile_by_id,
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
class IzumiPowerAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("Izumi Park Town 30分値解析ツール")
        self.root.geometry("1540x900")

        setup_matplotlib_japanese_font()
        init_db()

        self.df = None
        self.daily_df = None
        self.monthly_df = None
        self.current_file = None
        self.current_dataset_id = None
        self.figure = None
        self.canvas = None
        self.current_plot_df = None

        self.pv_norm_df = None
        self.pv_profile_file = None
        self.pv_time_cols = []
        self.pv_factor_var = tk.DoubleVar(value=100.0)
        self.use_pv_var = tk.BooleanVar(value=True)

        self.show_load_var = tk.BooleanVar(value=True)
        self.show_pv_profile_var = tk.BooleanVar(value=True)
        self.show_receive_var = tk.BooleanVar(value=True)

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

        ttk.Label(top, text="日付(YYYY-MM-DD):").pack(side="left", padx=(16, 4))
        self.date_entry = ttk.Entry(top, width=14)
        self.date_entry.pack(side="left")
        ttk.Button(top, text="指定日グラフ", command=self.show_selected_day).pack(side="left", padx=4)

        ttk.Button(top, text="月別 平日/休祝日平均", command=self.show_monthly_weekday_holiday).pack(side="left", padx=4)
        ttk.Button(top, text="CSV出力", command=self.export_csv).pack(side="left", padx=4)

        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(top, text="PV正規化CSV/ZIP読込", command=self.load_pv_profile_file).pack(side="left", padx=4)
        ttk.Checkbutton(top, text="PV反映", variable=self.use_pv_var).pack(side="left", padx=(8, 2))
        ttk.Label(top, text="PV係数:").pack(side="left", padx=(8, 2))
        self.pv_factor_entry = ttk.Entry(top, textvariable=self.pv_factor_var, width=8)
        self.pv_factor_entry.pack(side="left")

        self.status_var = tk.StringVar(value="未読込")
        ttk.Label(top, textvariable=self.status_var).pack(side="right")

        body = ttk.Panedwindow(main, orient="horizontal")
        body.pack(fill="both", expand=True, pady=10)

        left = ttk.Frame(body, width=460)
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=3)

        ttk.Label(left, text="解析結果 / 条件選択", font=("Meiryo UI", 11, "bold")).pack(anchor="w", pady=(0, 6))

        selector = ttk.LabelFrame(left, text="月別時刻プロファイル条件", padding=8)
        selector.pack(fill="x", pady=(0, 8))

        ttk.Label(selector, text="月（複数選択可）").grid(row=0, column=0, sticky="w")
        self.month_listbox = tk.Listbox(selector, selectmode="extended", height=8, exportselection=False)
        self.month_listbox.grid(row=1, column=0, rowspan=4, sticky="nsew", padx=(0, 8), pady=4)

        scrollbar = ttk.Scrollbar(selector, orient="vertical", command=self.month_listbox.yview)
        scrollbar.grid(row=1, column=1, rowspan=4, sticky="ns", pady=4)
        self.month_listbox.config(yscrollcommand=scrollbar.set)

        ttk.Label(selector, text="日種別").grid(row=0, column=2, sticky="w")
        self.daytype_var = tk.StringVar(value="全日")
        self.daytype_combo = ttk.Combobox(
            selector,
            textvariable=self.daytype_var,
            state="readonly",
            values=["全日", "平日", "休祝日"],
            width=12
        )
        self.daytype_combo.grid(row=1, column=2, sticky="w", pady=4)

        ttk.Label(selector, text="表示系列").grid(row=2, column=2, sticky="w", pady=(8, 0))
        ttk.Checkbutton(selector, text="負荷", variable=self.show_load_var).grid(row=3, column=2, sticky="w")
        ttk.Checkbutton(selector, text="疑似PV", variable=self.show_pv_profile_var).grid(row=4, column=2, sticky="w")
        ttk.Checkbutton(selector, text="受電点", variable=self.show_receive_var).grid(row=5, column=2, sticky="w")

        ttk.Button(selector, text="選択月プロファイル表示", command=self.show_monthly_time_profile).grid(
            row=6, column=2, sticky="ew", pady=4
        )
        ttk.Button(selector, text="月選択を全解除", command=self.clear_month_selection).grid(
            row=7, column=2, sticky="ew", pady=4
        )
        ttk.Button(selector, text="月を全選択", command=self.select_all_months).grid(
            row=8, column=2, sticky="ew", pady=4
        )

        selector.columnconfigure(0, weight=1)

        self.text = tk.Text(left, wrap="word", width=56)
        self.text.pack(fill="both", expand=True)

        self.plot_frame = ttk.Frame(right)
        self.plot_frame.pack(fill="both", expand=True)

        self.plot_button_frame = ttk.Frame(right)
        self.plot_button_frame.pack(fill="x", pady=(6, 0))

        ttk.Button(
            self.plot_button_frame,
            text="グラフデータCSV出力",
            command=self.export_current_plot_csv
        ).pack(side="left")

    def log(self, msg):
        self.text.insert("end", msg + "\n")
        self.text.see("end")

    def export_current_plot_csv(self):
        if self.current_plot_df is None or self.current_plot_df.empty:
            messagebox.showwarning("出力不可", "出力できるグラフデータがありません。")
            return

        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)

        if hasattr(self, "current_plot_name") and self.current_plot_name:
            filename = self.current_plot_name
        else:
            filename = "current_plot_data.csv"

        out_path = out_dir / filename
        self.current_plot_df.to_csv(out_path, index=False, encoding="utf-8-sig")
        messagebox.showinfo("出力完了", f"グラフデータを {out_path.resolve()} に出力しました。")

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

    def refresh_month_listbox(self):
        self.month_listbox.delete(0, "end")
        if self.df is None or self.df.empty:
            return
        months = sorted(self.df["month"].dropna().unique().tolist())
        for month in months:
            self.month_listbox.insert("end", month)

    def select_all_months(self):
        self.month_listbox.select_set(0, "end")

    def clear_month_selection(self):
        self.month_listbox.selection_clear(0, "end")

    def get_selected_months(self):
        idxs = self.month_listbox.curselection()
        return [self.month_listbox.get(i) for i in idxs]

    def prepare_views(self):
        self.df, self.daily_df, self.monthly_df = prepare_power_views(self.df)
        self.refresh_month_listbox()

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

                first_date = self.df["datetime"].min().strftime("%Y-%m-%d")
                self.date_entry.delete(0, "end")
                self.date_entry.insert(0, first_date)

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
            self.df = load_dataset(Path(path))
            self.prepare_views()

            dataset_id = insert_dataset(Path(path).name, file_hash, self.df)
            self.current_dataset_id = dataset_id

            first_date = self.df["datetime"].min().strftime("%Y-%m-%d")
            self.date_entry.delete(0, "end")
            self.date_entry.insert(0, first_date)

            self.status_var.set(f"新規DB保存: dataset_id={dataset_id}")
            self.log(f"新規登録完了: {Path(path).name}")
            self.log(f"dataset_id: {dataset_id}")
            self.log(f"レコード数: {len(self.df):,}")
            self.log(f"期間: {self.df['datetime'].min()} ～ {self.df['datetime'].max()}")
            self.log(f"総使用電力量: {self.df['kwh'].sum():,.1f} kWh")

            self.show_summary()

        except Exception as e:
            messagebox.showerror("読込エラー", str(e))

    def load_pv_profile_file(self):
        path = filedialog.askopenfilename(
            title="正規化PVプロファイルCSV/ZIPを選択",
            filetypes=[("CSV or Zip", "*.csv;*.zip"), ("CSV", "*.csv"), ("Zip", "*.zip")]
        )
        if not path:
            return

        try:
            file_hash = calc_file_hash(path)
            existing = pv_dataset_exists(file_hash)

            self.text.delete("1.0", "end")

            if existing:
                dataset_id, source_name, imported_at, record_count = existing

                self.pv_norm_df = load_pv_profile_by_id(dataset_id)
                self.current_pv_dataset_id = dataset_id
                self.pv_profile_file = source_name
                self.pv_time_cols = sorted(
                    [c for c in self.pv_norm_df.columns if c not in ["月", "日"]],
                    key=lambda x: pd.to_datetime(x, format="%H:%M", errors="coerce")
                )

                self.log("=== PV既存DB読込 ===")
                self.log(f"id={dataset_id} file={source_name}")
                self.status_var.set(f"PV DB読込: {dataset_id}")
                return

            # 新規読込
            self.pv_norm_df = load_pv_profile_dataset(Path(path))
            self.pv_profile_file = path
            self.pv_time_cols = sorted(
                [c for c in self.pv_norm_df.columns if c not in ["月", "日"]],
                key=lambda x: pd.to_datetime(x, format="%H:%M", errors="coerce")
            )

            dataset_id = insert_pv_profile_dataset(
                Path(path).name,
                file_hash,
                self.pv_norm_df
            )

            self.current_pv_dataset_id = dataset_id

            self.log("=== PV新規DB保存 ===")
            self.log(f"id={dataset_id}")
            self.log(f"rows={len(self.pv_norm_df)}")

            self.status_var.set(f"PV保存: {dataset_id}")

        except Exception as e:
            messagebox.showerror("PV読込エラー", str(e))

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

            first_date = self.df["datetime"].min().strftime("%Y-%m-%d")
            self.date_entry.delete(0, "end")
            self.date_entry.insert(0, first_date)

            self.status_var.set(f"DB読込: dataset_id={dataset_id}")
            self.text.delete("1.0", "end")
            self.log(f"最新DB読込完了: dataset_id={dataset_id}")
            self.log(f"source_name: {self.current_file}")
            self.log(f"レコード数: {len(self.df):,}")
            self.show_summary()

        except Exception as e:
            messagebox.showerror("DB読込エラー", str(e))

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
        avg_30m_kw = self.df["kw"].mean()
        max_30m_kw = self.df["kw"].max()
        min_30m_kw = self.df["kw"].min()
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

        plot_y = (self.daily_df["kwh"] / 48.0) / 0.5

        self.current_plot_df = pd.DataFrame({
            "日付": self.daily_df["date_ts"],
            "日平均需要電力_kW": plot_y
        })
        self.current_plot_name = "annual_summary_daily_average_kw.csv"

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(self.daily_df["date_ts"], plot_y)
        ax.set_title("日平均需要電力")
        ax.set_xlabel("Date")
        ax.set_ylabel("kW")
        ax.grid(True)
        fig.tight_layout()
        self.draw_figure(fig)

    def show_daily_profile(self):
        if not self.require_data():
            return

        profile = self.df.groupby("time", as_index=False)["kw"].mean()
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

    def show_selected_day(self):
        if not self.require_data():
            return

        date_str = self.date_entry.get().strip()
        if not date_str:
            messagebox.showwarning("日付未入力", "YYYY-MM-DD 形式で日付を入力してください。")
            return

        try:
            target_date = pd.to_datetime(date_str).date()
        except Exception:
            messagebox.showerror("日付エラー", "日付形式は YYYY-MM-DD で入力してください。")
            return

        merged, summary = build_selected_day_data(
            self.df,
            target_date,
            self.pv_norm_df,
            self.pv_time_cols,
            float(self.pv_factor_var.get()),
            self.use_pv_var.get(),
        )
        if merged is None or summary is None:
            messagebox.showwarning("データなし", f"{date_str} のデータはありません。")
            return

        self.text.delete("1.0", "end")
        self.log(f"=== 指定日グラフ: {date_str} ===")
        self.log(f"区分: {summary['holiday_label']}")
        self.log(f"日使用電力量: {summary['day_total_kwh']:,.1f} kWh")
        self.log(f"平均需要電力: {summary['day_avg_kw']:,.2f} kW")
        self.log(f"最大需要電力: {summary['day_max_kw']:,.2f} kW")

        if self.use_pv_var.get() and self.pv_norm_df is not None:
            self.log(f"PV係数: {float(self.pv_factor_var.get()):,.2f}")
            self.log(f"疑似PV発電量: {summary['pv_total_kwh']:,.1f} kWh")
            self.log(f"疑似PV最大出力: {summary['pv_max_kw']:,.2f} kW")
            self.log(f"差引後ネット電力量: {summary['net_total_kwh']:,.1f} kWh")
            self.log(f"差引後ネット最大需要: {summary['net_max_kw']:,.2f} kW")

            if not summary["pv_applied"]:
                self.log("※ PVプロファイルに該当する月日がないため、PVは反映されていません。")

        self.current_plot_df = merged[["time", "kw", "pv_kw", "net_kw"]].copy()
        self.current_plot_df = self.current_plot_df.rename(columns={
            "time": "時刻",
            "kw": "負荷_kW",
            "pv_kw": "疑似PV_kW",
            "net_kw": "受電点_kW",
        })
        self.current_plot_name = f"selected_day_profile_{date_str.replace('-', '')}.csv"

        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(merged["time"], merged["kw"], marker="o", markersize=2, label="需要(kW)")

        if self.use_pv_var.get() and self.pv_norm_df is not None:
            ax.plot(merged["time"], merged["pv_kw"], marker="o", markersize=2, label="疑似PV(kW)")
            ax.plot(merged["time"], merged["net_kw"], marker="o", markersize=2, label="ネット需要(kW)")

        ax.set_title(f"指定日需要電力: {date_str}")
        ax.set_xlabel("Time")
        ax.set_ylabel("kW")
        ax.tick_params(axis="x", rotation=90)
        ax.grid(True)
        ax.legend()
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

    def show_monthly_weekday_holiday(self):
        if not self.require_data():
            return

        daily = self.daily_df.copy()
        daily["day_type"] = daily["is_holiday"].map({False: "平日", True: "休祝日"})

        summary = (
            daily.groupby(["month", "day_type"], as_index=False)["kwh"]
            .mean()
            .rename(columns={"kwh": "avg_kwh_per_day"})
        )
        summary["avg_kw"] = (summary["avg_kwh_per_day"] / 48.0) / 0.5

        pivot = summary.pivot(index="month", columns="day_type", values="avg_kw").fillna(0.0)
        pivot = pivot.sort_index()

        months = list(pivot.index)
        weekday_vals = pivot["平日"] if "平日" in pivot.columns else pd.Series([0]*len(months), index=months)
        holiday_vals = pivot["休祝日"] if "休祝日" in pivot.columns else pd.Series([0]*len(months), index=months)

        self.text.delete("1.0", "end")
        self.log("=== 月別 平日/休祝日平均需要電力 ===")
        for month in months:
            wk = float(weekday_vals.loc[month]) if month in weekday_vals.index else 0.0
            hd = float(holiday_vals.loc[month]) if month in holiday_vals.index else 0.0
            self.log(f"{month} | 平日: {wk:,.2f} kW | 休祝日: {hd:,.2f} kW")

        x = range(len(months))
        width = 0.38

        fig, ax = plt.subplots(figsize=(12, 5))
        ax.bar([i - width/2 for i in x], weekday_vals.values, width=width, label="平日")
        ax.bar([i + width/2 for i in x], holiday_vals.values, width=width, label="休祝日")
        ax.set_title("月別 平日/休祝日 平均需要電力")
        ax.set_xlabel("Month")
        ax.set_ylabel("kW")
        ax.set_xticks(list(x))
        ax.set_xticklabels(months, rotation=45)
        ax.legend()
        fig.tight_layout()
        self.draw_figure(fig)

    def show_monthly_time_profile(self):
        if not self.require_data():
            return

        selected_months = self.get_selected_months()
        if not selected_months:
            messagebox.showwarning("月未選択", "月を1つ以上選択してください。")
            return

        if not (self.show_load_var.get() or self.show_pv_profile_var.get() or self.show_receive_var.get()):
            messagebox.showwarning("表示未選択", "負荷・疑似PV・受電点のいずれかを選択してください。")
            return

        daytype = self.daytype_var.get()
        export_df, stats_df = build_monthly_time_profile_data(
            self.df,
            selected_months,
            daytype,
            self.pv_norm_df,
            float(self.pv_factor_var.get()),
        )

        self.text.delete("1.0", "end")
        self.log("=== 月別時刻プロファイル比較 ===")
        self.log(f"日種別: {daytype}")
        self.log(f"対象月: {', '.join(selected_months)}")
        self.log(
            f"表示: "
            f"{'負荷 ' if self.show_load_var.get() else ''}"
            f"{'疑似PV ' if self.show_pv_profile_var.get() else ''}"
            f"{'受電点' if self.show_receive_var.get() else ''}"
        )

        fig, ax = plt.subplots(figsize=(13, 6))
        for month in selected_months:
            merged = export_df[export_df["month"] == month].copy()
            stats_row = stats_df[stats_df["month"] == month]
            load_mean = float(stats_row.iloc[0]["load_mean"]) if not stats_row.empty else 0.0
            pv_mean = float(stats_row.iloc[0]["pv_mean"]) if not stats_row.empty else 0.0
            recv_mean = float(stats_row.iloc[0]["recv_mean"]) if not stats_row.empty else 0.0
            self.log(
                f"{month} | 負荷平均: {load_mean:,.2f} kW | "
                f"疑似PV平均: {pv_mean:,.2f} kW | "
                f"受電点平均: {recv_mean:,.2f} kW"
            )

            if self.show_load_var.get():
                ax.plot(merged["time"], merged["kw"], label=f"{month} 負荷")

            if self.show_pv_profile_var.get():
                ax.plot(merged["time"], merged["pv_kw"], label=f"{month} 疑似PV")

            if self.show_receive_var.get():
                ax.plot(merged["time"], merged["recv_kw"], label=f"{month} 受電点")

        if not export_df.empty:
            self.current_plot_df = export_df[["month", "time", "kw", "pv_kw", "recv_kw"]].copy()
            self.current_plot_df = self.current_plot_df.rename(columns={
                "month": "月",
                "time": "時刻",
                "kw": "負荷_kW",
                "pv_kw": "疑似PV_kW",
                "recv_kw": "受電点_kW",
            })
            self.current_plot_name = "monthly_time_profile_with_pv.csv"
        else:
            self.current_plot_df = None
            self.current_plot_name = None

        ax.set_title(f"月別時刻プロファイル比較（{daytype}）")
        ax.set_xlabel("Time")
        ax.set_ylabel("kW")
        ax.tick_params(axis="x", rotation=90)
        ax.grid(True)
        ax.legend()
        fig.tight_layout()
        self.draw_figure(fig)

    def show_heatmap(self):
        if not self.require_data():
            return

        work = self.df.copy()
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
        export_frames = build_export_frames(self.df, self.daily_df, self.monthly_df)

        export_frames["long_df"].to_csv(out_dir / "izumi_30min_long_with_kw.csv", index=False, encoding="utf-8-sig")
        export_frames["daily_df"].to_csv(out_dir / "izumi_daily_totals.csv", index=False, encoding="utf-8-sig")
        export_frames["monthly_df"].to_csv(out_dir / "izumi_monthly_totals.csv", index=False, encoding="utf-8-sig")
        export_frames["monthly_daytype_df"].to_csv(
            out_dir / "izumi_monthly_weekday_holiday_avg.csv", index=False, encoding="utf-8-sig"
        )
        export_frames["monthly_time_profile_df"].to_csv(
            out_dir / "izumi_monthly_time_profile.csv", index=False, encoding="utf-8-sig"
        )

        date_str = self.date_entry.get().strip()
        if date_str:
            try:
                target_date = pd.to_datetime(date_str).date()
                day_df, _ = build_selected_day_data(
                    self.df,
                    target_date,
                    self.pv_norm_df,
                    self.pv_time_cols,
                    float(self.pv_factor_var.get()),
                    self.use_pv_var.get(),
                )
                if day_df is not None:
                    out_name = f"izumi_selected_day_with_pv_{target_date.strftime('%Y%m%d')}.csv"
                    day_df.to_csv(out_dir / out_name, index=False, encoding="utf-8-sig")
            except Exception:
                pass

        messagebox.showinfo("出力完了", f"CSVを {out_dir.resolve()} に出力しました。")


def main():
    root = tk.Tk()
    app = IzumiPowerAnalyzer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
