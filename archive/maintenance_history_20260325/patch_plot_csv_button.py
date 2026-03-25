from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

# 1) __init__ に current_plot_df を追加
old = """        self.figure = None
        self.canvas = None

        self.pv_norm_df = None
"""
new = """        self.figure = None
        self.canvas = None
        self.current_plot_df = None

        self.pv_norm_df = None
"""
if old in text:
    text = text.replace(old, new, 1)

# 2) plot_frame の下に export button を追加
old = """        self.plot_frame = ttk.Frame(right)
        self.plot_frame.pack(fill="both", expand=True)
"""
new = """        self.plot_frame = ttk.Frame(right)
        self.plot_frame.pack(fill="both", expand=True)

        self.plot_button_frame = ttk.Frame(right)
        self.plot_button_frame.pack(fill="x", pady=(6, 0))

        ttk.Button(
            self.plot_button_frame,
            text="グラフデータCSV出力",
            command=self.export_current_plot_csv
        ).pack(side="left")
"""
if old in text:
    text = text.replace(old, new, 1)

# 3) export_current_plot_csv メソッド追加
anchor = """    def clear_plot(self):
"""
insert = """    def export_current_plot_csv(self):
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

"""
if anchor in text and "def export_current_plot_csv(self):" not in text:
    text = text.replace(anchor, insert + anchor, 1)

# 4) show_monthly_time_profile に current_plot_df 保存を追加
old = """        fig, ax = plt.subplots(figsize=(13, 6))

        for month in selected_months:
"""
new = """        fig, ax = plt.subplots(figsize=(13, 6))
        export_rows = []

        for month in selected_months:
"""
if old in text:
    text = text.replace(old, new, 1)

old = """            if self.show_load_var.get():
                ax.plot(merged["time"], merged["kw"], label=f"{month} 負荷")

            if self.show_pv_profile_var.get():
                ax.plot(merged["time"], merged["pv_kw"], label=f"{month} 疑似PV")

            if self.show_receive_var.get():
                ax.plot(merged["time"], merged["recv_kw"], label=f"{month} 受電点")

        ax.set_title(f"月別時刻プロファイル比較（{daytype}）")
"""
new = """            export_sub = merged[["time", "kw", "pv_kw", "recv_kw"]].copy()
            export_sub["month"] = month
            export_rows.append(export_sub[["month", "time", "kw", "pv_kw", "recv_kw"]])

            if self.show_load_var.get():
                ax.plot(merged["time"], merged["kw"], label=f"{month} 負荷")

            if self.show_pv_profile_var.get():
                ax.plot(merged["time"], merged["pv_kw"], label=f"{month} 疑似PV")

            if self.show_receive_var.get():
                ax.plot(merged["time"], merged["recv_kw"], label=f"{month} 受電点")

        if export_rows:
            self.current_plot_df = pd.concat(export_rows, ignore_index=True)
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
"""
if old in text:
    text = text.replace(old, new, 1)

# 5) show_selected_day に current_plot_df 保存を追加
old = """        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(merged["time"], merged["kw"], marker="o", markersize=2, label="需要(kW)")
"""
new = """        self.current_plot_df = merged[["time", "kw", "pv_kw", "net_kw"]].copy()
        self.current_plot_df = self.current_plot_df.rename(columns={
            "time": "時刻",
            "kw": "負荷_kW",
            "pv_kw": "疑似PV_kW",
            "net_kw": "受電点_kW",
        })
        self.current_plot_name = f"selected_day_profile_{date_str.replace('-', '')}.csv"

        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(merged["time"], merged["kw"], marker="o", markersize=2, label="需要(kW)")
"""
if old in text:
    text = text.replace(old, new, 1)

# 6) 既存の show_summary にも current_plot_df 保存を追加（任意）
old = """        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(self.daily_df["date_ts"], plot_y)
"""
new = """        self.current_plot_df = pd.DataFrame({
            "日付": self.daily_df["date_ts"],
            "日平均需要電力_kW": plot_y
        })
        self.current_plot_name = "annual_summary_daily_average_kw.csv"

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(self.daily_df["date_ts"], plot_y)
"""
if old in text:
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("patched app.py successfully")
