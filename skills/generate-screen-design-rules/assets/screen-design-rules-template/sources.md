# 参照元

画面規約の作成に利用したデザインシステムと、主な採用範囲を記録します。

最終更新日: 2026-09-10

## 1. デジタル庁デザインシステム（DADS）

**位置付け:** 主たる画面設計規約

公式サイト：

- https://design.digital.go.jp/dads/

主な参照先：

- 基本デザイン
- レイアウト
- 余白
- タイポグラフィ
- カラー
- コンポーネント
- アクセシビリティ
- Design Token

### 主に採用するもの

- 色
- 文字
- 余白
- Grid / Layout
- Button
- Form
- Table
- Breadcrumb
- Tab
- 基本的なUI部品
- Accessibility
- Design Token

---

## 2. IBM Carbon Design System

**位置付け:** DADSで不足する業務アプリ向け規約の補完

公式サイト：

- https://carbondesignsystem.com/

主な参照先：

- UI Shell Header
- UI Shell Left Panel
- Data Table
- Dialog / Side Panel等の使い分け

### 主に補完するもの

- Application Shell
- Global Header
- Side Navigation
- Header / Side Navigation / Contentの組み合わせ
- ナビゲーション階層
- 狭い画面でのナビゲーション挙動
- 高機能Data Tableの操作パターン
- Dialog / Side Panel / 別画面の使い分け

### 暫定値として利用している例

| 項目 | 暫定値 | 出典 |
|---|---:|---|
| Header高さ | 48px | Carbon UI Shell Header |
| Side Navigation幅 | 256px | Carbon UI Shell Left Panel |
| Side Navigation項目高さ | 32px | Carbon UI Shell Left Panel |
| Side Navigation左右padding | 16px | Carbon UI Shell Left Panel |
| Side Navigationアイコン | 16px | Carbon UI Shell Left Panel |

これらは確定値ではありません。
プロジェクトの規約として採用するか、変更するかを確認して確定します。

---

## 3. プロジェクト独自ルール

DADS / Carbonにないルールや、プロジェクトとして変更したルールは理由とともに記録します。

| 対象 | 採用ルール | DADS / Carbonからの変更理由 |
|---|---|---|
| `[記載]` | `[記載]` | `[記載]` |

---

## 4. 外部規約の更新

外部デザインシステムが更新されても、このプロジェクトの規約を自動的には変更しません。

更新内容を確認し、必要な場合のみ `docs/rules/screen-design-rules/` へ反映します。
