# -*- coding: utf-8 -*-
import argparse

from solar_processing import extract_type1_to_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-o", "--output", default="solar.csv")
    args = parser.parse_args()

    result = extract_type1_to_csv(args.input, args.output)
    print("header_row:", result["header_row"])
    print("normalized time_cols:", result["time_cols"])
    print("rows:", result["rows"])
    print("saved:", result["output_path"])


if __name__ == "__main__":
    main()
