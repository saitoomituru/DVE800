# DVE800 設計メモ

作成: 2026-06-25  
著者: ZeroRoomLab / 齋藤みつる（ふさもふ）

---

## なぜDVE800を作るか

### SaaS編集ツールの限界

| ツール | 限界 |
|---|---|
| CapCut | NSFW素材BAN・クラウド依存・日本語形態素が雑・スマホ量産向け |
| Adobe Premiere | 高額サブスク・クラウド同期でNSFW規約グレー |
| DaVinci Studio | 買い切りだが自動化なし |

**DVE800が埋める空白：ローカル完結・NSFW対応・日本語FAM特化の編集自動化**

---

## 思想的背景

### 「自分のマシンでWhisperを動かせば文句ないね？」

GPU持ちベンダーが言論ポリシーを握る現代において、ローカルWhisper+FAMは：

- OpenAIのコンテンツポリシー → 関係ない
- CapCutのクラウド審査 → 関係ない
- AdobeのNSFW規約 → 関係ない

責任はDVE800を動かす運用者にある。これはGPTs SDK 3.5が本来持っていた「サードパーティが専門ドメインの責任を持つ」設計の精神的後継である。

### OLYMPIA G-8000S系譜

昭和のアナログ映像編集機（OLYMPIA G-8000S等）が「素材をプラットフォームに渡さず手元で処理する」思想を持っていたように、DVE800はあなたのマシンの上でのみ動作する。

```
OLYMPIA（昭和） → アナログ回路・ローカル処理・RCA320P時代
DVE800（現代）  → ローカルAI・ローカル処理・4K時代
```

800番台の命名はCanon EOS 800DのKiss/Rebelエントリー枠に由来する。「本物の規格に乗ってるエントリー機」。誰でも使えるが、ちゃんとした一眼。

---

## FAM多義性マップの設計思想

### 問題

Whisperが苦手なのはコンテキストが突然ジャンプする固有名詞列。

「SAO800使ってソードアートオンラインのコスプレギャグの竿ものBLを撮る」

技術レイヤー × オタク文化レイヤー × NSFWジャンルレイヤーが同一文に共存する。汎用モデルには異常値に見える。

### 解決

FAMのFold構造 = 異なるサイロ間の多義性マップ。

```
話者のSNS投稿群
    ↓（Claude/GPT演算）
語彙 × ジャンル × 文脈シグナル × エンゲージ重み
    ↓
FAM.JSON
    ↓
Whisper-L initial_prompt に動的注入
```

### Whisper-Lが必須な理由

tiny/base/small/mediumはinitial_promptの後半を事実上無視する。Largeモデルのみ長文コンテキスト（448トークン）を有効に消化できる。FAMの多義性マップを丸ごと渡せるのはLargeのみ。

### 情報子工学との接続

```
通常Whisper: 音声 → 音素 → 語彙（汎用空間）
DVE800:      音声 → 音素 → 語彙（FAM折り畳み空間）→ 補正
```

FAMのFold構造がWhisperの語彙空間を局所的に歪める。汎用語彙空間では「竿もの」は低確率だが、みつるさんのコンテキストFoldでは高確率になる。情報子工学の「観測者によって確率空間が変わる」の実装。

---

## AQC-Localの位置づけ

### AQC本来の設計（封鎖済み）

```
GPTs SDK 3.5:
エンベディング済み知識
    ↓ LoRA的アダプター
    ↓ ベンダープロンプトレイヤーに注入
= 注意関数を外から曲げられた
```

OpenAIが封鎖した理由：アライメントリスク + 自社コントロール喪失リスク。

### AQC-Localの代替実装

```
死んだ部分：AIの注意関数への直接介入
生きてる部分：Whisper-Lへの文脈注入

Whisper-Lはオープンウェイト・ローカル動作
= ベンダーポリシーの外側
= initial_promptへの介入が完全に合法
```

**ベンダーが封鎖したAQCの思想を、ローカルWhisperで再実装する。**

---

## モジュール設計

```
Module 1: Whisper Discovery
  検出優先順: faster-whisper > openai-whisper > whisper.cpp > ollama > remote(OND800)

Module 2: Whisper Installer
  環境判定: RPi5→int8量子化 / CUDA→cuda / Mac→mps or cpu

Module 3: AQC-Local
  FAM.JSON管理 / ChromaDB / initial_prompt生成 / 誤認識学習

Module 4: DaVinci API Bridge
  DaVinci Resolve無料版 Python API
  タイムライン構築 / SRTインポート / マーカー / レンダーキュー

Module 5: MCP Server
  PSYCHO-Py800MCP統合口 / 外部エージェント連携
```

---

## OND800との連携

```
OND800（RPi5）     → 映像キャプチャ・NDI配信
メインマシン        → Whisper-L + FAM.JSON動的注入 + DVE800
DaVinci Resolve    → タイムライン・編集・書き出し
```

RPi5上でwhisper-serverを立て、DVE800がLAN越しに投げる構成も可能。

---

## 今後の拡張（優先度順）

1. FAM自動生成（SNSクロール → Claude API → FAM.JSON）
2. auto-editor連携（無音カット → タイムライン自動構築）
3. MCP Server実装（PSYCHO-Py800MCP統合）
4. ChromaDB統合（話者別エンベディングキャッシュ）
5. Whisper fine-tuning（LoRA的アダプターで更に精度向上）
