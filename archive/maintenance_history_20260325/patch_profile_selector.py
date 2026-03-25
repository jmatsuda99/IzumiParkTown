from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

# 1) __init__ に表示選択変数を追加
old = """        self.pv_factor_var = tk.DoubleVar(value=100.0)
        self.use_pv_var = tk.BooleanVar(value=True)

        self._build_ui()
"""
new = """        self.pv_factor_var = tk.DoubleVar(value=100.0)
        self.use_pv_var = tk.BooleanVar(value=True)

        self.show_load_var = tk.BooleanVar(value=True)
        self.show_pv_profile_var = tk.BooleanVar(value=True)
        self.show_receive_var = tk.BooleanVar(value=True)

        self._build_ui()
"""
if old in text:
    text = text.replace(old, new, 1)

# 2) UI にチェックボックス追加
old = """        ttk.Button(selector, text="選択月プロファイル表示", command=self.show_monthly_time_profile).grid(
            row=2, column=2, sticky="ew", pady=4
        )
        ttk.Button(selector, text="月選択を全解除", command=self.clear_month_selection).grid(
            row=3, column=2, sticky="ew", pady=4
        )
        ttk.Button(selector, text="月を全選択", command=self.select_all_months).grid(
            row=4, column=2, sticky="ew", pady=4
        )

        selector.columnconfigure(0, weight=1)
"""
new = """        ttk.Label(selector, text="表示系列").grid(row=2, column=2, sticky="w", pady=(8, 0))
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
"""
if old in text:
    text = text.replace(old, new, 1)

# 3) PV長形式化ヘルパーを追加
anchor = """    def get_pv_profile_for_date(self, target_date):
"""
insert = """
    def build_pv_long_df(self):
        if self.pv_norm_df is None or self.pv_norm_df.empty:
            return pd.DataFrame()

        try:
            factor = float(self.pv_factor_var.get())
        except Exception:
            factor = 100.0
            self.pv_factor_var.set(factor)

        time_cols = [c for c in self.pv_norm_df.columns if c not in ["月", "日"]]
        records = []

        for _, row in self.pv_norm_df.iterrows():
            month = int(row["月"])
            day = int(row["日"])

            try:
                dt0 = pd.Timestamp(year=2025, month=month, day=day)
            except Exception:
                continue

            is_holiday = is_holiday_or_weekend(dt0)

            for t in time_cols:
                try:
                    pv_kw = float(row[t]) * factor
                except Exception:
                    pv_kw = 0.0

                records.append({
                    "month_num": month,
                    "month": f"2025-{month:02d}",
                    "day": day,
                    "time": t,
                    "pv_kw": pv_kw,
                    "is_holiday": is_holiday,
                })

        pv_long = pd.DataFrame(records)
        if pv_long.empty:
            return pv_long

        pv_long["sort_key"] = pd.to_datetime(pv_long["time"], format="%H:%M", errors="coerce")
        return pv_long

"""
if anchor in text and "def build_pv_long_df(self):" not in text:
    text = text.replace(anchor, insert + anchor, 1)

# 4) show_monthly_time_profile を置換
start = text.find("    def show_monthly_time_profile(self):")
if start == -1:
    raise SystemExit("show_monthly_time_profile not found")

end = text.find("    def show_heatmap(self):", start)
if end == -1:
    raise SystemExit("show_heatmap anchor not found")

new_block = """    def show_monthly_time_profile(self):
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

        load_work = self.df.copy()
        if daytype == "平日":
            load_work = load_work[load_work["is_holiday"] == False]
        elif daytype == "休祝日":
            load_work = load_work[load_work["is_holiday"] == True]
        load_work = load_work[load_work["month"].isin(selected_months)].copy()

        load_profile = (
            load_work.groupby(["month", "time"], as_index=False)["kw"]
            .mean()
        )
        load_profile["sort_key"] = pd.to_datetime(load_profile["time"], format="%H:%M", errors="coerce")

        pv_profile = pd.DataFrame(columns=["month", "time", "pv_kw", "sort_key"])
        if self.pv_norm_df is not None and not self.pv_norm_df.empty:
            pv_long = self.build_pv_long_df()

            if not pv_long.empty:
                if daytype == "平日":
                    pv_long = pv_long[pv_long["is_holiday"] == False]
                elif daytype == "休祝日":
                    pv_long = pv_long[pv_long["is_holiday"] == True]

                pv_long = pv_long[pv_long["month"].isin(selected_months)].copy()

                if not pv_long.empty:
                    pv_profile = (
                        pv_long.groupby(["month", "time"], as_index=False)["pv_kw"]
                        .mean()
                    )
                    pv_profile["sort_key"] = pd.to_datetime(pv_profile["time"], format="%H:%M", errors="coerce")

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
            load_sub = load_profile[load_profile["month"] == month].copy().sort_values("sort_key")
            pv_sub = pv_profile[pv_profile["month"] == month].copy().sort_values("sort_key")

            merged = pd.merge(
                load_sub[["time", "kw", "sort_key"]],
                pv_sub[["time", "pv_kw"]],
                on="time",
                how="left"
            )
            merged["pv_kw"] = merged["pv_kw"].fillna(0.0)
            merged["recv_kw"] = merged["kw"] - merged["pv_kw"]
            merged = merged.sort_values("sort_key")

            load_mean = merged["kw"].mean() if not merged.empty else 0.0
            pv_mean = merged["pv_kw"].mean() if not merged.empty else 0.0
            recv_mean = merged["recv_kw"].mean() if not merged.empty else 0.0

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

        ax.set_title(f"月別時刻プロファイル比較（{daytype}）")
        ax.set_xlabel("Time")
        ax.set_ylabel("kW")
        ax.tick_params(axis="x", rotation=90)
        ax.grid(True)
        ax.legend()
        fig.tight_layout()
        self.draw_figure(fig)

"""
text = text[:start] + new_block + text[end:]

path.write_text(text, encoding="utf-8")
print("patched app.py successfully")
