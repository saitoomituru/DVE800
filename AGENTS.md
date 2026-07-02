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
│   ├── whisper_discovery/    # Module 1: 既存Whisper検出
│   ├── whisper_installer/    # Module 2: Whisper自動取得
│   ├── aqc_local/            # Module 3: FAM管理・ChromaDB
│   ├── dav_api/              # Module 4: DaVinci API Bridge
│   ├── mcp_server/           # Module 5: MCP統合口
│   ├── cockpit/              # Module 6: コックピット層
│   ├── compliance_review/    # Module 7: 審査フィードバック取り込み
│   └── mosaic_detection/     # Module 8: 検出borrow層（要ライセンス隔離）
├── ofx/
│   └── mosaic_render/        # 重量OFX層（C++、別ビルド系統）
├── fusion_presets/           # 軽量プリセット層（.setting群）
├── tests/                    # テストケース
├── docs/                     # 設計ドキュメント
│   ├── threat_scouting_v1.md
│   ├── ux_philosophy.md
│   └── verification_log/     # 実機検証ログ格納先
├── scripts/                  # セットアップ・ユーティリティ
├── .env.example              # 環境変数テンプレート
├── fam_vocab/                # FAM多義性マップJSON格納
│   ├── K_chachamaru.json
│   ├── candy_rubber.json
│   └── m_Hakase.json
├── compliance_profiles/      # 審査傾向ログ（FAMStoreと同型パターン）
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

### Module 6: cockpit
- FastAPIサーバー＋ブラウザUIとして独立起動する
- 4パネル構成：検出候補パネル／審査ノートパネル／手動決定パネル／傾向ログパネル
- 自動化ゾーンと決定ゾーンを画面区画として明確に分離すること
- 確定操作（px・角度カバー範囲の反映）は必ず人間の明示アクション経由。自動適用は禁止
- Resolve本体とはLuaブリッジ層経由で疎結合に接続する（`dav_api`のスクリプトAPI依存を
  コックピット本体に持ち込まない。無料版でのスクリプトAPI可否が未確定のため）

### Module 7: compliance_review
- 審査フィードバック（STL/SRT/自由記述テキスト等）を`ReviewNote`型に正規化する
- `ReviewFormatAdapter`プロトコル＋レジストリ形式で、フォーマット追加を拡張可能にする
- 担当者依存でフォーマットが揺れることを前提とした設計にすること。固定パーサー1本化は禁止
- タイムコードから該当`MosaicRegion`インスタンスへのマッチングを行う（`shot_matcher.py`）
- `compliance_profiles/`への書き込みは`FAMStore`と同型のpending→明示マージパターンに従う

### Module 8: mosaic_detection
- lada等の外部検出モデル（YOLO系）を事前バッチ処理として呼び出し、
  フレームごとのNSFW領域座標を`MosaicRegion`のサイドカーファイル（JSON）として出力する
- **本モジュールはAGPL-3.0ライセンスのモデル資産に依存する可能性があるため、
  他モジュールから独立したサブディレクトリ・独立した依存関係管理（別venv/別requirements）
  とし、本体（Apache 2.0）へのライセンス伝播を防ぐこと**
- 検出結果は「候補」であり、最終的な強度決定には関与しない。これを侵さないこと

---

## コーディング規約

- Python 3.10+、型ヒント必須
- 関数・クラスにdocstring必須（日本語可）
- 外部API呼び出しはすべてtry/catchでラップ
- ログは`logging`モジュール使用、printは禁止
- テストはpytest、カバレッジ80%以上を目標
- 定数は`src/constants.py`に集約
- クラウドAPIへの依存を新規追加する場合はREADMEへの記載必須
- OFX層（`ofx/mosaic_render/`）はC++、他モジュールとビルド系統を分離する
- Fusion presets（`.setting`）はPythonから動的生成する場合、テンプレートエンジンではなく
  DaVinci Resolve公式のFusion Composition仕様に準拠したシリアライズ処理を用いること

---

## 禁止事項

- 素材ファイルを外部サーバーに送信するコードの追加
- NSFWコンテンツを検出・フィルタリングするロジックの追加
- ユーザーのコンテンツに基づく動作制限の実装
- DaVinci Resolve Studio版（有料）限定機能への依存
- `fam_vocab/`配下のJSONを無断で上書きするロジック
- 検出モデル（Module 8）の出力を、人間の確認・確定操作なしに直接レンダリングへ反映するロジックの実装
- `compliance_profiles/`配下のJSONを傾向ログから自動書き換えするロジック（`fam_vocab/`と同様、無断上書き禁止）
- Module 8とApache 2.0本体コードの依存関係を混在させ、ライセンス境界を曖昧にする実装
- 審査フォーマットパーサーを単一固定フォーマット前提で実装すること（アダプタパターン必須）

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

### 追加テスト項目（Module 6〜8関連）

- `tests/e2e/test_free_version_compat.py` に、無料版ResolveでのOFXロード確認ケースを追加
  （Gyroflow.ofx.bundleの実機確認結果を回帰テストの基準値として使用）
- `tests/unit/test_review_ingest.py` — ReviewFormatAdapterのレジストリ機構のテスト
  （フォーマット追加時に既存アダプタが壊れないことを保証）
- `tests/unit/test_mosaic_detection_license_boundary.py` — Module 8の依存関係が
  他モジュールのrequirements.txtに混入していないことを検証する静的チェック

---

## エージェントへの注意事項

1. `fam_vocab/`のJSONは話者のプライベート語彙データです。外部送信・ログ出力しないこと
2. DaVinci APIはResolveが起動している場合のみ動作します。起動確認を必ず行うこと
3. Whisper-Lのinitial_promptは500トークン上限があります。超過しないよう生成すること
4. ChromaDBのコレクション名は話者名をそのまま使用します（`K_chachamaru` / `candy_rubber` / `m_Hakase`）
5. 新機能追加時はdocs/配下に設計メモを残すこと
