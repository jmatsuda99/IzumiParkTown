# -*- coding: utf-8 -*-
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

def run():
    file_path = filedialog.askopenfilename(
        title="日射量データを選択",
        filetypes=[("Excel or Zip", "*.xlsx *.zip")]
    )

    if not file_path:
        return

    output = Path(file_path).stem + "_solar.csv"

    try:
        subprocess.run(
            ["python", "extract_solar_type1.py", file_path, "-o", output],
            check=True
        )
        messagebox.showinfo("完了", f"出力完了:\n{output}")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("エラー", f"処理に失敗しました\n{e}")

root = tk.Tk()
root.title("日射量抽出ツール")
root.geometry("320x140")

btn = tk.Button(root, text="ファイル選択して抽出", command=run)
btn.pack(expand=True)

root.mainloop()
