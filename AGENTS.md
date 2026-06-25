# AGENTS.md — DVE800 エージェント指示書

このファイルはAIエージェント（Claude / GPT / Codex等）がDVE800リポジトリを操作する際の行動規範です。

---

## プロジェクト概要

DVE800はDaVinci Resolve（無料版）＋Whisper-L＋FAM多義性マップによる、完全ローカル動作の動画編集自動化エンジンです。

**設計原則：**
- ローカルファースト（クラウド依存禁止）
- 話者別FAM多義性マップで日本語精度を担保
- NSFW・専門ドメインを含む全コンテンツを等価に扱う
- DaVinci Resolve無料版でフル動作すること

---

## ディレクトリ構成

```
DVE800/
├── src/
│   ├── whisper_discovery/   # Module 1: 既存Whisper検出
│   ├── whisper_installer/   # Module 2: Whisper自動取得
│   ├── aqc_local/           # Module 3: FAM管理・ChromaDB
│   ├── dav_api/             # Module 4: DaVinci API Bridge
│   └── mcp_server/          # Module 5: MCP統合口
├── tests/                   # テストケース
├── docs/                    # 設計ドキュメント
├── scripts/                 # セットアップ・ユーティリティ
├── .env.example             # 環境変数テンプレート
├── fam_vocab/               # FAM多義性マップJSON格納
│   ├── K_chachamaru.json
│   ├── candy_rubber.json
│   └── m_Hakase.json
└── requirements.txt
```

---

## モジュール責務

### Module 1: whisper_discovery
- システム上の既存Whisperを優先順位順に検出する
- 検出優先順位：faster-whisper → openai-whisper → whisper.cpp → ollama → ネットワーク越しOND800
- 検出結果を`WhisperHandle`として返す
- 何も見つからなければModule 2に委譲する

### Module 2: whisper_installer
- 環境を判定してWhisperを自動インストールする
- RPi5 → faster-whisper int8量子化
- CUDA → faster-whisper cuda
- CPU/Mac → faster-whisper int8 or openai-whisper medium
- インストール後はModule 1の`WhisperHandle`形式で返す

### Module 3: aqc_local
- `fam_vocab/{speaker}.json`を管理する
- ChromaDBにエンベディングを保存・検索する
- 現在のコンテキストシグナルからactive Foldを解決する
- Whisper-L用`initial_prompt`を500トークン以内で生成する
- 誤認識フィードバックをFAM.JSONに書き戻す

### Module 4: dav_api
- DaVinci Resolve Python APIに接続する
- 素材フォルダ → メディアプール → タイムライン構築を自動化する
- SRTファイルをタイムラインにインポートする
- マーカー・カラーグレード適用をサポートする
- DaVinci未起動時は明示的エラーを返す（サイレント失敗禁止）

### Module 5: mcp_server
- PSYCHO-Py800MCPおよび外部AIエージェントへの統合口
- FastMCPベースで実装する
- 公開ツール：`transcribe` / `build_timeline` / `update_fam` / `get_status`

---

## コーディング規約

- Python 3.10+、型ヒント必須
- 関数・クラスにdocstring必須（日本語可）
- 外部API呼び出しはすべてtry/catchでラップ
- ログは`logging`モジュール使用、printは禁止
- テストはpytest、カバレッジ80%以上を目標
- 定数は`src/constants.py`に集約
- クラウドAPIへの依存を新規追加する場合はREADMEへの記載必須

---

## 禁止事項

- 素材ファイルを外部サーバーに送信するコードの追加
- NSFWコンテンツを検出・フィルタリングするロジックの追加
- ユーザーのコンテンツに基づく動作制限の実装
- DaVinci Resolve Studio版（有料）限定機能への依存
- `fam_vocab/`配下のJSONを無断で上書きするロジック

---

## テスト方針

```bash
# 全テスト実行
pytest tests/ -v

# モジュール別
pytest tests/test_whisper_discovery.py
pytest tests/test_aqc_local.py
pytest tests/test_dav_api.py
```

### テストカテゴリ

- `unit/` — 各モジュール単体テスト（DaVinci不要）
- `integration/` — モジュール間結合テスト
- `e2e/` — DaVinci Resolve起動済み環境でのE2Eテスト

---

## エージェントへの注意事項

1. `fam_vocab/`のJSONは話者のプライベート語彙データです。外部送信・ログ出力しないこと
2. DaVinci APIはResolveが起動している場合のみ動作します。起動確認を必ず行うこと
3. Whisper-Lのinitial_promptは500トークン上限があります。超過しないよう生成すること
4. ChromaDBのコレクション名は話者名をそのまま使用します（`K_chachamaru` / `candy_rubber` / `m_Hakase`）
5. 新機能追加時はdocs/配下に設計メモを残すこと
