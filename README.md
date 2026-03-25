# Izumi Park Town Analysis CLI

## 概要
このリポジトリには、用途の異なる 2 系統のツールが含まれています。

1. `app.py`
   泉パークタウン向けの 30 分値電力データ解析 GUI アプリ
2. `extract_solar_type1.py` など
   NEDO 日射量データを抽出・補完・正規化する補助ツール群

現在の主アプリは `app.py` です。

## 主アプリ: 30分値電力解析ツール

### できること
- Excel / ZIP の 30 分値電力データを読み込む
- 読み込んだデータを SQLite (`izumi_power.db`) に保存する
- 同一ファイルの重複登録をファイルハッシュで回避する
- 年間概要、平均日負荷、指定日グラフ、月別集計、ヒートマップを表示する
- 正規化済み PV プロファイル CSV / ZIP を読み込み、疑似 PV と受電点を重ねて表示する
- 集計結果やグラフ元データを `output/` に CSV 出力する

### 主なファイル
- `app.py`: メイン GUI アプリ
- `db.py`: SQLite 初期化、データ保存、読込処理
- `izumi_power.db`: ローカル保存用データベース
- `output/`: アプリの CSV 出力先

### 起動方法
```bash
python app.py
```

### 主アプリの入力
- 30 分値電力データ: `.xlsx` または `.zip`
- PV プロファイル: 正規化済み `.csv` または `.zip`

### 主アプリの主な画面機能
- `年間概要`
- `日別負荷`
- `指定日グラフ`
- `月別集計`
- `月別 平日/休祝日平均`
- `ヒートマップ`
- `月別時刻プロファイル比較`

## 補助ツール: NEDO日射量データ処理

### 役割
NEDO 形式の日射量データから、PV プロファイル作成用の中間データを作るためのツール群です。

### ファイル構成
- `extract_solar_type1.py`: type=1 の日射量を抽出
- `interpolate_solar_30min.py`: 30 分値へ補完
- `normalize_solar.py`: 0〜1 に正規化
- `run_extract_gui.py`: 抽出だけを GUI で実行する簡易ツール

### 基本手順
1. 抽出
```bash
python extract_solar_type1.py <入力> -o test.csv
python extract_solar_type1.py 日射量データ.zip -o test.csv
```

2. 補完
```bash
python interpolate_solar_30min.py test.csv -o test_30min.csv
```

3. 正規化
```bash
python normalize_solar.py test_30min.csv -o test_30min_norm.csv
```

### 出力イメージ
- 列構成: `月`, `日`, `0:00`, `0:30`, ..., `23:30`
- 値: `0` から `1` の正規化値

## 依存ライブラリ
`requirements.txt` に以下を記載しています。

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
- `csv` と `zip` は `.gitignore` で除外しています
- 過去の修正スクリプトやバックアップは `archive/` に退避しています
- Excel ファイルを開いたままの状態や OneDrive 同期中は、読込に失敗することがあります
