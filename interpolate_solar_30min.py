# -*- coding: utf-8 -*-
import argparse

from solar_processing import interpolate_30min_to_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-o", "--output", default="solar_30min.csv")
    args = parser.parse_args()

    result = interpolate_30min_to_csv(args.input, args.output)
    print("saved:", result["output_path"])
    print("rows:", result["rows"])
    print("cols:", result["cols"])


if __name__ == "__main__":
    main()
