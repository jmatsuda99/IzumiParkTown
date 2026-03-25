# -*- coding: utf-8 -*-
import argparse
import pandas as pd

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-o", "--output", default="solar_norm.csv")
    args = parser.parse_args()

    df = pd.read_csv(args.input)

    # 時刻列を抽出
    time_cols = [c for c in df.columns if ":" in c]

    # 数値化
    for c in time_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # 全体最大値
    max_val = df[time_cols].max().max()

    print("max irradiance =", max_val)

    if max_val == 0 or pd.isna(max_val):
        raise ValueError("最大値が0またはNaNです")

    # 正規化
    df[time_cols] = df[time_cols] / max_val

    df.to_csv(args.output, index=False, encoding="utf-8-sig")

    print("saved:", args.output)

if __name__ == "__main__":
    main()
