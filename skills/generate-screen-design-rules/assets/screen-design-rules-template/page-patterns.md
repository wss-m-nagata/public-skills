# 標準画面パターン

> 各項目の`ローカル参照`は`generate-screen-design-rules` Skillに同梱されたファイルを指し、本プロジェクトには含まれません。詳細は[README.md](./README.md)を参照してください。

よく使う業務画面の構成をパターン化します。

## 1. 検索＋一覧
- **状態:** 暫定
- **参照ヒント:** コンポーネント > テーブル／データテーブル、テーブルコントロール（DADS）／Data table > Usage > Table toolbar / Batch actions（Carbon）
- **ローカル参照:** `references/dads/components/table/index.md`、`references/dads/components/table-control/index.md`、`references/carbon/data-table/usage.mdx`

### レイアウト例
[search-list.html](./assets/layouts/search-list.html)

> **参考例**
> HTMLは画面構成を示すための参考資料です。
> DOM構造、CSS、クラス名そのものを実装方法として指定するものではありません。

## 2. 詳細画面
- **状態:** 暫定
- **参照ヒント:** コンポーネント > 見出し、説明リスト
- **ローカル参照:** `references/dads/components/heading/index.md`、`references/dads/components/description-list/index.md`

## 3. 登録・編集画面
- **状態:** 暫定
- **参照ヒント:** コンポーネント > インプットテキスト等フォーム部品
- **ローカル参照:** `references/dads/components/input-text/index.md` 等（`components.md`のForm項目を参照）

### レイアウト例
[edit-form.html](./assets/layouts/edit-form.html)

> **参考例**
> HTMLは画面構成を示すための参考資料です。

## 4. マスタメンテナンス画面
- **状態:** 暫定

## 5. Dialog / Side Panel / 別画面の使い分け
- **状態:** 暫定
- **補完元:** Carbon
- **参照ヒント:** Modal > Usage（Modalとサイドパネルの使い分け）、UI shell right panel > Usage
- **検索キーワード:** editable fields, scrolling, context
- **ローカル参照:** `references/dads/components/modal-dialog/index.md`、`references/carbon/modal/usage.mdx`、`references/carbon/UI-shell-right-panel/usage.mdx`

| 操作 | 推奨 |
|---|---|
| 確認や短い入力 | Dialog |
| 元画面を見ながら補助的に操作 | Side Panel |
| 入力項目が多い・操作が複雑 | 別画面 |
