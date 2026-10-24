---
compatibility: '`design-standards` Skillがインストールされていると、DADS / Carbonのいずれにも定義がない項目の補完に利用できる（任意、必須ではない。無い場合はその旨をユーザーへ確認する運用にフォールバックする）。 規約の出力先（既定は `docs/rules/screen-design-rules/`）への読み書き権限が必要。初回生成時は `${CLAUDE_SKILL_DIR}/assets/screen-design-rules-template/` からのファイルコピーを行う。'
description: |
    プロジェクトの画面設計規約を作成・更新する。 Markdownテンプレートをもとに、 DADSを主、IBM Carbon Design Systemを補完として具体的な規約を埋め、 プロジェクト固有の判断が必要な項目をユーザーに確認して確定する。
    画面設計の基本原則（設計原則）についての問い合わせにも、同梱の参照資料で答える。
license: MIT
metadata:
    github-path: skills/generate-screen-design-rules
    github-ref: refs/tags/v1.0.11
    github-repo: https://github.com/wss-m-nagata/public-skills
    github-tree-sha: e3450b7931f3b6c4daddbd74b38156871cf80df9
name: generate-screen-design-rules
---
# Generate Screen Design Rules

## 目的

出力先（下の「前提」を参照）に、画面生成時に単独で参照できるプロジェクト固有の画面設計規約を作成・更新する。

このSkillは、規約テンプレートを自由に作り替えるのではなく、既存のMarkdownテンプレートを埋めて具体化する。

`${CLAUDE_SKILL_DIR}` は、このSKILL.mdが置かれているディレクトリ（`.claude/skills/generate-screen-design-rules/`）を指す。以下のパスは特に断りがない限りここからの相対パスであり、プロジェクト側のパスをSkill内に持たない。

## 前提

- 画面規約の保存先（以下「出力先」）の既定は `docs/rules/screen-design-rules/`。プロジェクトに資料の置き場所の決まりがある場合は、手順0で確認した場所を出力先にする
- 規約はユーザーが直接読んで修正できるMarkdownで管理する
- 規約テンプレートには `確定` / `暫定` / `要確認` の状態がある
- DADSを主たる規約とする
- DADSで不足する業務アプリ向けの内容のみCarbonで補完する
- DADS / Carbonでも判断できない場合のみ `design-standards` Skillを補完的に利用する
- 最終規約には具体値・具体ルールを書き、画面生成時に外部サイトを都度検索しなくてよい状態にする

## 規約の優先順位

1. 既に確定しているプロジェクト固有規約
2. デジタル庁デザインシステム（DADS）
3. DADSで不足する部分のみ IBM Carbon Design System
4. 上記に定義がない場合のみ `design-standards` Skill
5. それでも判断できない場合はユーザーへ確認する

既に `確定` しているプロジェクト固有規約を、外部デザインシステムの内容で自動上書きしてはならない。

## 参照元の使い方

### 情報源の一覧（何ができて、何ができないか）

| 情報源 | 主に確認できること | できないこと・限界 |
|---|---|---|
| `${CLAUDE_SKILL_DIR}/references/dads/`<br>（DADS公式Markdownの抜粋） | 余白・色の分類・タイポグラフィ・角の形状・エレベーション・レイアウト・アクセシビリティ方針、主要コンポーネント21種の説明 | 色の実HEX値は載っていない（下の`design-tokens`を使う）。テンプレートの`ローカル参照`が指していない項目はカバー対象外 |
| `${CLAUDE_SKILL_DIR}/references/dads/quick-values.md`<br>`${CLAUDE_SKILL_DIR}/references/dads/quick-values-tokens.md`<br>（値の早見表） | 文字・角の形状・ボタン・入力欄・レイアウトなどの値（`quick-values.md`。原文から確かめた値で、出典を併記している）と、色・文字・角丸・影のトークンの解決後の値（`quick-values-tokens.md`。トークンから生成） | 早見表は索引であり、**元の資料が正**。値が必要なときは、まず早見表を見て、迷ったら原文を読む |
| `${CLAUDE_SKILL_DIR}/references/dads/not-defined-and-stances.md`<br>（DADSに値がない項目と、DADSの方針） | DADSが値を定めていない項目の一覧と、DADSの方針が部品ライブラリの標準と食い違いやすい項目の一覧 | 決めた値と理由を残す場所は、出力先の `sources.md` の「プロジェクト独自ルール」 |
| `${CLAUDE_SKILL_DIR}/scripts/contrast.py` | 色の組み合わせのコントラスト比（テキスト4.5:1、テキスト以外3:1の判定つき） | — |
| `${CLAUDE_SKILL_DIR}/scripts/gen_quick_values.py` | `tokens.json` から `quick-values-tokens.md` を生成する（`tokens.json` を再取得したときに再実行する） | — |
| `${CLAUDE_SKILL_DIR}/references/dads/design-tokens/tokens.json`<br>（DADS Design Token） | 色・タイポグラフィ・サイズの実HEX値／実数値。`Semantic`や`Key`は`Primitive`へのエイリアスとして辿れば解決できる | どの色相をプロジェクトのPrimaryにするか等、ブランド固有の判断はできない（後述「色のHEX値」参照） |
| `${CLAUDE_SKILL_DIR}/references/carbon/`<br>（Carbon公式ソースの抜粋） | Header／Side Navigation／Right Panelの構造・数値、Modal・Tabs・Data Tableの使い分け基準 | 色・Typography・Button等の見た目をDADSより優先して採用してはならない |
| DADS公式サイト https://design.digital.go.jp/dads/ | ローカル参照に該当が無い項目、最新版の確認 | 大きいページはAI要約で情報が欠落・途中で切れることがある |
| Carbon公式サイト https://carbondesignsystem.com/ | 同上 | 同上 |
| `design-standards` Skill<br>（`Skill(skill: "design-standards", args: "<観点>")`で呼び出す） | DADS／Carbon／確定済みプロジェクト規約のいずれにも定義が無い、一般的な見た目・配置・余白・階層等の判断 | DADS／Carbon／確定済みプロジェクト規約より優先してはならない（あくまで補完） |

### 参照する順序

1. テンプレートの項目に `ローカル参照` が書かれていれば、そのファイルを直接読む（最優先・最速）。複数ファイルが列挙されている場合は必要な範囲だけ読めばよい。
2. `ローカル参照` が無い、または「専用ファイルなし」の場合は、`references/dads/README.md` / `references/carbon/README.md` の対応表を確認する。
3. それでも該当ファイルが無い場合、または内容の鮮度・正確性を再確認したい場合は、`参照ヒント`を使って公式サイトを直接調査する。単に「DADS/Carbonを参照」として広範囲を探索しない。
4. どの手段で得た内容も、原文の言い回しを尊重し、規約側で要約・言い換えする場合も元の意味を変えない。
5. 用途とトークン・値の対応づけ自体がDADS/Carbonの範囲では決まらない場合（例: プロジェクト独自のブランドカラーをどの色相にするか）のみ、無理に決めず `要確認` として理由とともに残す。値自体は辿れば解決できるのに、確認を理由に `要確認` のまま空欄にしない。

### 色のHEX値を具体化する手順

DADSの色ページ（公式サイト・ローカル参照とも同じ内容）には、分類（キー／共通／機能／セマンティックカラー）とコントラスト比の要件はあるが、実HEX値は載っていない。実HEX値は`design-tokens/tokens.json`から解決する。

1. `foundations/color/index.md` で、用途（Primary/Secondary/Tertiary/Background/Text/Border/Error/Warning等）ごとのコントラスト比要件（テキスト4.5:1以上、非テキスト3:1以上 等）を確認する。
   値は `references/dads/quick-values-tokens.md`（解決後のHEX値の一覧）で確認できる。選んだ色の組み合わせは `scripts/contrast.py` で確かめる。
2. Error / Warning / Success 等のセマンティックカラーは、`tokens.json` の `Color.Semantic.*` を解決し、そのまま暫定値として採用する（ブランドに依存しないDADS固有の値のため）。
3. Primary / Secondary / Tertiary / Background / Text / Border は、`Color.Key.*`（既定色相）と `Color.Neutral.*`（グレースケール）から、手順1の要件を満たす段階を選び暫定値にする。`Color.Key.*` の既定色相（同梱データはBlue）はDADS参考実装の例であり、プロジェクトのブランドカラーに応じて色相だけを差し替えてよい。差し替える場合も同じ選定ロジック（コントラスト比を満たす段階を選ぶ）を使う。
4. 色相の選定やWarningの色系統（Yellow / Orange）選択など、DADSだけでは一意に決まらない部分だけを `確認事項` としてユーザーに聞く。

### 参照ヒントが記載されていない項目

テンプレートに `参照ヒント` が無い項目を暫定化・確定する場合は、出典（DADS / Carbon）のページ構成全体から該当箇所を特定し、内容を確定したうえで、その参照ヒント（ページ名・章・検索キーワード）をテンプレートへ追記する。次回以降の規約更新で同じ探索を繰り返さないようにする。

継続的に参照する項目だと分かった場合は、該当する原文ファイルを `references/dads/` または `references/carbon/` へ未編集のまま追加し、それぞれの `README.md` の対応表に追記することを検討する（必須ではない、テンプレートの参照ヒント追記とは別の改善作業）。

### ローカルリファレンスの更新について

`references/` 配下は取得時点のスナップショットであり、自動更新は行わない。DADS/Carbonが更新されたことが分かっている場合や値に疑義がある場合のみ、公式サイト（DADSは https://design.digital.go.jp/dads/resources/ のMarkdownアーカイブ、Carbonは https://github.com/carbon-design-system/carbon-website 、design-tokensは https://github.com/digital-go-jp/design-tokens ）から該当ファイルを再取得し、対応する`README.md`の取得日を更新する。毎回の規約生成でリファレンス全体を再取得する必要はない。

## 実行手順

### 0. 出力先と前提を確認し、初回生成ならひな形をコピーする

**初回生成の場合は、コピーの前に、次の2点をユーザーに確認する**（既存の規約を更新する場合は、手順1へ進む）。

1. **出力先**: プロジェクトの資料の置き場所の決まり（ディレクトリの分け方、番号の付け方など）と、資料の書き方の決まり（規約に未決定の事項を書いてよいか、など）を確認し、出力先を決める。決まりがない場合は、既定の `docs/rules/screen-design-rules/` を使う。
   - 規約に未決定の事項を書いてはいけない決まりがある場合は、「暫定」「要確認」の状態を、規約の本文ではなく `デザインシステム確認事項.md` に集める運用に変える。
2. **使う部品ライブラリ**: 画面の部品のライブラリ（例: UIフレームワークの部品集）の有無と名前を確認し、`components.md` の「部品ライブラリとの対応」の表に反映する。

出力先がまだ存在しない場合は、`${CLAUDE_SKILL_DIR}/assets/screen-design-rules-template/` の内容をそのままコピーして初期状態を作る。

既に出力先が存在する場合は、コピーはせず、手順1（現在の規約を確認する）から進める。

### 1. 現在の規約を確認する

出力先を読み、以下を確認する。

- `確定`
- `暫定`
- `要確認`
- ユーザーが手動で変更した内容
- `参考例`
- `必須実装`

既にユーザーが確定・変更しているルールは保持する。

### 2. 暫定項目を具体化する

`暫定` の項目について、出典と参照ヒントを使って原典を確認する。

次のような抽象表現を最終規約に残さない。

NG:

- 「DADSの角の形状を採用する」
- 「CarbonのHeaderに準拠する」
- 「DADSを参照する」

具体的な値・条件・使い分けを原典から取り込み、プロジェクト規約として読める形にする。

- 値は、まず `references/dads/quick-values.md` と `references/dads/quick-values-tokens.md` で探す。
- 値が見つからない項目は、`references/dads/not-defined-and-stances.md` の「値が定められていない項目」に当たるかを確認する。当たる場合は、プロジェクトの値を決めて規約に書き、**決めた理由**を出力先の `sources.md` の「プロジェクト独自ルール」の表に書く。
- DADSの方針と部品ライブラリの標準が食い違う項目（同ファイルの「DADSの方針」）は、採用する・しないを決めて、規約と「プロジェクト独自ルール」の表に書く。

### 3. 出典情報を残す

外部規約から取り込んだ項目には、少なくとも以下を残す。

- 出典: DADS / Carbon
- 参照ヒント: ページ名、章・見出し、検索キーワード
- 必要に応じて参照URL
- 何を取り込んだか

参照ヒントは画面生成時に使うためではなく、規約の生成・更新時に原典へ素早く戻るために使う。

### 4. ユーザー判断が必要な項目を抽出する

以下は勝手に確定せず、ユーザーへ確認する。

- ブランドカラー
- 対応端末と、想定する画面の幅（PCの場合）
- Header / Side Navigationを利用するか
- Side Navigationを既定で開くか閉じるか、開くときの表示方式（本文を押し出す／重ねる）
- Header高さやSide Navigation幅を暫定値から変更するか
- Standard / Denseの選択
- ボタン配置
- Dialog / Side Panel / 別画面の使い分けに関するプロジェクト固有条件
- DADS / Carbonに定義がなく、プロジェクト要件で決める必要がある内容

質問は、何を決める質問なのかと、現在の暫定案を明示する。

### 5. 回答を反映する

ユーザーの回答をMarkdownへ反映する。

- 採用した場合: `確定` に変更
- 変更した場合: 値と判断理由を反映して `確定`
- 未回答の場合: `要確認` または `暫定` のまま保持

ユーザーの回答から推測して別項目まで確定しない。

### 6. 規約内の例を更新する

規約内容を理解しやすくするため、必要な場合は以下を更新する。

- OK例 / NG例
- HTML参考レイアウト
- 画像
- ソースコードの参考例
- 必須実装

`参考例` と `必須実装` を混同しない。

### 7. 完了確認

作業後、以下を確認する。

- 「DADSを参照」等だけで終わる抽象的な規約が残っていないか
- プロジェクト固有規約と外部規約が衝突していないか
- DADSとCarbonの両方に規約がある場合、DADSを優先しているか
- 画面生成時に外部検索しなくても実装判断できる程度に具体化されているか
- 色の「文字 × 背景」の組み合わせを、`scripts/contrast.py` で確かめたか（テキスト4.5:1、テキスト以外3:1。背景に別の色（区別する領域など）がある場合は、その上の文字色も確かめる）
- DADSに値がない項目と、DADSの方針から外れた項目に、決めた理由が `sources.md` の「プロジェクト独自ルール」に書かれているか

### 8. `デザインシステム確認事項.md` を更新する

出力先の全Markdownファイル（`デザインシステム確認事項.md` 自身と `README.md` を除く）を走査し、`- **状態:** 暫定` および `- **状態:** 要確認`（`確定（〜）／値は暫定` のような複合表記を含む）の項目を洗い出す。

`デザインシステム確認事項.md` の一覧を、以下の形式で書き直す。

- `要確認` の項目を先に、`暫定` の項目を後に並べる（`要確認` はまだ値そのものが無く優先度が高いため）
- 各行に、ファイル名・見出し（項目名）・現在の状態・確認してほしい内容（暫定値がある場合はその値、無ければ何を決める必要があるか）を記載する
- 手作業では追記・削除せず、走査結果でこのセクションを丸ごと置き換える
- 該当項目が0件になった場合は、一覧を空にし「現在、確認が必要な項目はありません。」と記載する
- 「最終更新」の日付をこの更新日に合わせる

この一覧は、プロジェクト担当者が全ファイルを開かなくても、`デザインシステム確認事項.md`だけで残作業を把握できるようにするためのものである。

## テンプレートを変更する場合

テンプレートの構造を独自判断で大きく変更しない。

テンプレート自体に不足がある場合は、規約値を埋める作業とは分けて、改善案としてユーザーへ提示する。

## 設計原則の問い合わせ

画面設計の基本原則について質問されたときは、上の実行手順とは別に、`${CLAUDE_SKILL_DIR}/references/design-principles/README.md` を見て答える。
原則を導入したいと言われたときは、同ディレクトリの `operations/導入手順.md` に従う。

## スコープ外

このSkillでは以下を行わない。

- 画面設計書から実際の画面コードを生成する
- Visual Regression
- 生成後のUI検査
- Playwrightによる検査
- ESLint等の一般的なコード品質検査
- フロントエンド実装規約の詳細設計

画面コード生成は別Skill `generate-screen-from-design` の責務とする。

## 参照

このSkillが参照している情報源。

- デジタル庁デザインシステム（DADS）公式サイト: https://design.digital.go.jp/dads/
  - 公式Markdownアーカイブ配布元: https://design.digital.go.jp/dads/resources/
  - 利用上の注意事項（出典明記等）: https://design.digital.go.jp/dads/introduction/notices/
  - Design Token（実HEX値を含む）: https://github.com/digital-go-jp/design-tokens
- IBM Carbon Design System 公式サイト: https://carbondesignsystem.com/
  - 公式サイトソースリポジトリ（Apache-2.0）: https://github.com/carbon-design-system/carbon-website
- ローカルリファレンス（DADS/Carbon公式原文の未編集抜粋、取得日・出典・対応表つき）
  - `${CLAUDE_SKILL_DIR}/references/dads/README.md`（取得情報は同ディレクトリの`VERSION.txt`）
  - `${CLAUDE_SKILL_DIR}/references/carbon/README.md`（取得情報は同ディレクトリの`VERSION.txt`）
- Skillが作成した早見表・一覧（原文ではなく、**原文が正**）
  - `${CLAUDE_SKILL_DIR}/references/dads/quick-values.md`（原文から確かめた値）
  - `${CLAUDE_SKILL_DIR}/references/dads/quick-values-tokens.md`（`tokens.json`から生成）
  - `${CLAUDE_SKILL_DIR}/references/dads/not-defined-and-stances.md`（DADSに値がない項目と、DADSの方針）
- 画面設計の基本原則（問い合わせ対応用）: `${CLAUDE_SKILL_DIR}/references/design-principles/README.md`
- スクリプト: `${CLAUDE_SKILL_DIR}/scripts/contrast.py`、`${CLAUDE_SKILL_DIR}/scripts/gen_quick_values.py`
- 規約ひな形: `${CLAUDE_SKILL_DIR}/assets/screen-design-rules-template/`
- 補完的に利用するSkill: `design-standards`（DADS / Carbon / プロジェクト固有規約のいずれにも定義がない場合のみ）
