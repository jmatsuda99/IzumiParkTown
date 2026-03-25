# -*- coding: utf-8 -*-
import argparse
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-o", "--output", default="solar_30min.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)

    hour_cols = [f"{h}:00" for h in range(24)]
    for c in hour_cols:
        if c not in df.columns:
            raise KeyError(f"列が見つかりません: {c}")

    out = df[["月", "日"]].copy()

    for h in range(24):
        c0 = f"{h}:00"
        v0 = pd.to_numeric(df[c0], errors="coerce")
        out[c0] = v0

        c30 = f"{h}:30"
        if h < 23:
            c1 = f"{h+1}:00"
            v1 = pd.to_numeric(df[c1], errors="coerce")
            out[c30] = (v0 + v1) / 2.0
        else:
            out[c30] = 0.0

    ordered_cols = ["月", "日"]
    for h in range(24):
        ordered_cols += [f"{h}:00", f"{h}:30"]

    out = out[ordered_cols]
    out.to_csv(args.output, index=False, encoding="utf-8-sig")

    print("saved:", args.output)
    print("rows:", len(out))
    print("cols:", len(out.columns))

if __name__ == "__main__":
    main()
