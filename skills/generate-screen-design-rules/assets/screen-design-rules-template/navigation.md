# ナビゲーション

> 各項目の`ローカル参照`は`generate-screen-design-rules` Skillに同梱されたファイルを指し、本プロジェクトには含まれません。詳細は[README.md](./README.md)を参照してください。

メニュー、パンくず、タブ、ページ送りなど、ユーザーが画面を移動するためのルールを定義します。

## 1. ナビゲーションの役割

- **状態:** 暫定
- **基本:** DADS
- **補完:** Carbon
- **参照ヒント:** コンポーネント > パンくずナビゲーション／タブ／ページナビゲーション（DADS）／UI Shell（Header + Left panel + Right panel）全体（Carbon）
- **ローカル参照:** `references/dads/components/breadcrumb/index.md`、`references/dads/components/tab/index.md`、`references/carbon/UI-shell-header/usage.mdx`、`references/carbon/UI-shell-left-panel/usage.mdx`

### 規約

| 種類 | 主な用途 |
|---|---|
| Header | システム全体に関わるナビゲーション・共通操作 |
| Side Navigation | 業務メニュー・機能カテゴリ |
| パンくず | 現在位置と上位階層への移動 |
| タブ | 同一画面内の関連情報の切り替え |
| ページナビゲーション | 一覧のページ送り |

---

## 2. Side Navigationを使う条件

- **状態:** 暫定
- **補完元:** Carbon
- **参照ヒント:** UI shell left panel > Usage > Behavior
- **ローカル参照:** `references/carbon/UI-shell-left-panel/usage.mdx`

### 規約

- 業務機能の主要ナビゲーションとして利用する
- セカンダリナビゲーションが多い場合に利用する
- **5項目を超える場合**を利用判断の目安とする
- Side Navigationだけで深い階層を表現しない

### 確認事項

- [ ] Side Navigationを全業務画面で利用する
- [ ] 利用する画面を限定する

---

## 3. メニュー階層

- **状態:** 暫定
- **補完元:** Carbon
- **参照ヒント:** UI shell left panel > Usage
- **検索キーワード:** nested list, sub-menu
- **ローカル参照:** `references/carbon/UI-shell-left-panel/usage.mdx`

### 規約

Side Navigation内は、原則として **2階層まで** とします。

さらに深い情報は、ページ内のタブ等へ分けることを検討します。

### 参考例

```text
アンケート
├─ アンケート一覧
└─ 配信管理

分析
├─ 分析結果
└─ レポート
```

### NG例

```text
管理
└─ マスタ
   └─ 組織
      └─ 組織編集
```

---

## 4. 現在位置

- **状態:** 暫定
- **基本:** DADS
- **参照ヒント:** コンポーネント > タブ／パンくずナビゲーション（選択状態の表現）
- **ローカル参照:** `references/dads/components/tab/index.md`、`references/dads/components/breadcrumb/index.md`

### 規約

現在表示しているメニューやタブは、色だけに依存せず、選択状態が明確に分かるようにします。

---

## 5. パンくず

- **状態:** 暫定
- **出典:** DADS
- **参照ヒント:** コンポーネント > パンくずナビゲーション
- **ローカル参照:** `references/dads/components/breadcrumb/index.md`

### 規約

ページ階層をユーザーに伝える必要がある場合は、パンくずを利用します。

### 確認事項

- [ ] 原則すべての下位画面に表示する
- [ ] 階層が深い画面のみ表示する
- [ ] Side Navigationで現在位置が十分に分かる場合の扱いを決める

---

## 6. タブ

- **状態:** 暫定
- **出典:** DADS
- **補完:** Carbon
- **参照ヒント:** コンポーネント > タブ（DADS）／Tabs > Usage（Carbon）
- **検索キーワード:** number of tabs, when to use
- **ローカル参照:** `references/dads/components/tab/index.md`、`references/carbon/tabs/usage.mdx`

### 規約

タブは、同一コンテキスト内の関連情報を切り替える用途に利用します。

### NG例

- タブで別業務へ移動させる
- タブを何重にもネストする
- タブを単なる装飾として利用する

---

## 7. 狭い画面でのナビゲーション

- **状態:** 暫定
- **補完元:** Carbon
- **参照ヒント:** UI shell header > Style > Responsive behavior、UI shell left panel > Usage（Responsive behavior）
- **ローカル参照:** `references/carbon/UI-shell-header/style.mdx`、`references/carbon/UI-shell-left-panel/usage.mdx`

### 規約

画面幅が狭い場合、Header内のナビゲーションをSide Navigation側へまとめる方式を候補とします。

Side Navigationを常時表示するか、メニューボタンから開閉するかは、対象端末を確認して決めます。
