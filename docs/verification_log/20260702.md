# DVE800 検証ログ — 2026-07-02

対象リポジトリ：`saitoomituru/DVE800`
セッション種別：設計補助＋市場索敵＋実機ベンチ検証
記録者：オトモアイルー（アシスタント）／みつるさん側視点で記録

---

## 0. セッション概要

README（設計哲学）＋AGENTS.md（要求仕様粒度）の状態から、実装フレーム粒度への落とし込み→GUI構成方針の検討→市場索敵→Gyroflow OFXの実機ロード確認、まで一気通貫で進めた回。理論だけで止めず、最後は実機の一次証拠まで取れている。

---

## 1. 実装フレーム設計（第一段階）

5モジュール構成（README/AGENTS.md記載）を型契約レベルまで落とした。

**境界オブジェクト方針**：`WhisperHandle`を全モジュール共通の受け渡し型にすることで、AQC-Local・DaVinci Bridgeは背後のASRエンジン実装（faster-whisper/openai-whisper/リモート）を知らずに動く設計。バックエンド差し替え実験がModule1/2の中だけで完結する。

**`fam_vocab/`無断上書き禁止をコード契約化**：`FAMStore.propose_update()`はpendingファイル作成のみ、実マージ`apply_pending()`は明示CLI経由限定。MCP側`update_fam`ツールもpending作成止まりに権限を絞り、外部エージェント（PSYCHO-Py800MCP経由）からの自動書き換えを構造的にゲート。

**500トークン上限の実証可能化**：`build_initial_prompt()`にtoken_budget境界テストを持たせ、「Whisper-Lが必須」という主張自体を自前で裏取りできる形にした。

成果物：`DVE800_implementation_frame.md`（別途生成済み、docs/相当）

索敵表（threat scouting）も同セッションで作成：DaVinci APIバージョン変動・Whisperモデル配布元可用性・ChromaDBスキーマ非互換の3点について、「壊れない」と断定するのではなく「壊れたら自動で直る／境界内に被害を封じ込める」設計＋再現テストの形に変換済み。

---

## 2. GUI構成方針（第二段階）

みつるさんの初期案：
- ①エフェクトプラグイン粒度（モザイク/字幕演出/トス）は個別プラグインとして供給
- ②統合ワークフローパネルをPythonスクリプトと共に別パネル提供（AE Juice All Bundle / Animation Composer相当を志向）

これに対する配分方針：

| レイヤー | 方針 |
|---|---|
| ①エフェクトプラグイン粒度 | 車輪の再発明をしない。Resolveネイティブ機能＋既存OFXに乗り、DVE800側は「FAMタグに応じてどのプリセットを適用するか」の判断ロジックのみ持つ。配布はReactorエコシステムに乗る薄いラッパーで工数を空ける |
| ②統合ワークフローパネル（Python） | 本丸。FAM Fold解決→話者別initial_prompt→NSFW語彙もフラット扱い→モザイク自動検出候補提示、まで一本の縦串。Animation Composer的な「パネルからプリセットを流し込む」UI発想はここに実装（プリセット＝エフェクトではなく「FAM文脈に応じた処理レシピ」） |

---

## 3. 市場索敵（レッドオーシャン／空白域マッピング）

### 3-1. 密度が高い（レッドオーシャン）領域

| 領域 | 主要プレイヤー | 備考 |
|---|---|---|
| トランジション/タイトルプリセット集 | MotionVFX, AEJuice, Boris FX Sapphire, Pixelan(250+3Dトランジション), TheResolve.Store, Envato/VideoHive | AE Juice型UXはResolve側に既に移植済み |
| プラグイン配布インフラ | **Reactor**（WeSuckLess、無料、週40万人利用、6年運用、Atomパッケージ形式） | ゼロから配布UIを作る意味は薄い。乗るか無視するかの二択 |
| モザイク処理そのもの | Resolve無料版ネイティブ（Power Window＋Mosaic Blur OFX） | 効果自体は空白なし。空いてるのは自動検出・自動追跡のバッチ化の方 |
| Whisper字幕自動生成 | `tmoroney/auto-subs`（Lua server＋Fusion macro、話者分離、アニメキャプション、日本語含む100+言語、直近2週間以内更新＝現役開発）、`in03/squawk`、Caption Cat（aescripts商業版、112言語） | DVE800のModule1〜4とほぼ丸かぶり |
| Whisperラフカット | `BadWords`（GUI内蔵、台本比較、フィラーワード除去、無音検出） | 統合ワークフローパネルの直接競合 |

### 3-2. 空白域（DVE800が刺せる場所）

- 話者ごとの多義性語彙マップ（FAM）をWhisperのinitial_promptに動的注入する設計を持つツール：**ゼロ**
- NSFW・専門ドメイン語彙を対等に扱う設計思想を明示しているツール：**ゼロ**（aescripts系は完全にSFW企業ブランディング前提）

→ 結論：字幕生成やモザイクという「機能」レベルで差別化しようとするのは負け筋。FAM語彙特化＋NSFW対等設計の縦串こそが唯一の空白。

---

## 4. 実機検証：Gyroflow OFX ロードテスト（一次証拠取得）

**環境**：DaVinci Resolve 無料版、Preferences → ビデオプラグイン → OpenFXプラグイン
**結果**：`Gyroflow.ofx.bundle` → 状況「ロード完了」（チェック有効）
**証跡**：スクリーンショット（2026-07-02 15:48:56）

### 解消した外部主張の矛盾

事前索敵の時点で、「無料版ResolveはOFXプラグインに非対応」（tella.com記載）という説と、「無料版でMosaic OFXが普通に使える」という実演チュートリアル（edits101/miracamp）の間で矛盾があった。

2026-06-30更新のtoolfarm記事で以下が判明：
- **Studio限定**なのは内蔵ResolveFXの一部（Lens Blur / Camera Blur / Lens Flare / Film Grain / Magic Mask / 文字起こし等）
- **サードパーティOFX**（Gyroflow、ntsc-rs等）は無料版でも通常ロードされる

今回のスクリーンショットはこれを伝聞ではなく**実機の一次証拠**として固定したもの。DVE800 README主張（「無料版でフル動作」）の防衛ラインとして、そのまま`tests/e2e/test_free_version_compat.py`のケース根拠に転用できる。

### 未完了項目（次のログで埋める）

1. OS/Resolveバージョン番号の記録（About画面から）
2. Fusion Consoleログ確認 — Gyroflowロード過程でStudio限定機能への隠れ参照がないかの監視
3. クリップへの実適用→スタビライズ処理→書き出しまでの完走（現状は「ロード完了」表示のみで実処理は未検証）

---

## 5. 次アクション候補

- 上記未完了3項目を同一実機で継続検証するか
- 並行してntsc-rs／BaldavengerPluginsの導入検証に進むか
- `docs/threat_scouting_v1.md`として索敵表を正式に切り出し、資金調達ロビー資料に転用する準備をするか

判断待ち。
