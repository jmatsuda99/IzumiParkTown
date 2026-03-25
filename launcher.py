# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk


class ToolLauncher:
    def __init__(self, root, power_tool_cls=None, solar_tool_cls=None):
        self.root = root
        self.power_tool_cls = power_tool_cls
        self.solar_tool_cls = solar_tool_cls
        self.root.title("Izumi Park Town Tool Launcher")
        self.root.geometry("1100x760")

        self.container = ttk.Frame(root)
        self.container.pack(fill="both", expand=True)
        self.show_selector()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_selector(self):
        self.clear_container()
        self.root.title("Izumi Park Town Tool Launcher")
        self.root.geometry("1100x760")

        frame = ttk.Frame(self.container, padding=24)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="ツールを選択", font=("Meiryo UI", 18, "bold")).pack(anchor="center", pady=(20, 10))
        ttk.Label(
            frame,
            text="起動する作業ツールを選択してください。作業後は各画面の「ツール選択へ戻る」でこの画面に戻れます。",
        ).pack(anchor="center", pady=(0, 24))

        cards = ttk.Frame(frame)
        cards.pack(expand=True)

        power_card = ttk.LabelFrame(cards, text="30分値電力解析ツール", padding=20)
        power_card.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        ttk.Label(
            power_card,
            text="電力30分値を読込・DB保存し、年間概要、指定日、月別比較、PV重ね合わせを行います。",
            wraplength=320,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))
        ttk.Button(power_card, text="電力解析を開く", command=self.launch_power_tool).pack(anchor="w")

        solar_card = ttk.LabelFrame(cards, text="日射量データ処理ツール", padding=20)
        solar_card.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        ttk.Label(
            solar_card,
            text="NEDO日射量データから type=1 抽出、30分補完、正規化を GUI で実行します。",
            wraplength=320,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))
        ttk.Button(solar_card, text="日射量処理を開く", command=self.launch_solar_tool).pack(anchor="w")

        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)

    def launch_power_tool(self):
        self.clear_container()
        power_tool_cls = self.power_tool_cls
        if power_tool_cls is None:
            from app import IzumiPowerAnalyzer

            power_tool_cls = IzumiPowerAnalyzer
        power_tool_cls(self.container, on_back=self.show_selector)

    def launch_solar_tool(self):
        self.clear_container()
        solar_tool_cls = self.solar_tool_cls
        if solar_tool_cls is None:
            from solar_tool_app import SolarToolApp

            solar_tool_cls = SolarToolApp
        solar_tool_cls(self.container, on_back=self.show_selector)


def main():
    from app import IzumiPowerAnalyzer
    from solar_tool_app import SolarToolApp

    root = tk.Tk()
    ToolLauncher(root, power_tool_cls=IzumiPowerAnalyzer, solar_tool_cls=SolarToolApp)
    root.mainloop()


if __name__ == "__main__":
    main()
