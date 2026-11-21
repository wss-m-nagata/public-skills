<!--
# 修正履歴
# {{作成日}}: 初版作成。
-->

# Nuxtコーディング規約（nuxt）

本ドキュメントは、`nuxt/`の、Vue・Nuxtに固有のコードの書き方を定める。

`> [AI]`で始まる引用は、AIが従う指示と、AIに伝える前提である。人は、読み飛ばしてよい（書き方は、[screen-design-rules/README.md](screen-design-rules/README.md)の「`[AI]`」の記載に従う）。

各サブセクションは、決まりの表（書き方）と、コードの例で示す。  
サブセクションの最後の「出典」に挙げた決まりは、Vue・Nuxt・Piniaなどの公式の推奨に基づく。  
挙げていない決まりは、このプロジェクト独自の決まりである。

## 目次

- [1. 用語](#1-用語)
- [2. 基本方針](#2-基本方針)
- [3. 命名規則](#3-命名規則)
  - [3.1. ファイルとディレクトリ](#31-ファイルとディレクトリ)
  - [3.2. 変数・関数・定数・型](#32-変数関数定数型)
  - [3.3. propsとイベント](#33-propsとイベント)
  - [3.4. 関数の種類ごとの名前](#34-関数の種類ごとの名前)
  - [3.5. テストの識別子](#35-テストの識別子)
- [4. コメントの付け方](#4-コメントの付け方)
  - [4.1. 関数のコメント](#41-関数のコメント)
  - [4.2. ファイルのコメント](#42-ファイルのコメント)
  - [4.3. 値のコメント](#43-値のコメント)
  - [4.4. 部品の入出力のコメント](#44-部品の入出力のコメント)
  - [4.5. 型のコメント](#45-型のコメント)
  - [4.6. 処理の中のコメント](#46-処理の中のコメント)
  - [4.7. テンプレートのコメント](#47-テンプレートのコメント)
- [5. コードの書き方](#5-コードの書き方)
  - [5.1. Vueのファイルの構成](#51-vueのファイルの構成)
  - [5.2. `<script setup>`の書く順番](#52-script-setupの書く順番)
  - [5.3. 関心事ごとの節](#53-関心事ごとの節)
  - [5.4. ハンドラー](#54-ハンドラー)
  - [5.5. props・イベント・v-modelの宣言](#55-propsイベントv-modelの宣言)
  - [5.6. composable](#56-composable)
  - [5.7. テンプレート](#57-テンプレート)
  - [5.8. CSS](#58-css)
- [6. 非推奨の書き方](#6-非推奨の書き方)
- [7. コードの検査](#7-コードの検査)

## 1. 用語

| 用語 | 意味 |
| --- | --- |
| ページ | `pages/`に置く、1つの画面のVueファイル。ファイルの場所が、そのまま画面のURLになる |
| 部品 | `components/`に置く、画面の一部を表すVueファイル（コンポーネント）。共通の部品と、機能の部品がある |
| 関心事 | 画面や部品の中の、1つの役割。例えばカテゴリの画面では、「基準年月」「右側のパネル」「CSV入出力」がそれぞれ1つの関心事である。1つの関心事は、その役割に必要な状態・computed・関数・watchを持つ |
| 節 | `<script setup>`の中で、1つの関心事のコードをまとめた範囲。区切りのコメントで始める（「5.3. 関心事ごとの節」） |
| ハンドラー | テンプレートで、部品のイベントに渡す関数（「3.4. 関数の種類ごとの名前」） |
| 処理の関数 | ハンドラーやほかの関数から呼ぶ関数。テンプレートには直接渡さない（「5.4. ハンドラー」） |
| composable | Vueの仕組み（`ref`、`watch`など）を使って、状態を持つ処理をまとめた関数。名前は`use`で始める（「5.6. composable」） |
| ライフサイクルフック | 部品の表示や削除のときに呼ばれる処理（`onMounted`など） |

## 2. 基本方針

| 決まり | 理由 |
| --- | --- |
| Vueの公式スタイルガイドの「優先度A：必須」と「優先度B：強く推奨」に従う | 誤りやすい書き方と、読みにくい書き方を、公式の基準で避ける |
| 本規約は、スタイルガイドのうち特に守るものと、スタイルガイドにない決まりを定める。食い違う場合は、本規約に従う | スタイルガイドは、チームの事情に応じて、考えたうえで外れることを認めている |
| 本規約に書いていないスタイルガイドの優先度A・Bの規則も、守る | 規約を短く保ちながら、公式の基準を外さない |
| スタイルガイドから外れる箇所には、理由をコメントで書く（「4.6. 処理の中のコメント」） | 意図した例外か、見落としかを区別できる |

**出典**
- スタイルガイドに従うこと、考えたうえで外れることを認めていること：[Vueスタイルガイド](https://ja.vuejs.org/style-guide/)

## 3. 命名規則

### 3.1. ファイルとディレクトリ

#### 3.1.1. 書き方

| 対象 | 付け方 | 理由 |
| --- | --- | --- |
| 部品のファイル | パスカルケース。2つ以上の単語にし、単語は略さない | テンプレートのタグ名で検索して、ファイルを見つけられる。1単語の名前は、HTMLの要素と名前がぶつかる。略した名前は、意味が分かりにくい |
| 共通の部品のファイル | 先頭に`App`と分類名を付ける | ファイル名と同じ名前で、部品を使える |
| 共通の部品の分類のディレクトリ | 小文字の英単語1語 | 部品の名前に入る分類名を、短くそろえる |
| 機能の部品のファイル | 先頭に機能名を付ける | ファイル名と同じ名前で、部品を使える |
| ページ以外のContainerのファイル | 機能の部品の付け方に加え、末尾に`Container`を付ける（[フロントエンド実装方針.md](フロントエンド実装方針.md)の「4.1.1. ページ以外のContainer」） | 機能のcomposableを呼ぶ部品であることを、ページのタグから見分けられる |
| 機能のディレクトリ | ケバブケース | ページのURLと、書き方をそろえる |
| ページのファイルとディレクトリ | ケバブケース（[URL命名規則](../../../docs/20_rules/URL命名規則.md)に従う）。1単語（`index.vue`など）でよい | ファイルの場所が、そのまま画面のURLになる。ページは、タグとして使わないため、HTMLの要素と名前がぶつからない |
| composableのファイル | 先頭に`use`を付けたキャメルケース。中の関数と同じ名前にする | Vueの状態を持つ関数であることが、名前から分かる |
| storeのファイル | storeの名前のキャメルケース。中の関数は`use`＋storeの名前＋`Store` | composableと区別できる |
| utilsのファイル | 機能名か、まとめた内容のキャメルケース。関係する関数をまとめてよい。機能のutilsが長くなり、関心事ごとに分けるときは、機能のディレクトリ（ケバブケース）の下に、関心事の名前のファイルで置く（[フロントエンド実装方針.md](フロントエンド実装方針.md)の「4.3. composable・utils・型の置き場所」） | 関係する関数を1か所で探せる |
| 型のファイル | 機能名か、まとめた内容のキャメルケース。共通の型は`types/app/`に、機能の型は`types/<機能名>.ts`に1つのファイルで置く | composable・utilsのファイルと、書き方と分け方をそろえる。Nuxtは、`.ts`のファイル名の書き方を決めていないため、プロジェクトの中でそろえる |
| pluginsのファイル | ケバブケース。読み込む順番を決めるときは、先頭に番号を付ける | Nuxtは、ファイル名の順に読み込む |
| middlewareのファイル | ケバブケース。画面を移るたびに必ず行うものは、末尾に`.global`を付ける | Nuxtは、`.global`の付いたものを、すべての画面の移動で行う |

#### 3.1.2. 例

```text
app/
├── components/
│   ├── app/                              … 共通の部品
│   │   └── feedback/                     … 分類のディレクトリ（小文字の英単語1語）
│   │       └── AppFeedbackConfirmDialog.vue   … <AppFeedbackConfirmDialog /> で使う
│   └── product-catalog/                    … 機能のディレクトリ（ケバブケース。機能 CAT01「商品カテゴリ管理」の英語名）
│       ├── ProductCatalogTreeCanvas.vue        … <ProductCatalogTreeCanvas /> で使う
│       └── ProductCatalogCsvContainer.vue      … ページ以外のContainer。末尾に Container を付ける
├── composables/
│   └── product-catalog/
│       └── useProductCatalogApi.ts             … useProductCatalogApi() を定義する
├── stores/
│   └── productCatalog.ts                   … useProductCatalogStore() を定義する
├── utils/
│   ├── app/
│   │   └── isoDate.ts                    … 日付の変換の関数をまとめる
│   └── product-catalog/                    … 機能のutilsを、関心事ごとのファイルに分けたもの
│       ├── editTree.ts                   … 編集用のツリーの処理
│       └── csv.ts                        … カテゴリツリーのCSV
├── types/
│   ├── app/
│   │   └── feedback.ts                   … 共通の型
│   └── productCatalog.ts                   … 商品カテゴリ管理の機能の型
├── plugins/
│   └── 01.env-config.ts                  … 番号の順に読み込まれる
├── middleware/
│   └── auth.global.ts                    … すべての画面の移動で行う
└── pages/
    └── catalog/categories/
        └── index.vue                     … URLは /catalog/categories
```

> [AI]
> - Nuxtは、部品が置かれたディレクトリの名前を、部品の名前の先頭に付ける。ファイル名を、ディレクトリ名のパスカルケースで始めれば、重複が除かれる。始めなければ、`<AppFeedbackAppConfirmDialog />`のように、長い名前になる。

**出典**
- 部品のファイル：[Vueスタイルガイド「単一ファイルコンポーネントのファイル名の形式」「略さないコンポーネント名」](https://ja.vuejs.org/style-guide/rules-strongly-recommended.html)、[Vueスタイルガイド「複数の単語からなるコンポーネント名」](https://ja.vuejs.org/style-guide/rules-essential.html)
- 共通の部品・機能の部品のファイル：[Nuxt「components」](https://nuxt.com/docs/4.x/guide/directory-structure/app/components)
- composableのファイル：[Vue「コンポーザブル」の「命名」](https://ja.vuejs.org/guide/reusability/composables.html)
- storeのファイル：[Pinia「Defining a Store」](https://pinia.vuejs.org/core-concepts/)
- pluginsのファイル：[Nuxt「plugins」](https://nuxt.com/docs/4.x/guide/directory-structure/app/plugins)
- middlewareのファイル：[Nuxt「middleware」](https://nuxt.com/docs/4.x/guide/directory-structure/app/middleware)

### 3.2. 変数・関数・定数・型

#### 3.2.1. 書き方

| 対象 | 付け方 | 理由 |
| --- | --- | --- |
| 変数・関数 | キャメルケース | JavaScriptで一般的な書き方にそろえる |
| 定数（実行中に変わらない、決まった値） | 大文字のスネークケース | 変わる値と、変わらない値を見分けられる |
| 型・インターフェース | パスカルケース | 値と型を見分けられる |
| 真偽値の変数 | `is`・`has`・`can`のどれかで始める | 状態か、持っているか、できるかを読み取れる |

#### 3.2.2. 例

```ts
/** この画面で扱う最下層の階層 */
const MAX_LEVEL = 7

/** カテゴリツリーを取得しているか */
const isLoading = ref(false)

/** 追加・除外・移管の変更があるか */
const hasChanges = computed(() => hasCatalogChanges(editNodes.value))

/** 更新ボタンを押せるか */
const canUpdate = computed(() => mode.value === 'edit' && hasChanges.value)

/** ツリーの1ノード */
interface CategoryNode {
  /** ノードの識別子 */
  id: string
  /** カテゴリ名 */
  name: string
}
```

### 3.3. propsとイベント

#### 3.3.1. 書き方

| 対象 | 付け方 | 理由 |
| --- | --- | --- |
| props | 宣言はキャメルケース、テンプレートで渡すときはケバブケース | JavaScriptでは識別子として使え、テンプレートではHTMLの属性と見た目がそろう |
| イベント | 宣言はキャメルケース、テンプレートで受けるときはケバブケース | propsと同じ |

#### 3.3.2. 部品の側の例

```ts
defineProps<{
  /** 列の間隔（px） */
  rankSep: number
}>()

defineEmits<{
  /**
   * カテゴリが押されたとき。
   * 押されたカテゴリを渡す。
   */
  nodeClick: [node: CategoryNode]
}>()
```

#### 3.3.3. 親の側の例

```vue
<ProductCatalogTreeCanvas :rank-sep="appliedRankSep" @node-click="onTreeNodeClick" />
```

**出典**
- props：[Vueスタイルガイド「props 名の形式」](https://ja.vuejs.org/style-guide/rules-strongly-recommended.html)、[Vue「Props」](https://ja.vuejs.org/guide/components/props.html)
- イベント：[Vue「コンポーネントのイベント」](https://ja.vuejs.org/guide/components/events.html)

### 3.4. 関数の種類ごとの名前

#### 3.4.1. 書き方

| 区分 | 付け方 | 理由 |
| --- | --- | --- |
| イベント用の関数（ハンドラー） | `on`＋部品＋イベント名。部品は画面の上での名前で表し、イベント名だけで分かる場合も省かない | どの部品の、どのイベントで呼ばれるかが分かる。省くかどうかで、人によって名前が分かれない |
| 処理の関数（内部の関数） | 動詞＋対象。真偽値を返す関数は、`is`・`has`・`can`で始める | 何をする関数か、何を判定する関数かが分かる |

ハンドラーと処理の関数の使い分けは、「5.4. ハンドラー」に従う。

#### 3.4.2. 例

```vue
<script setup lang="ts">
/**
 * カテゴリを、別の商品に切り替えられるかを判定する。
 *
 * @param node - 判定するカテゴリ
 * @returns 切り替えられるときは true
 */
function canSwitch(node: CategoryNode): boolean {
  return !node.placeholder && node.parentId !== null
}

/**
 * ツリーのカテゴリが押されたときに、右側のパネルを開く。
 * 編集のときに切り替えられるカテゴリなら編集パネルを、それ以外は詳細パネルを開く。
 *
 * @param node - 押されたカテゴリ
 */
function onTreeNodeClick(node: CategoryNode) {
  panelKind.value = mode.value === 'edit' && canSwitch(node) ? 'edit' : 'view'
  selectedNode.value = node
}
</script>

<template>
  <ProductCatalogTreeCanvas :nodes="targetNodes" @node-click="onTreeNodeClick" />
</template>
```

### 3.5. テストの識別子

#### 3.5.1. 書き方

| 対象 | 付け方 | 理由 |
| --- | --- | --- |
| `data-testid` | ケバブケース（[E2Eテスト作成規約.md](../../../docs/20_rules/E2Eテスト作成規約.md)の「画面側に識別子を付ける」に従う） | E2Eテストの決まりを1か所で管理する |

#### 3.5.2. 例

```vue
<AppFormButton data-testid="search-button" @click="onSearchClick">
  {{ $t('button.search') }}
</AppFormButton>
```

## 4. コメントの付け方

### 4.1. 関数のコメント

すべての関数（ハンドラー、処理の関数）の直前に、コメントを書く。

#### 4.1.1. 書き方

| 項目 | 決まり | 理由 |
| --- | --- | --- |
| 1行目 | 関数が何をするかを、短い1文で書く（目安は30文字まで）。いつ呼ばれるか（どの操作で呼ぶか）は、2行目に書く | エディターで関数にマウスを重ねたときに、最初に表示される。長いと、何をする関数かが分かりにくい |
| 2行目から | いつ呼ばれるか、条件による動きの違い、コードから分からない理由を、1文ごとに改行して書く | 1文ずつ読めるようにする。1行目で足りることは繰り返さない |
| 説明とタグの間 | 説明と`@param`・`@returns`の間に、`*`だけの行を入れる | 説明とタグの境目が、ひと目で分かる |
| 1行で書く場合 | 説明が1文で、`@param`・`@returns`がないときだけ、`/** … */`の1行で書く。2文以上なら、1文ごとに改行した複数行にする | 1行に複数の文を詰めると、読みにくい |
| `@param` | 引数があるときは、引数ごとに必ず、`@param 引数名 - 説明`の形で書く。型は書かない | 書くかどうかの判断が、人によって分かれない。型はコードに書くため、コメントにも書くと、型を変えたときに食い違う |
| `@returns` | 戻り値があるときは、必ず書く（`Promise<void>`を返す関数は、戻り値がないものとして扱う）。型は書かない | `@param`と同じ |
| 文体 | である調で書く（「〜する」「〜を返す」） | 文末をそろえ、短く書ける |

#### 4.1.2. 引数と戻り値がある関数の例

```ts
/**
 * CSVファイルの文字を読む。
 * UTF-8として読めなければ、Shift_JIS（表計算ソフトの既定の保存形式）として読む。
 *
 * @param file - 利用者が選んだCSVファイル
 * @returns ファイルの文字（文字コードは、UTF-8かShift_JISのどちらかとして読んだもの）
 */
async function readCsvFile(file: File): Promise<string> {
  const buffer = await file.arrayBuffer()
  try {
    // 文字コードが UTF-8 として正しくなければ、例外にする
    return new TextDecoder('utf-8', { fatal: true }).decode(buffer)
  } catch {
    return new TextDecoder('shift_jis').decode(buffer)
  }
}
```

#### 4.1.3. 引数と戻り値がない関数の例

`@param`と`@returns`は書かない。

```ts
/**
 * 基準年月を今月に戻す。
 * 「現在へ戻す」ボタンが押されたときに呼ぶ。
 * 未保存の変更があるときは、何もしない。
 */
function onRestoreCurrentClick() {
  if (!canRestoreCurrent.value) return
  monthInput.value = currentMonth()
  // カテゴリツリーは、URLの変更から取り直す
  void updateSearchUrl(appliedCode.value, currentMonth())
}
```

**出典**
- `@param`、`@returns`の書き方：[TSDoc「@param」](https://tsdoc.org/pages/tags/param/)、[TSDoc「@returns」](https://tsdoc.org/pages/tags/returns/)

### 4.2. ファイルのコメント

ファイルの先頭に、修正履歴と、ファイルの説明を書く。

#### 4.2.1. 書き方

| 項目 | 決まり | 理由 |
| --- | --- | --- |
| 修正履歴 | `.vue`は先頭に`<!-- -->`で、`.ts`は先頭に`//`で書く。1行の形は[リポジトリ規約](../../../docs/20_rules/リポジトリ規約.md)に従う | 変更の経緯を、コメントや本文に混ぜずに、1か所に残す |
| ファイルの説明 | `.vue`は`<script setup>`の先頭に、`.ts`は修正履歴の次に、`//`で書く | ファイルを開いたときに、最初に役割が分かる |
| 部品・composable・utilsの説明に書くこと | 何を受け持つか、何を受け持たないか（親や別の部品に任せること） | 部品とページの役割の境目を、ファイルを開いただけで確かめられる |
| ページの説明に書くこと | 次の見出しごとにまとめて書く（「4.2.3. ページの例」）。<br/>「画面名」：画面設計書の画面名と画面ID。<br/>「概要」：画面で何ができるかを、1〜2文で書く。<br/>「機能の部品」「機能のcomposable」「機能のutils」：そのページが使う、その機能のものを、1行に1つ、名前と役割で書く。使わない見出しは書かない。<br/>共通のもの（`App`で始まる部品、`composables/app/`、`utils/app/`）は書かない | 形をそろえると、どの画面でも、同じ場所に同じことが書かれ、読む人が探さずに済む。共通のものは数が多く、書くと説明が長くなり、直し忘れも増える |

#### 4.2.2. 部品の例

```vue
<!--
修正履歴
2026/11/17: ABC山田 太郎: 初版作成。
-->
<script setup lang="ts">
// CSV入出力の子画面。インポート用CSVのダウンロードと、CSVファイルの読み込みを受け付ける。
// CSVの作成と、読み込んだ内容の反映は、画面が行う。
import type { ProductCandidate } from '~/types/productCatalog'
```

#### 4.2.3. ページの例

```vue
<script setup lang="ts">
// 画面名：商品カテゴリ管理（SCR0101）
// 概要：商品カテゴリをツリーで表示し、カテゴリ内の商品を追加・除外・移動する。
//
// 機能の部品
// - ProductCatalogTreeCanvas：ツリーの描画
// - ProductCatalogAddPanel：商品の追加の入力
//
// 機能のcomposable
// - useProductCatalogApi：カテゴリツリーと商品の候補の取得
//
// 機能のutils
// - utils/product-catalog/editTree.ts：編集用のツリーを作る・読む関数
import type { CategoryNode } from '~/types/productCatalog'
```

#### 4.2.4. `.ts`の例

```ts
// 修正履歴
// 2026/11/16: ABC山田 太郎: 初版作成。

// カテゴリツリーの画面が使うAPI（カテゴリツリーの取得、商品の候補の取得）を呼ぶ。
import type { ProductCandidate, CategoryTreeEdge } from '~/types/productCatalog'
```

### 4.3. 値のコメント

`<script setup>`の中で、関数の外に宣言する値（`ref`、`computed`、定数）に、コメントを書く。  
関数の中で宣言する一時的な変数には、書かなくてよい。

#### 4.3.1. 書き方

| 項目 | 決まり | 理由 |
| --- | --- | --- |
| 形 | 直前に`/** */`で書く。1文なら1行で、2文以上なら1文ごとに改行した複数行で書く | エディターで、値を使う箇所にマウスを重ねたときに、説明が表示される。1行に複数の文を詰めると、読みにくい |
| 内容 | 何を表すか。値の形式（`YYYY-MM`など）、空のときの意味（`null`なら未選択など）があれば、それも書く | 値の名前と型だけでは、形式と空の意味が分からない |

#### 4.3.2. 例

```ts
/**
 * この画面で扱う最下層の階層。
 * これより深い階層は、表示も追加もしない。
 */
const MAX_LEVEL = 7

/**
 * 反映済みの基準年月（YYYY-MM）。
 * カテゴリツリーは、この年月で表示している。
 */
const asOfMonth = ref(currentMonth())

/**
 * 右側のパネルで表示しているカテゴリ。
 * パネルを閉じているときは null。
 */
const selectedNode = ref<CategoryNode | null>(null)

/**
 * 基準年月の月初日（YYYY-MM-DD）。
 * APIには、この日付を渡す。
 */
const asOfDate = computed(() => monthToFirstDate(asOfMonth.value))
```

### 4.4. 部品の入出力のコメント

部品が受け取るもの（props、`defineModel`、スロット）と、部品が出すもの（イベント、`defineExpose`で公開する関数）に、コメントを書く。

#### 4.4.1. 書き方

項目ごとに、直前に`/** */`でコメントを書く。  
部品を使う人が、エディターでマウスを重ねたときに、項目の説明を確かめられるためである。  
`defineExpose`で公開する関数は、「4.1. 関数のコメント」と同じ形で書く。

| 項目 | 書く内容 | 理由 |
| --- | --- | --- |
| props | 意味と、空のときの意味 | 名前と型だけでは、空のときの意味が分からない |
| イベント | いつ出すかと、渡す値 | 親が、どの操作で呼ばれるかを、宣言から読み取れる |
| `defineModel` | 親と持ち合う値の意味 | propsと同じ |
| スロット | 何を差し込む場所か | 親が、何を差し込めばよいかを、宣言から読み取れる |
| `defineExpose`で公開する関数 | 何をするか（「4.1. 関数のコメント」） | 親から呼ぶ関数であり、通常の関数と同じく説明が要る |

#### 4.4.2. 例

```vue
<script setup lang="ts">
// CSV入出力の子画面。インポート用CSVのダウンロードと、CSVファイルの読み込みを受け付ける。
// CSVの作成と、読み込んだ内容の反映は、画面が行う。

defineProps<{
  /**
   * 読み込んだCSVの誤り。
   * 誤りがなければ空。
   */
  errors: string[]
}>()

const emit = defineEmits<{
  /** インポート用CSVのダウンロードが押されたとき */
  download: []
  /**
   * 読み込むが押されたとき。
   * 選んだCSVファイルを渡す。
   */
  load: [file: File]
}>()

/** 子画面を開いているか */
const isOpen = defineModel<boolean>({ required: true })

defineSlots<{
  /** 子画面の下に置く、補足の説明 */
  note?: () => unknown
}>()

/** ファイルの選択欄 */
const fileInput = useTemplateRef<HTMLInputElement>('fileInput')

/** ファイルの選択欄に、フォーカスを移す。 */
function focusFileInput() {
  fileInput.value?.focus()
}

defineExpose({ focusFileInput })
</script>
```

### 4.5. 型のコメント

`types/`などに置く型（インターフェース、型の別名）に、コメントを書く。

#### 4.5.1. 書き方

型と、型の項目ごとに、直前に`/** */`でコメントを書く。

| 項目 | 書く内容 | 理由 |
| --- | --- | --- |
| 型そのもの | 何を表す型か。APIの入出力の型は、どのAPIのものかも書く | 型を使う箇所で、何のデータかが分かる |
| 項目 | 意味と、値の範囲や空のときの意味 | 項目の名前と型だけでは、値の範囲と空の意味が分からない |
| 決まった値の組み合わせ | それぞれの値の意味（型そのもののコメントに書く） | 値ごとの意味を、1か所で確かめられる |

#### 4.5.2. 例

```ts
/** 配置候補の商品（GET /catalog/products/candidates の1件） */
export interface ProductCandidate {
  /** 業務上の商品コード */
  code: number
  /** 商品の名称 */
  name: string
}

/**
 * ツリーの1ノード。
 * 親子の一覧から組み立てる。
 */
export interface CategoryNode {
  /**
   * ノードの識別子。
   * カテゴリコード（8桁）か、階層の抜けを埋める空ノードの識別子。
   */
  id: string
  /**
   * 親ノードの識別子。
   * 最上位は null。
   */
  parentId: string | null
  /** 階層（1〜8） */
  level: number
}

/**
 * 処理区分。
 * view は参照、edit は編集。
 */
export type CatalogMode = 'view' | 'edit'
```

### 4.6. 処理の中のコメント

関数の中、`watch`、ライフサイクルフック、節の区切りなどには、直前に`//`でコメントを書く。  
今の動作と、コードから分からない理由を書き、変更の経緯は書かない（経緯は修正履歴に書く）。  
コメントに経緯が混ざると、どれが今の動作か分からなくなるためである。

#### 4.6.1. 書き方

| 箇所 | 書く内容 | 理由 |
| --- | --- | --- |
| 関数の中の処理の区切り | その区切りが何をするか | 処理の流れを、コメントだけを追って読める |
| `watch`、ライフサイクルフック | 何をきっかけに、何をするか | 名前のない処理であり、何のためにあるかが、コードだけでは分からない |
| 節の区切り | 1行目に`// --- 関心事の名前 ---`、次の行から、その節が何を受け持つか（「5.3. 関心事ごとの節」） | 節の境目と役割を、読み始めの位置で分かるようにする |
| 決まりから外れる箇所 | 外れる理由（スタイルガイドから外れる書き方、ESLintの規則の無効化など） | あとから読む人が、意図した例外か、見落としかを区別できる |

#### 4.6.2. 例

```ts
// --- 商品の候補 ---
// 追加パネルか編集パネルを開いているときに、基準年月に有効な商品を取得して、パネルへ渡す

/** パネルへ渡す商品の候補 */
const products = ref<ProductCandidate[]>([])

/**
 * 最後に始めた取得の番号。
 * 古い取得の結果を捨てるために使う。
 */
let productRequest = 0

/** 基準年月に有効な商品を取得する。 */
async function loadProducts() {
  const request = ++productRequest
  const result = await fetchProducts(asOfDate.value)
  // 古い取得の結果で、新しい結果を上書きしない
  if (request === productRequest) products.value = result
}

// パネルを開いている間に基準年月が変わったときに、商品を取り直す
watch(asOfDate, () => {
  if (isProductPanelOpen.value) void loadProducts()
})
```

### 4.7. テンプレートのコメント

次の箇所には、直前に`<!-- -->`でコメントを書く。

#### 4.7.1. 書き方

| 箇所 | 書く内容 | 理由 |
| --- | --- | --- |
| 意味のまとまり | 画面の上での名前 | テンプレートの中で、画面のどの部分かを探せる |
| 見て分からない書き方 | そう書く理由 | 書き換えてよいかを、あとから読む人が判断できる |

#### 4.7.2. 例

```vue
<template>
  <!-- 検索条件 -->
  <section aria-labelledby="search-title">
    <!-- 確定した年月は、URLを更新してから反映するため、v-model ではなく、確定の通知で受け取る -->
    <AppFormMonthField
      v-model:draft="monthInput"
      :model-value="asOfMonth"
      @update:model-value="onMonthFieldUpdate"
    />
  </section>
</template>
```

## 5. コードの書き方

### 5.1. Vueのファイルの構成

#### 5.1.1. 書き方

| 項目 | 決まり | 理由 |
| --- | --- | --- |
| ブロックの順番 | 処理（`script setup`）、画面（`template`）、見た目（`style scoped`）の順に書く。見た目は、必要な場合だけ書く | どのファイルでも、処理・画面・見た目の場所をすぐに見つけられる |
| 処理のブロック | `script setup`だけを使い、通常の`script`は使わない | 通常の`script`は、読み込み時に1回だけ実行され、部品ごとの状態を持てない |
| 部品の設定 | `defineOptions`で書く | 通常の`script`を使わずに、部品の設定を書ける |

#### 5.1.2. 例

```vue
<!--
修正履歴
2026/11/20: ABC山田 太郎: 初版作成。
-->
<script setup lang="ts">
// 項目の説明を、ヘルプのアイコンと文で表示する部品。
// 受け取った属性は、外側の要素ではなく、アイコンのボタンに付ける。
defineOptions({ inheritAttrs: false })

defineProps<{
  /** アイコンの横に表示する説明 */
  text: string
}>()
</script>

<template>
  <span class="help">
    <v-btn v-bind="$attrs" icon="mdi-help-circle-outline" variant="text" size="small" />
    <span>{{ text }}</span>
  </span>
</template>

<style scoped>
/* ヘルプ：アイコンと説明を横に並べる。 */
.help {
  display: inline-flex;
  gap: 4px;
}
</style>
```

**出典**
- 通常の`script`を使わないこと、`defineOptions`：[Vue「`<script setup>`」の「通常の `<script>` との併用」「defineOptions()」](https://ja.vuejs.org/api/sfc-script-setup.html)

### 5.2. `<script setup>`の書く順番

#### 5.2.1. 書き方

`<script setup>`の中は、次の順に書く。  
どのファイルでも、部品の入出力、共通で使うもの、画面の処理の順に読めるようにするためである。

| 順番 | 書くもの | 書く場面 |
| --- | --- | --- |
| 1 | import | |
| 2 | ページの設定（`definePageMeta`） | ページだけ |
| 3 | 部品の入出力の宣言（props、イベント、v-model、スロットの順） | 部品だけ |
| 4 | ファイル全体で使う定数 | |
| 5 | ファイル全体で使うcomposableの呼び出し | |
| 6 | 関心事ごとの節（「5.3. 関心事ごとの節」） | |
| 7 | 複数の節にまたがる、画面を開いたときの処理 | |
| 8 | 親に公開する関数（`defineExpose`） | 部品だけ |

#### 5.2.2. ページの例

```vue
<script setup lang="ts">
// カテゴリの画面。カテゴリの階層をツリーで表示し、選んだカテゴリの詳細をパネルで表示する。
import type { CategoryNode } from '~/types/productCatalog'

definePageMeta({ businessLinks: 'menu-group' })

/** この画面で扱う最下層の階層 */
const MAX_LEVEL = 7

const route = useRoute()
const { fetchTree } = useProductCatalogApi()

// --- カテゴリツリーの取得 ---
// 指定した年月のカテゴリツリーを取得して持つ

/** 取得したカテゴリツリーのノード */
const nodes = shallowRef<CategoryNode[]>([])

/**
 * 指定した年月のカテゴリツリーを取得する。
 *
 * @param month - 取得する年月（YYYY-MM）
 */
async function loadTree(month: string) {
  const result = await fetchTree(month)
  nodes.value = result.filter((node) => node.level <= MAX_LEVEL)
}

// --- 右側のパネル ---
// ツリーで選んだカテゴリの詳細を、パネルで表示する

/**
 * パネルで表示しているカテゴリ。
 * パネルを閉じているときは null。
 */
const selectedNode = ref<CategoryNode | null>(null)

// URLの年月でカテゴリツリーを取得し、最上位のカテゴリの詳細を開く
onMounted(async () => {
  await loadTree(String(route.query.month ?? currentMonth()))
  selectedNode.value = nodes.value[0] ?? null
})
</script>
```

#### 5.2.3. 部品の例

「4.4.2. 例」に示す（props、イベント、v-model、スロット、関数、`defineExpose`の順）。

### 5.3. 関心事ごとの節

#### 5.3.1. 書き方

| 項目 | 決まり | 理由 |
| --- | --- | --- |
| まとめ方 | 状態・computed・関数・watchを、種類ごとではなく、関心事（画面の中の1つの役割）ごとにまとめる | 1つの役割を追うときに、ファイルの中を行き来しなくて済む。composableへ切り出すときも、まとまりのまま移せる |
| 区切り | 節の先頭に、区切りのコメントを書く（「4.6. 処理の中のコメント」） | 節の境目と役割を、読み始めの位置で分かる |
| 節の中の順番 | 状態、computed、関数、watch・ライフサイクルフックの順に書く | watchとライフサイクルフックは関数を呼ぶ側のため、最後に置けば、使う箇所より前で宣言できる |
| computed | 1つのcomputedでは、1つの値を求める。計算が複雑なときは、名前を付けた複数のcomputedに分ける | 何を求めているかが名前から分かり、途中の値も使い回せる |
| ライフサイクルフック | 1つの節にしか関わらないものは、その節に置く | 処理の始まりと、その処理の状態を、同じ場所で読める |
| 宣言の位置 | 変数と関数は、使う箇所より前で宣言する | 定義を探して、下へ読み進めなくて済む。宣言より前の参照は、実行の順番によってはエラーになる |
| composableへの切り出し | 節が長くなり、ほかの節から独立したまとまりになったときに切り出す（基準は、[フロントエンド実装方針.md](フロントエンド実装方針.md)の「4.2. 切り出しと共有の判断」に従う） | ページを、画面の組み立てと、その画面に固有の処理に絞れる |

#### 5.3.2. 例

```ts
// --- 基準年月 ---
// カテゴリツリーの基準年月を持ち、年月の欄で確定した年月をURLへ反映する

/** 反映済みの基準年月（YYYY-MM） */
const asOfMonth = ref(currentMonth())

/**
 * 基準年月の月初日（YYYY-MM-DD）。
 * APIには、この日付を渡す。
 */
const asOfDate = computed(() => monthToFirstDate(asOfMonth.value))

/**
 * 年月の欄で年月が確定したときに、URLを更新する。
 *
 * @param month - 確定した年月（YYYY-MM）
 */
function onMonthFieldUpdate(month: string) {
  void router.push({ query: { ...route.query, month } })
}

// URLの年月が変わったときに、基準年月を合わせる
watch(
  () => route.query.month,
  (month) => {
    if (typeof month === 'string') asOfMonth.value = month
  },
)
```

**出典**
- 関心事ごとのまとめ方：[Vue「Composition API FAQ」の「より柔軟なコード構成」](https://ja.vuejs.org/guide/extras/composition-api-faq.html)
- computed：[Vueスタイルガイド「単純な算出プロパティ」](https://ja.vuejs.org/style-guide/rules-strongly-recommended.html)
- composableへの切り出し：[Vue「コンポーザブル」の「コード整理のためのコンポーザブルの抽出」](https://ja.vuejs.org/guide/reusability/composables.html)

### 5.4. ハンドラー

#### 5.4.1. 書き方

| 項目 | 決まり | 理由 |
| --- | --- | --- |
| テンプレートに渡すもの | ハンドラーだけを渡す。処理の関数は、直接渡さない | テンプレートの中で、ハンドラーとそれ以外の関数が混ざらない |
| 処理の置き場所 | まずハンドラーの中に書く。ほかの場所からも呼ぶ処理だけ、処理の関数に分けて、ハンドラーから呼ぶ | 1か所からしか呼ばない処理を分けると、呼び出し先を追う手間が増える |
| コメント | ハンドラーが何をするかを、関数のコメントに書く（「4.1. 関数のコメント」） | `submit`のように、イベント名から中身が分からない場合がある |

#### 5.4.2. 例

`loadProducts`は、ハンドラーと`watch`の2か所から呼ぶため、処理の関数に分けている。

```vue
<script setup lang="ts">
/** 基準年月に有効な商品を取得する。 */
async function loadProducts() {
  products.value = await fetchProducts(asOfDate.value)
}

/** 編集パネルの「再読み込み」が押されたときに、商品を取り直す。 */
function onEditPanelRetry() {
  void loadProducts()
}

// パネルを開いている間に基準年月が変わったときに、商品を取り直す
watch(asOfDate, () => {
  if (isProductPanelOpen.value) void loadProducts()
})
</script>

<template>
  <ProductCatalogEditPanel :products="products" @retry="onEditPanelRetry" />
</template>
```

### 5.5. props・イベント・v-modelの宣言

#### 5.5.1. 書き方

| 項目 | 決まり | 理由 |
| --- | --- | --- |
| props | 型引数で宣言する | TypeScriptの型で、渡す値を検査できる |
| propsの既定値 | `withDefaults`で指定する | 分割代入で既定値を付けると、watchで監視するときにgetterで包む必要があり、包み忘れると監視されない |
| イベント | 型引数で、イベント名と引数の名前を宣言する。部品が出すイベントは、すべて宣言する | 親が受け取る値の型と意味を、宣言から読み取れる |
| v-model | 親と同じ値を持ち合う場合は、`defineModel`を使う。1つの部品で複数の値を持ち合う場合は、名前を付ける | propsとイベントを個別に書くより短く、書き間違えない |

#### 5.5.2. 例

```ts
withDefaults(
  defineProps<{
    /** 見出しの文字 */
    title: string
    /**
     * 見出しの階層。
     * 省略したときは 2。
     */
    level?: 2 | 3
  }>(),
  { level: 2 },
)

defineEmits<{
  /** 閉じるが押されたとき */
  close: []
  /**
   * カテゴリが押されたとき。
   * 押されたカテゴリを渡す。
   */
  nodeClick: [node: CategoryNode]
}>()

/**
 * パネルを開いているか。
 * 親と持ち合う。
 */
const isOpen = defineModel<boolean>({ required: true })

/**
 * 入力中の年月（YYYY-MM）。
 * 親の v-model:draft と持ち合う。
 */
const draft = defineModel<string>('draft')
```

**出典**
- props、propsの既定値、イベント：[Vue「TypeScript とコンポジション API」](https://ja.vuejs.org/guide/typescript/composition-api.html)、[Vue「コンポーネントのイベント」](https://ja.vuejs.org/guide/components/events.html)
- v-model：[Vue「コンポーネントの v-model」](https://ja.vuejs.org/guide/components/v-model.html)

### 5.6. composable

#### 5.6.1. 書き方

| 項目 | 決まり | 理由 |
| --- | --- | --- |
| composableにするもの | Vueの仕組み（`ref`、`watch`など）を使って、状態を持つ処理。状態を持たない関数は、utilsに置く | composableと、ただの関数を、名前と置き場所で見分けられる |
| 戻り値 | `ref`と関数を入れた、普通のオブジェクトにする（`reactive`で包まない） | 呼び出し側で分割代入しても、値の変化が伝わる |
| 引数 | 値・`ref`・getterのどれでも受け取れるようにし、`toValue`で値を取り出す | 呼び出し側が、値の形を気にせずに渡せる |
| 呼ぶ場所 | `script setup`の中で、同期的に呼ぶ。`await`のあとや、関数の中では呼ばない | Vueが、どの部品のcomposableかを判断でき、部品が消えたときに片付けられる |
| 共有の方法 | 部品の間で処理を共有するときは、mixinと、表示を持たない部品を使わず、composableにする | 公式が、Vue 3ではcomposableを推奨している |

#### 5.6.2. composableのファイルの例

```ts
// 修正履歴
// 2026/11/20: ABC山田 太郎: 初版作成。

// 基準日に有効な商品の候補を取得して持つ。
import type { MaybeRefOrGetter } from 'vue'
import type { ProductCandidate } from '~/types/productCatalog'

/**
 * 基準日に有効な商品の候補を取得して持つ。
 *
 * @param date - 基準日（YYYY-MM-DD）。値・ref・getterのどれでもよい
 * @returns 商品の候補、取得しているか、取得する関数
 */
export function useProducts(date: MaybeRefOrGetter<string>) {
  const { fetchProducts } = useProductCatalogApi()

  /** 商品の候補 */
  const products = ref<ProductCandidate[]>([])

  /** 商品を取得しているか */
  const isLoadingProducts = ref(false)

  /** 基準日に有効な商品を取得する。 */
  async function loadProducts() {
    isLoadingProducts.value = true
    try {
      products.value = await fetchProducts(toValue(date))
    } finally {
      isLoadingProducts.value = false
    }
  }

  return { products, isLoadingProducts, loadProducts }
}
```

#### 5.6.3. 呼び出す側の例

`script setup`の中で、同期的に呼ぶ。

```ts
const { products, isLoadingProducts, loadProducts } = useProducts(asOfDate)
```

**出典**
- composableにするもの：[Vue「用語集」の「composable」](https://ja.vuejs.org/glossary/#composable)
- 戻り値、引数、呼ぶ場所、共有の方法：[Vue「コンポーザブル」](https://ja.vuejs.org/guide/reusability/composables.html)

### 5.7. テンプレート

#### 5.7.1. 書き方

| 項目 | 決まり | 理由 |
| --- | --- | --- |
| 繰り返し（`v-for`） | 要素を一意に表す値を、`key`に必ず指定する。配列の番号は使わない | 並びが変わったときに、表示と入力の状態がずれない |
| 繰り返しと条件 | `v-for`と`v-if`を、同じ要素に書かない。絞り込みはcomputedで行う | 評価の順番が分かりにくく、絞り込みの結果を使い回せない |
| 式 | 単純な式だけを書く。絞り込み・集計・条件の組み合わせは、computedにする | 何を表示するかだけを読める |
| 部品のタグ | パスカルケースで書く。中身のない部品は、`/>`で閉じる | HTMLの要素と、Vueの部品を見分けられる |
| ディレクティブ | 省略形（`:`、`@`、`#`）で書く | 書き方がそろう |
| HTMLの埋め込み | `v-html`は使わない | 利用者が入力した値を表示したときに、スクリプトが実行される（XSS） |
| 文言 | メッセージファイルから取り出す（[フロントエンド実装方針.md](フロントエンド実装方針.md)の「7. メッセージの管理」に従う） | 文言を1か所で管理する |

#### 5.7.2. 良い例

```vue
<template>
  <ul>
    <li v-for="node in visibleNodes" :key="node.id">{{ node.name }}</li>
  </ul>
  <p>{{ nodeCount }}件</p>
  <AppFormHelp :text="$t('productCatalog.monthHelp')" />
</template>
```

#### 5.7.3. 悪い例

```vue
<template>
  <ul>
    <!-- 番号を key にし、v-for と v-if を同じ要素に書いている -->
    <li v-for="(node, index) in nodes" v-if="!node.placeholder" :key="index">{{ node.name }}</li>
  </ul>
  <!-- テンプレートで絞り込みと集計をしている -->
  <p>{{ nodes.filter((node) => !node.placeholder).length }}件</p>
  <!-- タグがケバブケース、省略形でない、文言を直接書いている -->
  <app-form-help v-bind:text="'基準年月の説明'"></app-form-help>
  <!-- v-html で表示している -->
  <div v-html="node.name"></div>
</template>
```

**出典**
- 繰り返し、繰り返しと条件：[Vueスタイルガイド「優先度A：必須」](https://ja.vuejs.org/style-guide/rules-essential.html)
- 式、部品のタグ、ディレクティブ：[Vueスタイルガイド「優先度B：強く推奨」](https://ja.vuejs.org/style-guide/rules-strongly-recommended.html)
- HTMLの埋め込み：[Vue「セキュリティ」](https://ja.vuejs.org/guide/best-practices/security.html)

### 5.8. CSS

#### 5.8.1. 書き方

| 項目 | 決まり | 理由 |
| --- | --- | --- |
| 書く場所 | Vueファイル内のスタイルは、`style scoped`に書く | スタイルが、ほかの部品に影響しない |
| セレクター | `style scoped`では、要素セレクターを使わず、クラスセレクターを使う | 要素セレクターは、`scoped`の属性と組み合わさると、表示が遅くなる |
| 固定の見た目 | テンプレートの`style`属性に書かない | 固定の見た目をテンプレートから分け、変更箇所を把握しやすくする |
| 実行時に変わる値 | 部品のパラメーターや実行時の状態に応じた値は、`:style`で指定してよい | クラスでは表せない値を渡せる |
| CSSの書き方 | [CSSコーディング規約](CSSコーディング規約.md)に従う | CSSの決まりを1か所で管理する |

#### 5.8.2. 例

```vue
<template>
  <!-- 固定の見た目はクラスで、計算した高さは :style で指定する -->
  <div class="tree" :style="{ height: `${contentHeight}px` }" />
</template>

<style scoped>
/* ツリー：本文の残りの幅に広げる。 */
.tree {
  flex: 1;
}
</style>
```

## 6. 非推奨の書き方

次の書き方は使わず、代わりの書き方にする。  
決まりの詳細は、参照の列のサブセクションに従う。

| 非推奨の書き方 | 代わりの書き方 | 理由 | 参照 |
| --- | --- | --- | --- |
| Options API（`data`、`methods`などで書く部品） | `script setup`（Composition API） | 関心事ごとにまとめられず、型の推論も弱い | 「5.1. Vueのファイルの構成」 |
| 通常の`script`ブロック | `script setup`と`defineOptions` | 部品ごとの状態を持てない | 「5.1. Vueのファイルの構成」 |
| mixin | composable | どの値がどこから来たかが分からず、名前がぶつかる | 「5.6. composable」 |
| 処理だけを共有するための、表示を持たない部品 | composable | 部品の入れ子が増え、処理が重くなる | 「5.6. composable」 |
| composableの戻り値を`reactive`で包む | `ref`を入れた普通のオブジェクト | 分割代入すると、値の変化が伝わらない | 「5.6. composable」 |
| propsの分割代入による既定値 | `withDefaults` | watchで監視するときに、getterで包み忘れると監視されない | 「5.5. props・イベント・v-modelの宣言」 |
| 受け取ったpropsの書き換え | イベントで親に知らせ、親が変える | 値がどこで変わるかを、親から追えなくなる | [フロントエンド実装方針.md](フロントエンド実装方針.md)の「4.1. ページと部品の役割（Container / Presentational）」 |
| 親や子の部品の、値や状態の直接の操作（`$parent`など） | props・イベント。操作を呼ぶ必要がある場合だけ、`defineExpose`で公開した関数 | 部品の間の値の流れを、宣言から読み取れなくなる | [フロントエンド実装方針.md](フロントエンド実装方針.md)の「4.1. ページと部品の役割（Container / Presentational）」 |
| テンプレートのイベントに、処理の関数を直接渡す | ハンドラーを渡す | ハンドラーとそれ以外の関数が混ざる | 「5.4. ハンドラー」 |
| `v-for`の`key`に、配列の番号を使う | 要素を一意に表す値 | 並びが変わったときに、表示と入力の状態がずれる | 「5.7. テンプレート」 |
| `v-for`と`v-if`を、同じ要素に書く | computedで絞り込んだ配列を、`v-for`に渡す | 評価の順番が分かりにくい | 「5.7. テンプレート」 |
| `v-html` | テキストの埋め込み（`{{ }}`） | 利用者が入力した値で、スクリプトが実行される（XSS） | 「5.7. テンプレート」 |
| テンプレートの`style`属性に、固定の見た目を書く | クラスと`style scoped` | 見た目の変更箇所が、テンプレートに散らばる | 「5.8. CSS」 |
| `style scoped`で、要素セレクター（`label`、`button`など）を使う | クラスセレクター | 要素セレクターは、`scoped`の属性と組み合わさると、表示が遅くなる | 「5.8. CSS」 |

**出典**
- Options API：[Vue「イントロダクション」の「どちらを選ぶか」](https://ja.vuejs.org/guide/introduction.html)
- mixin、表示を持たない部品、composableの戻り値：[Vue「コンポーザブル」](https://ja.vuejs.org/guide/reusability/composables.html)
- propsの書き換え、親や子の部品の直接の操作、`style scoped`の要素セレクター：[Vueスタイルガイド「優先度D：使用注意」](https://ja.vuejs.org/style-guide/rules-use-with-caution.html)
- `v-for`の`key`、`v-for`と`v-if`：[Vueスタイルガイド「優先度A：必須」](https://ja.vuejs.org/style-guide/rules-essential.html)
- `v-html`：[Vue「セキュリティ」](https://ja.vuejs.org/guide/best-practices/security.html)

## 7. コードの検査

この規約の決まりは、対象プロジェクトで設定したESLintの規則で検査する。  
ESLintの実行の決まりは、[Node.jsコーディング規約.md](../../../docs/20_rules/Node.jsコーディング規約.md)の「コードの検査（ESLint）」に従う。

| ESLintの規則 | 検査すること | 指摘の重さ |
| --- | --- | --- |
| `vue/no-mutating-props` | 部品が、受け取ったpropsを書き換えていないか | エラー |
| `vue/require-explicit-emits` | 部品が出すイベントを、宣言しているか | 警告 |
| `vue/block-order` | `script`、`template`、`style`の順番 | 警告 |

> [AI]
> - ESLintを設定した後、規則と指摘の重さは、`nuxt/`で`npx eslint --print-config <ファイル>`を実行して確かめられる。いずれも、Nuxt標準の設定（`@nuxt/eslint`）に含まれる規則である。
