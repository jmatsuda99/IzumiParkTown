from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

# 1. __init__ に PV 属性を追加
old = """        self.figure = None
        self.canvas = None

        self._build_ui()
"""
new = """        self.figure = None
        self.canvas = None

        self.pv_norm_df = None
        self.pv_profile_file = None
        self.pv_time_cols = []
        self.pv_factor_var = tk.DoubleVar(value=100.0)
        self.use_pv_var = tk.BooleanVar(value=True)

        self._build_ui()
"""
if old not in text:
    raise SystemExit("patch failed: __init__ block not found")
text = text.replace(old, new, 1)

# 2. top UI に PV 読込・係数入力を追加
old = """        ttk.Button(top, text="CSV出力", command=self.export_csv).pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="未読込")
"""
new = """        ttk.Button(top, text="CSV出力", command=self.export_csv).pack(side="left", padx=4)

        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(top, text="PV正規化CSV/ZIP読込", command=self.load_pv_profile_file).pack(side="left", padx=4)
        ttk.Checkbutton(top, text="PV反映", variable=self.use_pv_var).pack(side="left", padx=(8, 2))
        ttk.Label(top, text="PV係数:").pack(side="left", padx=(8, 2))
        self.pv_factor_entry = ttk.Entry(top, textvariable=self.pv_factor_var, width=8)
        self.pv_factor_entry.pack(side="left")

        self.status_var = tk.StringVar(value="未読込")
"""
if old not in text:
    raise SystemExit("patch failed: top UI block not found")
text = text.replace(old, new, 1)

# 3. load_pv_profile_file を追加
anchor = """    def show_db_list(self):
"""
insert = """    def load_pv_profile_file(self):
        path = filedialog.askopenfilename(
            title="正規化PVプロファイルCSV/ZIPを選択",
            filetypes=[("CSV or Zip", "*.csv;*.zip"), ("CSV", "*.csv"), ("Zip", "*.zip")]
        )
        if not path:
            return

        try:
            self.pv_norm_df = self._load_pv_profile_dataset(Path(path))
            self.pv_profile_file = path

            self.text.delete("1.0", "end")
            self.log("=== PV正規化プロファイル読込完了 ===")
            self.log(f"ファイル: {Path(path).name}")
            self.log(f"行数: {len(self.pv_norm_df):,}")
            self.log(f"時刻列数: {len(self.pv_time_cols)}")
            self.log(f"係数デフォルト: {self.pv_factor_var.get():,.2f}")
            self.log(f"月範囲: {self.pv_norm_df['月'].min()} ～ {self.pv_norm_df['月'].max()}")
            if "日" in self.pv_norm_df.columns:
                self.log(f"日範囲: {self.pv_norm_df['日'].min()} ～ {self.pv_norm_df['日'].max()}")

            self.status_var.set(f"PV読込済: {Path(path).name}")

        except Exception as e:
            messagebox.showerror("PV読込エラー", str(e))

"""
if anchor not in text:
    raise SystemExit("patch failed: show_db_list anchor not found")
text = text.replace(anchor, insert + anchor, 1)

# 4. _load_pv_profile_dataset / _load_pv_profile_csv を追加
anchor = """    def _load_excel(self, path: Path):
"""
insert = """    def _load_pv_profile_dataset(self, path: Path):
        if path.suffix.lower() == ".zip":
            with tempfile.TemporaryDirectory() as td:
                with zipfile.ZipFile(path, "r") as zf:
                    csv_list = [n for n in zf.namelist() if n.lower().endswith(".csv")]
                    if not csv_list:
                        raise ValueError("ZIP内にCSVが見つかりません。")
                    csv_name = csv_list[0]
                    zf.extract(csv_name, td)
                    csv_path = Path(td) / csv_name
                    return self._load_pv_profile_csv(csv_path)
        elif path.suffix.lower() == ".csv":
            return self._load_pv_profile_csv(path)
        else:
            raise ValueError("PVプロファイルは .csv または .zip に対応しています。")

    def _load_pv_profile_csv(self, path: Path):
        df = pd.read_csv(path)

        required = {"月", "日"}
        if not required.issubset(df.columns):
            raise ValueError("PVプロファイルCSVには '月' と '日' 列が必要です。")

        time_cols = [c for c in df.columns if c not in ["月", "日"]]
        if len(time_cols) != 48:
            raise ValueError(f"PVプロファイルCSVの時刻列は48個必要です。現在: {len(time_cols)} 個")

        normalized_map = {}
        for c in time_cols:
            try:
                t = pd.to_datetime(str(c), format="%H:%M", errors="raise")
                normalized_map[c] = t.strftime("%H:%M")
            except Exception:
                try:
                    hh, mm = str(c).split(":")
                    normalized_map[c] = f"{int(hh):02d}:{int(mm):02d}"
                except Exception:
                    raise ValueError(f"時刻列の形式が不正です: {c}")

        df = df.rename(columns=normalized_map)

        self.pv_time_cols = sorted(
            [c for c in df.columns if c not in ["月", "日"]],
            key=lambda x: pd.to_datetime(x, format="%H:%M", errors="coerce")
        )

        df["月"] = pd.to_numeric(df["月"], errors="coerce").astype("Int64")
        df["日"] = pd.to_numeric(df["日"], errors="coerce").astype("Int64")

        for c in self.pv_time_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

        df = df.dropna(subset=["月", "日"]).copy()
        df["月"] = df["月"].astype(int)
        df["日"] = df["日"].astype(int)

        return df

"""
if anchor not in text:
    raise SystemExit("patch failed: _load_excel anchor not found")
text = text.replace(anchor, insert + anchor, 1)

# 5. get_pv_profile_for_date を追加
anchor = """    def show_summary(self):
"""
insert = """    def get_pv_profile_for_date(self, target_date):
        if self.pv_norm_df is None:
            return None

        month = target_date.month
        day = target_date.day

        row = self.pv_norm_df[
            (self.pv_norm_df["月"] == month) & (self.pv_norm_df["日"] == day)
        ]

        if row.empty:
            return None

        try:
            factor = float(self.pv_factor_var.get())
        except Exception:
            factor = 100.0
            self.pv_factor_var.set(factor)

        values = row.iloc[0][self.pv_time_cols].astype(float).values * factor
        return pd.DataFrame({
            "time": self.pv_time_cols,
            "pv_kw": values
        })

"""
if anchor not in text:
    raise SystemExit("patch failed: show_summary anchor not found")
text = text.replace(anchor, insert + anchor, 1)

# 6. show_selected_day を丸ごと置換
start = text.find("    def show_selected_day(self):")
if start == -1:
    raise SystemExit("patch failed: show_selected_day start not found")

end = text.find("    def show_monthly_usage(self):", start)
if end == -1:
    raise SystemExit("patch failed: show_selected_day end anchor not found")

new_block = """    def show_selected_day(self):
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

        work = self.df[self.df["date"] == target_date].copy()
        if work.empty:
            messagebox.showwarning("データなし", f"{date_str} のデータはありません。")
            return

        work["sort_key"] = pd.to_datetime(work["time"], format="%H:%M", errors="coerce")
        work = work.sort_values("sort_key")

        day_total_kwh = work["kwh"].sum()
        day_avg_kw = work["kw"].mean()
        day_max_kw = work["kw"].max()
        holiday_label = "休祝日" if is_holiday_or_weekend(pd.Timestamp(target_date)) else "平日"

        pv_df = None
        merged = work[["time", "kw", "kwh"]].copy()

        if self.use_pv_var.get() and self.pv_norm_df is not None:
            pv_df = self.get_pv_profile_for_date(target_date)
            if pv_df is not None:
                merged = merged.merge(pv_df, on="time", how="left")
                merged["pv_kw"] = merged["pv_kw"].fillna(0.0)
                merged["net_kw"] = merged["kw"] - merged["pv_kw"]
                merged["pv_kwh"] = merged["pv_kw"] * 0.5
                merged["net_kwh"] = merged["net_kw"] * 0.5
            else:
                merged["pv_kw"] = 0.0
                merged["net_kw"] = merged["kw"]
                merged["pv_kwh"] = 0.0
                merged["net_kwh"] = merged["kwh"]
        else:
            merged["pv_kw"] = 0.0
            merged["net_kw"] = merged["kw"]
            merged["pv_kwh"] = 0.0
            merged["net_kwh"] = merged["kwh"]

        pv_total_kwh = merged["pv_kwh"].sum()
        pv_max_kw = merged["pv_kw"].max()
        net_total_kwh = merged["net_kwh"].sum()
        net_max_kw = merged["net_kw"].max()

        self.text.delete("1.0", "end")
        self.log(f"=== 指定日グラフ: {date_str} ===")
        self.log(f"区分: {holiday_label}")
        self.log(f"日使用電力量: {day_total_kwh:,.1f} kWh")
        self.log(f"平均需要電力: {day_avg_kw:,.2f} kW")
        self.log(f"最大需要電力: {day_max_kw:,.2f} kW")

        if self.use_pv_var.get() and self.pv_norm_df is not None:
            self.log(f"PV係数: {float(self.pv_factor_var.get()):,.2f}")
            self.log(f"疑似PV発電量: {pv_total_kwh:,.1f} kWh")
            self.log(f"疑似PV最大出力: {pv_max_kw:,.2f} kW")
            self.log(f"差引後ネット電力量: {net_total_kwh:,.1f} kWh")
            self.log(f"差引後ネット最大需要: {net_max_kw:,.2f} kW")

            if pv_df is None:
                self.log("※ PVプロファイルに該当する月日がないため、PVは反映されていません。")

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

"""
text = text[:start] + new_block + text[end:]

# 7. export_csv に指定日PV出力を追加
old = """        monthly_time_profile.to_csv(out_dir / "izumi_monthly_time_profile.csv", index=False, encoding="utf-8-sig")

        messagebox.showinfo("出力完了", f"CSVを {out_dir.resolve()} に出力しました。")
"""
new = """        monthly_time_profile.to_csv(out_dir / "izumi_monthly_time_profile.csv", index=False, encoding="utf-8-sig")

        date_str = self.date_entry.get().strip()
        if date_str:
            try:
                target_date = pd.to_datetime(date_str).date()
                day_df = self.df[self.df["date"] == target_date].copy()
                if not day_df.empty:
                    day_df["sort_key"] = pd.to_datetime(day_df["time"], format="%H:%M", errors="coerce")
                    day_df = day_df.sort_values("sort_key")[["datetime", "date", "time", "kwh", "kw"]].copy()

                    if self.use_pv_var.get() and self.pv_norm_df is not None:
                        pv_df = self.get_pv_profile_for_date(target_date)
                        if pv_df is not None:
                            day_df = day_df.merge(pv_df, on="time", how="left")
                            day_df["pv_kw"] = day_df["pv_kw"].fillna(0.0)
                        else:
                            day_df["pv_kw"] = 0.0
                    else:
                        day_df["pv_kw"] = 0.0

                    day_df["pv_kwh"] = day_df["pv_kw"] * 0.5
                    day_df["net_kw"] = day_df["kw"] - day_df["pv_kw"]
                    day_df["net_kwh"] = day_df["kwh"] - day_df["pv_kwh"]

                    out_name = f"izumi_selected_day_with_pv_{target_date.strftime('%Y%m%d')}.csv"
                    day_df.to_csv(out_dir / out_name, index=False, encoding="utf-8-sig")
            except Exception:
                pass

        messagebox.showinfo("出力完了", f"CSVを {out_dir.resolve()} に出力しました。")
"""
if old not in text:
    raise SystemExit("patch failed: export_csv block not found")
text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("patched app.py successfully")
