# -*- coding: utf-8 -*-
import argparse

from solar_processing import normalize_solar_to_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-o", "--output", default="solar_norm.csv")
    args = parser.parse_args()

    result = normalize_solar_to_csv(args.input, args.output)
    print("max irradiance =", result["max_val"])
    print("saved:", result["output_path"])


if __name__ == "__main__":
    main()
