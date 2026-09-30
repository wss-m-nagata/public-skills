# DADS ローカルリファレンス（このファイルのみSkill独自の索引です）

このディレクトリ配下の `foundations/` `guidance/` `components/` の各Markdownは、デジタル庁デザインシステム（DADS）が公式に配布しているMarkdownアーカイブから、**本Skillのテンプレートが参照する範囲だけを未編集のまま**コピーしたものです。

`design-tokens/tokens.json` は、上記Markdownとは別の出典（`digital-go-jp/design-tokens` リポジトリ）から取得した、色・タイポグラフィ・サイズのDesign Token定義（実HEX値を含む）です。詳細は下記「Design Tokenについて」を参照してください。

このREADME.md自体はSkill側で作成した索引であり、DADS本体のコンテンツではありません。

## 出典・取得情報（Markdownアーカイブ）

- 配布元: https://design.digital.go.jp/dads/resources/
- 取得したアーカイブ: `dads-markdown-20260909.zip`
- 取得日: 2026-09-15
- 元のディレクトリ構成（`foundations/xxx/index.md` 等）をそのまま維持しています。
- 機械可読な取得情報は同ディレクトリの `VERSION.txt` を参照してください。古いかどうかの判断はこのファイルの日付を基準にします。

## 利用条件（DADS「利用上の注意事項」より、Markdownアーカイブ分）

出典: https://design.digital.go.jp/dads/introduction/notices/

- コンテンツ利用時は出典を記載する（例: `出典：デジタル庁デザインシステムウェブサイト https://design.digital.go.jp/dads/`）。
- 編集・加工して利用する場合は、加工した旨を別途記載する必要がある。
- **本ディレクトリのファイルは加工・要約をせず原文のまま保存しています。** 規約Markdownへ引用・転記する際は、DADSを出典として明記してください。

## Design Tokenについて（`design-tokens/tokens.json`）

- 出典リポジトリ: https://github.com/digital-go-jp/design-tokens
- 収録ファイル: `figma/tokens.json`（Color / Typography / Size の各トークン。Primitive値は実HEX値を含み、Semantic/Key等の上位トークンはPrimitiveへのエイリアス参照になっている）
- ライセンス: MIT（リポジトリの`LICENSE`参照）
- 取得コミット・取得日: 同ディレクトリの `VERSION.txt` を参照

**色のHEX値はDADS公式サイト・Markdownアーカイブのどちらにも掲載されていないが、このリポジトリには実HEX値まで含まれている。** 色を具体化する場合は、まず `foundations/color/index.md` で分類・用途を確認したうえで、`design-tokens/tokens.json` の該当トークン（例: `Color.Semantic.Error.1` → `Color.Primitive.Red.800` → 実HEX値）を辿って値を確定する。

## 更新方針

このリファレンスは**取得時点のスナップショット**であり、自動更新は行いません。DADSの内容が更新された場合、必要になったタイミングで `dads-markdown-*.zip` を再取得し、該当ファイルを置き換え、取得日を更新してください（自動チェックの仕組みは持たせていません）。

## 収録ファイルと参照ヒントの対応

| 参照ヒント | ローカルファイル |
|---|---|
| 基本デザイン > 余白 | `foundations/spacing/index.md` |
| 基本デザイン > 角の形状 | `foundations/corner-shapes/index.md` |
| 基本デザイン > エレベーション | `foundations/elevation/index.md` |
| 基本デザイン > タイポグラフィ | `foundations/typography/index.md` |
| 基本デザイン > カラー | `foundations/color/index.md`（分類・用途）＋ `design-tokens/tokens.json`（実HEX値） |
| 基本デザイン > レイアウト（グリッドシステム／ブレークポイント） | `foundations/layout/index.md` |
| ガイダンス > アクセシビリティ | `guidance/accessibility/index.md` |
| コンポーネント > ボタン | `components/button/index.md` |
| コンポーネント > インプットテキスト | `components/input-text/index.md` |
| コンポーネント > テキストエリア | `components/textarea/index.md` |
| コンポーネント > セレクトボックス | `components/select/index.md` |
| コンポーネント > チェックボックス | `components/checkbox/index.md` |
| コンポーネント > ラジオボタン | `components/radio/index.md` |
| コンポーネント > 日付ピッカー／カレンダー | `components/date-picker/index.md` |
| コンポーネント > テーブル／データテーブル | `components/table/index.md` |
| コンポーネント > テーブルコントロール | `components/table-control/index.md` |
| コンポーネント > パンくずナビゲーション | `components/breadcrumb/index.md` |
| コンポーネント > タブ | `components/tab/index.md` |
| コンポーネント > モーダルダイアログ | `components/modal-dialog/index.md` |
| コンポーネント > カード | `components/card/index.md` |
| コンポーネント > ノティフィケーションバナー | `components/notification-banner/index.md` |
| コンポーネント > 見出し | `components/heading/index.md` |
| コンポーネント > 説明リスト | `components/description-list/index.md` |

上記以外の参照ヒントに該当するローカルファイルが無い場合は、`SKILL.md`の「参照ヒントが記載されていない項目」の手順に従い、公式サイト（https://design.digital.go.jp/dads/）を直接確認してください。
