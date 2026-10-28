# レイアウト

> 各項目の`ローカル参照`は`generate-screen-design-rules` Skillに同梱されたファイルを指し、本プロジェクトには含まれません。詳細は[README.md](./README.md)を参照してください。

Header、Side Navigation、Content領域、Gridなど、画面全体の配置ルールを定義します。

## 1. 基本グリッド

<!-- template-only:start -->
- **状態:** 暫定
- **出典:** DADS
- **参照ヒント:** 基本デザイン > レイアウト > グリッドシステム
- **ローカル参照:** `references/dads/foundations/layout/index.md`
<!-- template-only:end -->

### 説明

画面の内容をそろえる列の構成と幅の考え方を定めます。

### 規約
- 画面レイアウトはグリッドを使って構成する
- 基本は12カラムとする
- 画面の用途に応じて1カラム等も利用できる
- ページ全体はリキッドレイアウトを基本とする

## 2. アプリケーション全体の構成

<!-- template-only:start -->
- **状態:** 暫定
- **基本:** DADS
- **補完:** Carbon
- **参照ヒント:** UI Shell（Header + Left panel + Right panel）> Usage
- **検索キーワード:** Application shell, UI shell
- **ローカル参照:** `references/carbon/UI-shell-header/usage.mdx`、`references/carbon/UI-shell-left-panel/usage.mdx`、`references/carbon/UI-shell-right-panel/usage.mdx`
<!-- template-only:end -->

### 説明

ヘッダー、ナビゲーション、本文などの領域を画面全体にどう配置するかを定めます。

### レイアウト例
[application-shell.html](./assets/layouts/application-shell.html)

> **参考例**
> HTMLは画面構成を示すための参考資料です。
> DOM構造、CSS、クラス名そのものを実装方法として指定するものではありません。
> 実装時は、このMarkdownに記載された規約を優先します。

## 3. Header

<!-- template-only:start -->
- **状態:** 暫定
- **補完元:** Carbon
- **参照ヒント:** UI shell header > Style > Structure
- **検索キーワード:** Header height, Product name padding
- **ローカル参照:** `references/carbon/UI-shell-header/style.mdx`
- **候補:** 高さ48pxを採用するか確認する。
<!-- template-only:end -->

### 説明

画面上部の共通領域の寸法と配置を定めます。

| 項目 | 暫定値 |
|---|---:|
| 高さ | 48px |
| 横幅 | 画面全幅 |

## 4. Side Navigation

<!-- template-only:start -->
- **状態:** 暫定
- **補完元:** Carbon
- **参照ヒント:** UI shell left panel > Style / Usage
- **検索キーワード:** width, menu item, padding, icon
- **ローカル参照:** `references/carbon/UI-shell-left-panel/style.mdx`、`references/carbon/UI-shell-left-panel/usage.mdx`
- **候補:** 幅256px、項目高さ32px、左右padding 16px、アイコン16pxを採用するか確認する。
<!-- template-only:end -->

### 説明

業務メニューを表示する領域の寸法と開き方を定めます。

| 項目 | 暫定値 |
|---|---:|
| 幅 | 256px |
| メニュー項目高さ | 32px |
| 左右padding | 16px |
| アイコンサイズ | 16px |

<!-- template-only:start -->
### 確認事項

- [ ] 既定で開くか、閉じるか
- [ ] 開くときの表示方式（本文を押し出す／本文の上に重ねる）
<!-- template-only:end -->

> 横に長い画面（表、ツリーなど）が多い場合は、既定で閉じる、または本文の上に重ねる方式にすると、本文の幅を広く使えます。

## 5. Main Content

<!-- template-only:start -->
- **状態:** 要確認
<!-- template-only:end -->

### 説明

本文を配置する領域の余白と最大幅を定めます。

| 項目 | 値 |
|---|---|
| Content左右padding | `[要確認]` |
| Content上部padding | `[要確認]` |
| 最大幅 | `[要確認]` |

## 6. レスポンシブ

<!-- template-only:start -->
- **状態:** 暫定
- **基本:** DADS
- **補完:** Carbon
- **参照ヒント:** 基本デザイン > レイアウト > ブレークポイント（DADS）／UI shell header > Style > Responsive behavior、UI shell left panel > Usage（Responsive behavior、Carbon）
- **検索キーワード:** Responsive behavior
- **ローカル参照:** `references/dads/foundations/layout/index.md`、`references/carbon/UI-shell-header/style.mdx`、`references/carbon/UI-shell-left-panel/usage.mdx`
<!-- template-only:end -->

### 説明

画面幅に応じた内容やナビゲーションの配置方法を定めます。

### 規約
- 画面幅に応じてコンテンツ幅を可変にする
- DOM上の順序と視覚上の表示順を大きく乖離させない
- 狭い画面でのSide Navigationの表示方法を統一する
