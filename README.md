# DVE800 — Deep Video Engine 800

**自分のマシンでWhisperを動かせば文句ないね？**

- GPUベンダーの言論ポリシー → 関係ない
- CapCutのクラウド審査 → 関係ない
- AdobeのNSFW規約 → 関係ない
- OpenAIのコンテンツポリシー → 関係ない

あなたのマシン、あなたの責任、あなたの言論。

---

## 概要

DVE800は、DaVinci Resolve（無料版）をローカルAIで強化するPython製の動画編集自動化エンジンです。

ZeroRoomLabの800シリーズ（OND800 / SAO800 / FAN800）の**編集レイヤー**として位置づけられ、NSFW・専門ドメイン・日本語特化コンテンツの制作ワークフローを完全ローカルで自動化します。

```
OND800  → 撮る（NDIマルチカメラ）
SAO800  → 流す（OBS配信母艦）
FAN800  → 刻む（ESP32 BLEメッシュ・樽）
DVE800  → 編む（Deep Video Engine）← ここ
```

---

## なぜDVE800か

CapCutはスマホ・クラウド前提のネタ動画量産ツールです。Adobeは広告代理店のSFW制作向けです。DaVinci公式にAI自動化はありません。

DVE800が埋めるのはその空白です：

| | CapCut | Adobe | DVE800 |
|---|---|---|---|
| ローカル完結 | ✗ | ✗ | ✅ |
| NSFW素材 | BAN | グレー | ✅ |
| 日本語形態素 | 雑 | 雑 | FAMで特化 |
| ドメイン語彙 | 汎用のみ | 汎用のみ | 話者別FAM |
| DaVinci連携 | ✗ | ✗ | ✅ |
| 価格 | 無料/サブスク | 高額サブスク | OSS無料 |

---

## アーキテクチャ

```
素材（映像・音声）
    ↓
[Module 1] Whisper Discovery   既存Whisperを環境検出
    ↓（なければ）
[Module 2] Whisper Installer   Whisper-Lを自動取得・設定
    ↓
[Module 3] AQC-Local           FAM多義性マップ生成・管理
           話者別ベクトルDB（ChromaDB）
           initial_prompt動的生成
    ↓
Whisper-L  音声書き起こし（FAMコンテキスト注入済み）
    ↓
[Module 4] DaVinci API Bridge  タイムライン自動構築
           SRT自動インポート
           カット・マーカー・カラー適用
    ↓
[Module 5] MCP Server          PSYCHO-Py800MCP統合口
                               外部エージェント連携
```

### FAM多義性マップとは

話者のSNS投稿群から、語彙がどのジャンル・文脈で使われているかを抽出したJSON構造体です。

```json
{
  "speaker": "K_chachamaru",
  "lexicon": {
    "SAO": {
      "branches": {
        "tech_hardware": {"weight": 0.7, "signals": ["800", "OBS", "NDI"]},
        "anime_ref":     {"weight": 0.25, "signals": ["コスプレ", "ギャグ"]}
      }
    },
    "竿": {
      "branches": {
        "nsfw_genre": {"weight": 0.8, "signals": ["BL", "撮影"]},
        "fishing":    {"weight": 0.2, "signals": ["釣り"]}
      }
    }
  }
}
```

このマップをWhisper-Lの`initial_prompt`に動的注入することで、技術用語・NSFW語彙・地域固有名詞・造語が高精度で書き起こされます。

**Whisper-Lが必須な理由：** tiny/base/small/mediumはinitial_promptの後半を無視します。Largeモデルのみ長文コンテキストを有効に消化できます。

---

## 800シリーズにおける思想的位置づけ

DVE800はOLYMPIA G-8000Sの系譜を継ぐローカル編集エンジンです。

昭和のアナログ映像編集機が「素材をプラットフォームに渡さず手元で処理する」思想を持っていたように、DVE800はあなたのマシンの上でのみ動作します。

```
OLYMPIA G-8000S（昭和）：アナログ回路でローカル処理
DVE800（現代）          ：ローカルAIでローカル処理

どちらも：SaaSが介入しない / 素材がネットに出ない
```

AQC-Localは、かつてGPTs SDK 3.5が持っていた「サードパーティが注意関数にLoRA的介入をする」機能の精神的後継です。ベンダーが封鎖したその機能を、ローカルWhisperとFAM階層で再実装します。責任はDVE800を動かすあなたにあります。

---

## 動作要件

| 項目 | 最小 | 推奨 |
|---|---|---|
| OS | macOS 12+ / Ubuntu 22.04+ | macOS 15+ / Ubuntu 24.04 |
| Python | 3.10+ | 3.11+ |
| RAM | 8GB | 16GB以上 |
| Whisper | faster-whisper (int8) | Whisper-Large-v3 |
| DaVinci Resolve | 19.x 無料版 | 19.x 無料版 |
| GPU | 不要（CPU動作） | CUDA/Metal対応GPU |

**Raspberry Pi 5対応：** OND800と連携する場合、RPi5側にwhisper-serverを立て、DVE800はLAN越しに投げる構成が現実解です。

---

## インストール

```bash
git clone https://github.com/saitoomituru/DVE800.git
cd DVE800
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# .envを編集してDaVinci Resolveのパスなどを設定
```

---

## クイックスタート

```bash
# Whisper環境を自動検出・セットアップ
python -m dve800.setup

# FAM多義性マップを生成（SNS投稿から）
python -m dve800.aqc_local.build_fam --speaker K_chachamaru

# 動画を処理（書き起こし→タイムライン構築）
python -m dve800 --input ./footage/raw.mp4 --speaker K_chachamaru
```

---

## 800シリーズとの連携

```yaml
# OND800からの映像ソースを直接処理
python -m dve800 --source ndi://OND800 --speaker candy_rubber

# PSYCHO-Py800MCP経由でエージェント制御
# MCPサーバーを起動
python -m dve800.mcp_server
```

---

## ライセンス

Apache License 2.0

Copyright 2026 ZeroRoomLab / 齋藤みつる（ふさもふ）

本ソフトウェアを使用して制作されたコンテンツの内容・適法性・倫理的責任は、すべて運用者に帰属します。ZeroRoomLabおよび開発者はコンテンツに対する責任を負いません。

---

## 関連プロジェクト（800シリーズ）

- [OND800](https://github.com/saitoomituru/OND800) — OBS NDI Dominator
- [SAO800](https://github.com/saitoomituru/SAO800) — OBS配信母艦拡張
- [FAN800](https://github.com/HIPSTAR-IScompany/FAN800) — ESP32 BLEメッシュ演出エンジン
- [PSYCHO-Py800MCP](https://github.com/saitoomituru/PSYCHO-Py800MCP) — 計測器MCPサーバー

---

*ZeroRoomLab / quantaril.cloud — 山形県高畠町・江戸時代古民家より*
