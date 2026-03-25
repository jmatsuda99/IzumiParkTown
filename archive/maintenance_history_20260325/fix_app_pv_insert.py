from pathlib import Path
import re

path = Path("app.py")
text = path.read_text(encoding="utf-8")

start = text.find("    def load_pv_profile_file(self):")
if start == -1:
    raise SystemExit("load_pv_profile_file not found")

end = text.find("    def show_db_list(self):", start)
if end == -1:
    raise SystemExit("show_db_list not found")

new_block = """    def load_pv_profile_file(self):
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
                self.pv_time_cols = [c for c in self.pv_norm_df.columns if c not in ["月", "日"]]

                self.log("=== PV既存DB読込 ===")
                self.log(f"id={dataset_id} file={source_name}")
                self.status_var.set(f"PV DB読込: {dataset_id}")
                return

            # 新規読込
            self.pv_norm_df = self._load_pv_profile_dataset(Path(path))
            self.pv_profile_file = path
            self.pv_time_cols = [c for c in self.pv_norm_df.columns if c not in ["月", "日"]]

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

"""

text = text[:start] + new_block + text[end:]
path.write_text(text, encoding="utf-8")

print("patched load_pv_profile_file successfully")
