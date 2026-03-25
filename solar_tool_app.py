import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from solar_processing import (
    extract_type1_to_csv,
    interpolate_30min_to_csv,
    normalize_solar_to_csv,
)


class SolarToolApp:
    def __init__(self, parent, on_back=None):
        self.parent = parent
        self.root = parent.winfo_toplevel()
        self.on_back = on_back

        self.root.title("日射量データ処理ツール")
        self.root.geometry("980x720")

        self.source_var = tk.StringVar()
        self.extract_output_var = tk.StringVar()
        self.interpolate_input_var = tk.StringVar()
        self.interpolate_output_var = tk.StringVar()
        self.normalize_input_var = tk.StringVar()
        self.normalize_output_var = tk.StringVar()
        self.status_var = tk.StringVar(value="未実行")

        self.main = ttk.Frame(parent, padding=10)
        self.main.pack(fill="both", expand=True)
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self.main)
        top.pack(fill="x", pady=(0, 8))

        ttk.Label(top, text="日射量データ処理", font=("Meiryo UI", 12, "bold")).pack(side="left")
        if self.on_back is not None:
            ttk.Button(top, text="ツール選択へ戻る", command=self.on_back).pack(side="right")

        ttk.Label(self.main, text="NEDO日射量データから 抽出 → 30分補完 → 正規化 を行います。").pack(anchor="w")

        source_frame = ttk.LabelFrame(self.main, text="元データ", padding=8)
        source_frame.pack(fill="x", pady=(10, 8))
        ttk.Label(source_frame, text="Excel/ZIP").grid(row=0, column=0, sticky="w")
        ttk.Entry(source_frame, textvariable=self.source_var, width=90).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(source_frame, text="参照", command=self.choose_source).grid(row=0, column=2)
        ttk.Button(source_frame, text="一括実行", command=self.run_all).grid(row=0, column=3, padx=(8, 0))
        source_frame.columnconfigure(1, weight=1)

        extract_frame = ttk.LabelFrame(self.main, text="1. type=1抽出", padding=8)
        extract_frame.pack(fill="x", pady=6)
        ttk.Label(extract_frame, text="出力CSV").grid(row=0, column=0, sticky="w")
        ttk.Entry(extract_frame, textvariable=self.extract_output_var, width=90).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(extract_frame, text="保存先", command=self.choose_extract_output).grid(row=0, column=2)
        ttk.Button(extract_frame, text="抽出実行", command=self.run_extract).grid(row=0, column=3, padx=(8, 0))
        extract_frame.columnconfigure(1, weight=1)

        interpolate_frame = ttk.LabelFrame(self.main, text="2. 30分補完", padding=8)
        interpolate_frame.pack(fill="x", pady=6)
        ttk.Label(interpolate_frame, text="入力CSV").grid(row=0, column=0, sticky="w")
        ttk.Entry(interpolate_frame, textvariable=self.interpolate_input_var, width=90).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(interpolate_frame, text="参照", command=self.choose_interpolate_input).grid(row=0, column=2)
        ttk.Label(interpolate_frame, text="出力CSV").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(interpolate_frame, textvariable=self.interpolate_output_var, width=90).grid(row=1, column=1, sticky="ew", padx=6, pady=(6, 0))
        ttk.Button(interpolate_frame, text="保存先", command=self.choose_interpolate_output).grid(row=1, column=2, pady=(6, 0))
        ttk.Button(interpolate_frame, text="補完実行", command=self.run_interpolate).grid(row=0, column=3, rowspan=2, padx=(8, 0))
        interpolate_frame.columnconfigure(1, weight=1)

        normalize_frame = ttk.LabelFrame(self.main, text="3. 正規化", padding=8)
        normalize_frame.pack(fill="x", pady=6)
        ttk.Label(normalize_frame, text="入力CSV").grid(row=0, column=0, sticky="w")
        ttk.Entry(normalize_frame, textvariable=self.normalize_input_var, width=90).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(normalize_frame, text="参照", command=self.choose_normalize_input).grid(row=0, column=2)
        ttk.Label(normalize_frame, text="出力CSV").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(normalize_frame, textvariable=self.normalize_output_var, width=90).grid(row=1, column=1, sticky="ew", padx=6, pady=(6, 0))
        ttk.Button(normalize_frame, text="保存先", command=self.choose_normalize_output).grid(row=1, column=2, pady=(6, 0))
        ttk.Button(normalize_frame, text="正規化実行", command=self.run_normalize).grid(row=0, column=3, rowspan=2, padx=(8, 0))
        normalize_frame.columnconfigure(1, weight=1)

        ttk.Label(self.main, textvariable=self.status_var).pack(anchor="e", pady=(8, 4))

        self.log_text = tk.Text(self.main, wrap="word", height=18)
        self.log_text.pack(fill="both", expand=True)

    def log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def choose_source(self):
        path = filedialog.askopenfilename(
            title="日射量データを選択",
            filetypes=[("Excel or Zip", "*.xlsx;*.zip"), ("Excel", "*.xlsx"), ("Zip", "*.zip")],
        )
        if not path:
            return

        self.source_var.set(path)
        base = Path(path)
        self.extract_output_var.set(str(base.with_name(base.stem + "_solar.csv")))
        self.interpolate_input_var.set(self.extract_output_var.get())
        self.interpolate_output_var.set(str(base.with_name(base.stem + "_solar_30min.csv")))
        self.normalize_input_var.set(self.interpolate_output_var.get())
        self.normalize_output_var.set(str(base.with_name(base.stem + "_solar_norm.csv")))

    def choose_extract_output(self):
        self._choose_save_csv(self.extract_output_var, "抽出結果の保存先")

    def choose_interpolate_input(self):
        self._choose_open_csv(self.interpolate_input_var, "30分補完の入力CSV")

    def choose_interpolate_output(self):
        self._choose_save_csv(self.interpolate_output_var, "30分補完結果の保存先")

    def choose_normalize_input(self):
        self._choose_open_csv(self.normalize_input_var, "正規化の入力CSV")

    def choose_normalize_output(self):
        self._choose_save_csv(self.normalize_output_var, "正規化結果の保存先")

    def _choose_open_csv(self, variable, title):
        path = filedialog.askopenfilename(title=title, filetypes=[("CSV", "*.csv")])
        if path:
            variable.set(path)

    def _choose_save_csv(self, variable, title):
        path = filedialog.asksaveasfilename(
            title=title,
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=Path(variable.get()).name if variable.get() else None,
        )
        if path:
            variable.set(path)

    def run_extract(self):
        source = self.source_var.get().strip()
        output = self.extract_output_var.get().strip()
        if not source or not output:
            messagebox.showwarning("入力不足", "元データと抽出結果の保存先を指定してください。")
            return False

        try:
            result = extract_type1_to_csv(source, output)
            self.interpolate_input_var.set(output)
            if not self.interpolate_output_var.get().strip():
                self.interpolate_output_var.set(str(Path(output).with_name(Path(output).stem + "_30min.csv")))
            self.status_var.set("抽出完了")
            self.log("=== type=1抽出 ===")
            self.log(f"header_row: {result['header_row']}")
            self.log(f"rows: {result['rows']}")
            self.log(f"saved: {result['output_path']}")
            return True
        except Exception as exc:
            messagebox.showerror("抽出エラー", str(exc))
            return False

    def run_interpolate(self):
        input_path = self.interpolate_input_var.get().strip()
        output_path = self.interpolate_output_var.get().strip()
        if not input_path or not output_path:
            messagebox.showwarning("入力不足", "30分補完の入力CSVと出力先を指定してください。")
            return False

        try:
            result = interpolate_30min_to_csv(input_path, output_path)
            self.normalize_input_var.set(output_path)
            if not self.normalize_output_var.get().strip():
                self.normalize_output_var.set(str(Path(output_path).with_name(Path(output_path).stem + "_norm.csv")))
            self.status_var.set("30分補完完了")
            self.log("=== 30分補完 ===")
            self.log(f"rows: {result['rows']}")
            self.log(f"cols: {result['cols']}")
            self.log(f"saved: {result['output_path']}")
            return True
        except Exception as exc:
            messagebox.showerror("30分補完エラー", str(exc))
            return False

    def run_normalize(self):
        input_path = self.normalize_input_var.get().strip()
        output_path = self.normalize_output_var.get().strip()
        if not input_path or not output_path:
            messagebox.showwarning("入力不足", "正規化の入力CSVと出力先を指定してください。")
            return False

        try:
            result = normalize_solar_to_csv(input_path, output_path)
            self.status_var.set("正規化完了")
            self.log("=== 正規化 ===")
            self.log(f"max irradiance: {result['max_val']}")
            self.log(f"rows: {result['rows']}")
            self.log(f"saved: {result['output_path']}")
            return True
        except Exception as exc:
            messagebox.showerror("正規化エラー", str(exc))
            return False

    def run_all(self):
        if not self.run_extract():
            return
        if not self.run_interpolate():
            return
        if not self.run_normalize():
            return

        self.status_var.set("一括実行完了")
        if self.on_back is not None:
            should_return = messagebox.askyesno(
                "完了",
                "抽出・30分補完・正規化が完了しました。\nツール選択画面へ戻りますか？",
            )
            if should_return:
                self.on_back()
                return
        else:
            messagebox.showinfo("完了", "抽出・30分補完・正規化が完了しました。")


def main():
    root = tk.Tk()
    SolarToolApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
