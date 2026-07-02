# 索敵レポート v1 — レッドオーシャン／空白域マッピング

作成: 2026-07-02
著者: ZeroRoomLab / 齋藤みつる（ふさもふ）
位置づけ: `docs/verification_log/20260702.md` §3の索敵結果を正式ドキュメント化したもの。

---

## 1. レッドオーシャン領域マップ

| 領域 | 主要プレイヤー | 備考 |
|---|---|---|
| トランジション/タイトルプリセット集 | MotionVFX, AEJuice, Boris FX Sapphire, Pixelan(250+3Dトランジション), TheResolve.Store, Envato/VideoHive | AE Juice型UXはResolve側に既に移植済み |
| プラグイン配布インフラ | **Reactor**（WeSuckLess、無料、週40万人利用、6年運用、Atomパッケージ形式） | ゼロから配布UIを作る意味は薄い。乗るか無視するかの二択 |
| モザイク処理そのもの | Resolve無料版ネイティブ（Power Window＋Mosaic Blur OFX） | 効果自体は空白なし。空いているのは自動検出・自動追跡のバッチ化の方 |
| Whisper字幕自動生成 | `tmoroney/auto-subs`（Lua server＋Fusion macro、話者分離、アニメキャプション、日本語含む100+言語、直近2週間以内更新＝現役開発）、`in03/squawk`、Caption Cat（aescripts商業版、112言語） | DVE800のModule 1〜4とほぼ丸かぶり |
| Whisperラフカット | `BadWords`（GUI内蔵、台本比較、フィラーワード除去、無音検出） | 統合ワークフローパネルの直接競合 |

## 2. 検出モデル軍拡競争

NSFW領域の検出モデル軍拡は既に進行中：

- DeepMosaics → DeepMosaicsPlus（後継・高精度化）
- lada（YOLO系セグメンテーション、事前バッチ検出向き）
- RVC / Applio / Ultimate RVC（音声変換系、隣接領域）

**位置づけ：** この軍拡競争のスポーン過密は、DVE800にとって狩場ではなく資源プールである。検出精度そのものを競う必要はなく、これらのモデルをModule 8（`mosaic_detection`）でborrowし、事前バッチのサイドカーファイル生成に限定利用する。

## 3. DVE800の狩場定義

索敵範囲内で類似実装が確認できなかった二点：

1. **人間主導の審査対応ワークフロー** — 審査フィードバックをタイムコード単位で取り込み、`ReviewFormatAdapter`で正規化し、最終強度決定を常に人間に残す設計を持つツールはゼロ。
2. **話者別FAM文脈判断** — 話者ごとの多義性語彙マップ（FAM）をWhisperの`initial_prompt`に動的注入する設計を持つツールはゼロ。NSFW・専門ドメイン語彙を対等に扱う設計思想を明示しているツールもゼロ（aescripts系は完全にSFW企業ブランディング前提）。

→ 結論：字幕生成やモザイクという「機能」レベルで差別化しようとするのは負け筋。FAM語彙特化＋NSFW対等設計＋人間主導審査対応ワークフローの縦串こそが唯一の空白。

## 4. 継続監視項目（月次目安）

lada / DeepMosaics / Applio系のIssueトラッカー・ロードマップに、以下の言及が出ていないかを定点観測する：

- 「NLE統合」（DaVinci Resolve / Premiere等への直接統合）
- 「人間フィードバックループ」（検出結果に対する人間の確定操作を前提とした設計）

これらが出現した場合、DVE800の狩場定義（§3）の再検証が必要になる。
