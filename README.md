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

## プラグイン構成（三層）

Adobe Animation Composerを技術UXの参照点とする。ただしAnimation Composerには
存在しない「重量OFX処理層」がDVE800には必須。

| 層 | 役割 | 実装形態 |
|---|---|---|
| コックピット層 | FAM文脈判断・審査ノート取り込み・粒度の最終決定 | ローカルFastAPI + ブラウザUI |
| 軽量プリセット層 | 字幕演出・トス・タイトル等、ノード合成で足りるもの | Fusion macro / .setting（コンパイル不要） |
| 重量OFX層 | モザイク検出座標の読み込み、強度パラメータのリアルタイム露出 | C++ OFXバンドル（Gyroflowと同型の設計） |

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

## 担げるロマン砲

DVE800は超兵器を作らない。担げるロマン砲を作る。

NSFW領域のモザイク自動検出・音声補正・危険ワード書き起こしといった要素技術は、
すでにOSSコミュニティで急速に充実してきている（DeepMosaics, lada, RVC等）。
しかし、それらは共通して「モデルの出力が最終解」という設計思想を採用しており、
プラットフォーム審査・自主規制団体審査のような、人間の心象がタイムコード単位で
局所的に返ってくる実運用フローには噛み合わない。

DVE800は、検出モデルは借りるが、強度の最終決定権は常にオペレーターの手元に残す。
理由は単純で、演者としても監督としても現場を経験した人間が設計したツールだから、
「完全自動は無理」という一次データに基づいている。

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

> 無料版DaVinci Resolveでのサードパーティ OpenFXプラグインのロード動作は実機確認済み
> （Gyroflow.ofx.bundle、2026-07-02）。詳細は `docs/verification_log/` を参照。

---

## 開発体制について

DVE800は、開発者本人（TikToker/演者）が実際の現場——NSFW、技術系SFW、音楽歌唱、
屋外ダンスロケなど多様な撮影・配信シーンで日常的に使うことを前提にした、
現場駆動・ビジョン駆動の開発です。

開発リソースは投げ銭とジャンクボックスの部材で賄われています。そのため：

- 開発が停止・放置される期間が発生することを前提にしてください
- 800シリーズが広く展開されているように見えるかもしれませんが、
  「広く展開する計画がある」からではなく、投げ銭とジャンク箱ガチャで
  作れるところから作っているだけです
- 過剰な期待はせず、気長に、生あたたかく見守ってください（投げ銭してくれると嬉しいです）

---

## 実装状況（2026-07-02時点）

このプロジェクトは現在**設計段階シーズン**にあります。設計ドキュメントとコード骨格を
マイクロラピッドサイクルで積み上げている途中で、まだエンドツーエンドで起動できる状態
ではありません。インストール手順・クイックスタートは、動くエントリポイントが揃うまで
このREADMEには書きません（書いても実行できないコマンドを載せる意味がないため）。

| Module | 状態 | 補足 |
|---|---|---|
| Module 1: whisper_discovery | ✅ 実装・テスト済み | バックエンド自動検出ロジック。`tests/test_dve800.py`でカバー |
| Module 2: whisper_installer | ⛔ 未着手 | ディレクトリ未作成。設計のみ（AGENTS.md記載） |
| Module 3: aqc_local | 🔶 基本テスト済み・設計見直し検討中 | `FAMVocab` / `AQCLocal`。`tests/test_dve800.py`で基本動作はカバー済みだが、設計フィードバックを受けて構造見直しを検討中。インターフェースは変わる可能性がある。**FAM理論自体もフルサイズではなくトイモデルでの検証段階で、ツールレベルのFAM実装はまだ調整中** |
| Module 4: dav_api | 🔶 コード実装済み・実機未検証 | `DaVinciBridge`クラスは実装済みだが、実Resolve環境での動作確認・テストは未実施 |
| Module 5: mcp_server | ⛔ 未着手 | ディレクトリ未作成 |
| Module 6: cockpit | ⛔ 未着手（設計のみ） | [docs/ux_philosophy.md](docs/ux_philosophy.md)参照 |
| Module 7: compliance_review | 🔶 型定義・レジストリ骨格のみ | `ReviewNote`型・`ReviewFormatAdapter`プロトコルは実装済み。STL/SRT/Freeformアダプタ、`shot_matcher`の実処理は未実装（呼ぶと`NotImplementedError`） |
| Module 8: mosaic_detection | ⛔ 未着手（設計のみ） | ライセンス隔離方針（AGPL-3.0との境界）のみ確定。コードなし |
| 軽量プリセット層（`fusion_presets/`） | ⛔ 未着手 | |
| 重量OFX層（`ofx/mosaic_render/`） | ⛔ DVE800自前実装は未着手 | 参考として、外部OFX（`Gyroflow.ofx.bundle`）が無料版Resolveでロードできることは実機確認済み（[docs/verification_log/20260702.md](docs/verification_log/20260702.md)）。これはDVE800自体の動作保証ではない |

インストール・クイックスタートは、最初のモジュール（Whisper Discovery → AQC-Local の
最小縦串）がCLIから実行できるようになった時点で、このセクションを置き換えて記載します。

### FAM実装バリエーションの状況

FAMは接続先によって複数の実装バリエーションがあり、それぞれ検証段階が異なります。

| バリエーション | 状態 | 補足 |
|---|---|---|
| FAM over AQC（フルレベル） | 🔶 過去に動作実績あり・現在は利用不可 | 過去のある環境で一度フル動作した実績があるが、現在の情勢とサプライ事情により同環境を再現できず、現状は利用不可。当時の構成をサルベージ（復旧）する必要がある |
| FAM over MCP | 🔶 トイモデル状態 | 概念検証レベル。Module 5 (`mcp_server`) 自体はまだディレクトリ未作成で、実装はこれから |

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
