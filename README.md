# Izumi Park Town Analysis CLI

## 概要
このリポジトリには、同じプロジェクト内で使う 2 つの GUI ツールがあります。

1. `30分値電力解析ツール`
   電力データの読込、DB保存、集計、グラフ表示、PV 重ね合わせを行う
2. `日射量データ処理ツール`
   NEDO 日射量データの抽出、30分補完、正規化を行う

現在は `launcher.py` を正式な起動入口としており、起動時に GUI でツールを選択できます。

## 起動方法

### 正式な起動入口
```bash
python launcher.py
```

### 補助的な単独起動
電力解析ツールだけを直接開く場合:

```bash
python app.py
```

日射量処理ツールだけを直接開く場合:

```bash
python run_extract_gui.py
```

## ツール構成

### 1. 30分値電力解析ツール

主なファイル:
- `app.py`: 電力解析 GUI 本体
- `db.py`: SQLite 初期化、保存、読込
- `analysis_utils.py`: 集計・分析用の共通処理
- `plot_helpers.py`: グラフ描画ヘルパー

できること:
- Excel / ZIP の 30 分値電力データを読み込む
- 読み込んだデータを SQLite (`izumi_power.db`) に保存する
- 年間概要、日別負荷、指定日グラフ、月別集計、ヒートマップを表示する
- 正規化済み PV プロファイル CSV / ZIP を読み込み、疑似 PV と受電点を重ねて表示する
- 集計結果やグラフ元データを `output/` に CSV 出力する

入力:
- 30 分値電力データ: `.xlsx` または `.zip`
- PV プロファイル: 正規化済み `.csv` または `.zip`

### 2. 日射量データ処理ツール

主なファイル:
- `solar_tool_app.py`: 日射量処理 GUI
- `solar_processing.py`: 抽出、30分補完、正規化の共通処理
- `extract_solar_type1.py`: 抽出 CLI
- `interpolate_solar_30min.py`: 30分補完 CLI
- `normalize_solar.py`: 正規化 CLI

できること:
- NEDO 形式データから `type=1` を抽出
- 時系列を 30 分値へ補完
- 全体最大値で正規化
- GUI から一括実行

基本手順:
1. 抽出
```bash
python extract_solar_type1.py <入力> -o test.csv
```

2. 30分補完
```bash
python interpolate_solar_30min.py test.csv -o test_30min.csv
```

3. 正規化
```bash
python normalize_solar.py test_30min.csv -o test_30min_norm.csv
```

出力イメージ:
- 列構成: `月`, `日`, `0:00`, `0:30`, ..., `23:30`
- 値: `0` から `1` の正規化値

## 依存ライブラリ
`requirements.txt`

- `pandas`
- `openpyxl`
- `matplotlib`
- `numpy`
- `jpholiday`

インストール例:

```bash
pip install -r requirements.txt
```

## 補足
- `csv`、`zip`、`db` は `.gitignore` で除外しています
- 過去の修正スクリプトやバックアップは `archive/` に退避しています
- Excel ファイルを開いたままの状態や OneDrive 同期中は、読込に失敗することがあります

## 変更後の確認
変更後の最低限の確認手順は [docs/regression_checklist.md](/d:/Deltabox/OneDrive%20-%20Delta%20Electronics,%20Inc/020_TOOL/070_IzumiParkTown/izumi_park_analysis_cli/docs/regression_checklist.md) にまとめています。
