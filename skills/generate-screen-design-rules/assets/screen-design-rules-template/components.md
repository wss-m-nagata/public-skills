# UIコンポーネント

> 各項目の`ローカル参照`は`generate-screen-design-rules` Skillに同梱されたファイルを指し、本プロジェクトには含まれません。詳細は[README.md](./README.md)を参照してください。

Button、Form、Table、Dialogなど、画面で共通利用するUI部品の見た目と使い方を定義します。

## 1. 基本方針

- **状態:** 暫定
- **基本:** DADS

### 規約

DADSに該当するUI部品がある場合は、DADSの見た目・状態・アクセシビリティ上の考え方を優先します。

同じ役割の部品を、画面ごとに別の見た目で作り分けません。

### コンポーネント利用の優先順位

1. プロジェクト既存の共通コンポーネント
2. DADS公式Reactコードをもとにした共通コンポーネント
3. DADSに不足する挙動をHeadless / Unstyledライブラリで補完
4. それでも不足する場合のみ新規コンポーネントを検討

> [AI]
> - 既存の共通コンポーネントがある場合は、同じ用途のコンポーネントを新規作成しないこと。

---

## 2. Button

- **状態:** 暫定
- **出典:** DADS
- **参照ヒント:** コンポーネント > ボタン
- **ローカル参照:** `references/dads/components/button/index.md`

### 規約

- 操作の重要度に応じてボタンの種類を使い分ける
- 1つの操作領域でPrimaryを乱立させない
- 同じ意味のボタンは画面ごとに色・サイズを変えない
- ボタンのサイズはDADSの定義から選ぶ
- hover / focus / disabled等の状態を統一する

### 確認事項

- [ ] 主要操作ボタンの標準配置を決める
- [ ] 戻る / キャンセル / 保存の順序を決める

### 必須実装

`[共通Buttonコンポーネントを指定する場合はここに記載]`

---

## 3. Form

- **状態:** 暫定
- **出典:** DADS
- **参照ヒント:** コンポーネント > インプットテキスト／テキストエリア／セレクトボックス／チェックボックス／ラジオボタン／日付ピッカー・カレンダー
- **ローカル参照:** `references/dads/components/input-text/index.md`、`references/dads/components/textarea/index.md`、`references/dads/components/select/index.md`、`references/dads/components/checkbox/index.md`、`references/dads/components/radio/index.md`、`references/dads/components/date-picker/index.md`

### 対象

- Text Input
- Textarea
- Select
- Checkbox
- Radio Button
- 日付等の入力部品

### 規約

- ラベルの位置を統一する
- 必須項目の表示方法を統一する
- エラーは対象項目との関係が分かる位置に表示する
- placeholderだけをラベル代わりにしない
- 同じ種類の入力欄は高さ・余白を統一する

### 確認事項

- [ ] ラベルの標準位置を決める
- [ ] フォームを1列中心にするか決める
- [ ] 横並びを許可する条件を決める
- [ ] 必須表示の形式を決める

### 必須実装

`[共通Formコンポーネントを指定する場合はここに記載]`

---

## 4. Table / Data Table

- **状態:** 暫定
- **基本:** DADS
- **高度な操作の補完:** Carbon
- **参照ヒント:** コンポーネント > テーブル／データテーブル、テーブルコントロール（DADS）／Data table > Usage > Table toolbar / Batch actions（Carbon）
- **ローカル参照:** `references/dads/components/table/index.md`、`references/dads/components/table-control/index.md`、`references/carbon/data-table/usage.mdx`

### 規約

テーブルの見た目、文字、余白等はDADSを優先します。

必要に応じて以下の機能を利用します。

- ソート
- フィルタ
- ページング
- 行選択
- 複数行選択
- 一括操作
- 検索
- エクスポート

一覧全体に対する操作と、行単位の操作は区別して配置します。

### 確認事項

- [ ] Default / Denseのどちらを標準にするか
- [ ] 行クリックで詳細画面へ移動するか
- [ ] 操作列を設けるか
- [ ] 一括操作を利用するか

### 必須実装

`[共通Tableコンポーネントを指定する場合はここに記載]`

---

## 5. Dialog / Modal

- **状態:** 暫定
- **基本:** DADS
- **使い分けの補完:** Carbon
- **参照ヒント:** コンポーネント > モーダルダイアログ（DADS）／Modal > Usage（Modalとサイドパネルの使い分け）、UI shell right panel > Usage（Carbon）
- **検索キーワード:** modal vs side panel, editable fields, scrolling
- **ローカル参照:** `references/dads/components/modal-dialog/index.md`、`references/carbon/modal/usage.mdx`、`references/carbon/UI-shell-right-panel/usage.mdx`

### 規約

Dialogは、元画面の文脈を保ったまま短時間で完了する操作に利用します。

複雑な入力や大量の情報を扱う処理はDialogに詰め込まず、別画面やSide Panelを検討します。

### 確認事項

- [ ] Side Panel / Drawerを利用するか
- [ ] Dialogで扱う操作の目安を決める

---

## 6. Card

- **状態:** 暫定
- **出典:** DADS
- **参照ヒント:** コンポーネント > カード
- **ローカル参照:** `references/dads/components/card/index.md`

### 規約

関連する情報を一つのまとまりとして見せる必要がある場合に利用します。

意味のない装飾目的では多用しません。

---

## 7. 状態表示

- **状態:** 暫定
- **出典:** DADS
- **参照ヒント:** コンポーネント > ノティフィケーションバナー
- **ローカル参照:** `references/dads/components/notification-banner/index.md`

### 規約

エラー、警告、完了、情報などは、色だけではなくテキストやアイコン等を組み合わせて意味を伝えます。

---

## 8. 追加コンポーネント

DADSや既存共通部品にないコンポーネントが必要になった場合に記載します。

| コンポーネント | 必要な理由 | 採用元 | 状態 |
|---|---|---|---|
| `[例: Tree]` | `[理由]` | `[Radix / TanStack / 独自等]` | 要確認 |

追加する場合は、既存部品で代替できないかを確認してから採用します。
