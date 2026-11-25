---
name: bootstrap-ai-harness
description: Nuxt・Vue・VuetifyのWeb画面、サービス単位のPython API、AWS CDK、Playwrightを前提に、新規WebアプリのAI駆動開発ハーネスを構築する。利用者が記入した入力シート（Excel）を読み、規約・AI向け指示・設計資料の配置をテンプレートから整え、画面規約・設計書用のスキルを導入する。入力シートの項目の意味を聞かれたとき、資料から入力シートの下書きを作るとき、入力シートの記入漏れを確かめるときにも使用する。アプリやインフラの実装コードの生成には使用しない。Keywords：AI coding harness, project setup, AGENTS.md, CLAUDE.md, coding standards.
license: MIT
---

# WebアプリのAI開発ハーネス構築

ハーネスに詳しくない利用者でも、同じ技術スタックのWebアプリでAI駆動開発を始められるよう、規約・AI向け指示・設計資料の配置と作成手順を整える。
利用者は入力シート（Excel）に記入し、AIは入力シートを読んで構築する。
アプリコード、CDKコード、デプロイは作成しない。
CI実装は、運用に必要な自動化（PRのAIレビュー、Issueの自動ラベル付け）のひな形を配置する場合に限る。
これは任意の機能であり、入力シートで「する」と記入されたときだけ行う。
新規Webアプリをリポジトリのルートとし、資料とAI指示がその中で完結するようにする。

## 適用方針

- 入力の正本は入力シートである。
  プロジェクト固有の事項は入力シートから読み、利用者に質問しない。
  入力シートに無い事項で、判断が要るものだけを確認する。
- テンプレートの共通規約・章立て・具体例は引き継ぎ、入力シートの値と既定値に合わせて、プロジェクト固有の部分だけを調整する。
- 入力シートで「未定」「不明」とされた項目は、推測で埋めず、[記入要領](references/intake-guide.md)の扱いに従い、未決定事項として報告する。
- 外部スキルは同梱せず、導入先の`SKILL.md`に従って使う。
  このスキルでは用途・実行時期・渡す前提・成果物の配置を定め、外部スキルの内部手順は重複して定義しない。

## 使い方の判定

利用者の依頼から、次のどれかを判定し、該当する手順に従う。

| 使い方 | 依頼の例 | 手順 |
| --- | --- | --- |
| 項目の意味を聞く | 「この項目には何を書けばよいか」 | [項目の意味を答える](#項目の意味を答える) |
| 資料から下書きを作る | 「要件定義書から入力シートを埋めて」 | [下書きを作る](#下書きを作る) |
| 記入漏れを確かめる | 「入力シートの記入漏れを確かめて」 | [記入漏れを確かめる](#記入漏れを確かめる) |
| 環境を作る | 「入力シートの内容で環境を作って」 | [環境を作る](#環境を作る) |

入力シートのパスが分からないときは、利用者に尋ねる。
入力シートがまだ無いときは、ひな形（`assets/project-intake/プロジェクト入力シート.xlsx`）を、利用者が指定する場所にコピーして渡す。

## 項目の意味を答える

1. [記入要領](references/intake-guide.md)で、聞かれた項目の説明、補足、選択肢、既定値、反映先を読む。
2. 項目の意味と、答えによって何が変わるかを答える。
   利用者のプロジェクトの事情が分かれば、どれを選ぶかの考え方を示す。
   値を決めるのは利用者であり、AIは入力シートに書き込まない。

## 下書きを作る

1. `read_intake.py` で入力シートを読み、インプット資料シートの行（`lists.inputs`）を取る。
2. インプット資料を読む。
   「見てほしいシート・ページ」が書かれていれば、そこを先に読む。
   ファイルサーバーの資料が読めないときは、読めなかった資料を報告する。
3. 資料に根拠がある値だけを、下書きの値のJSONにする（形は`write_intake.py`の説明に従う）。
   根拠の無い値を推測で書かない。
   既定値でよい任意の項目と、記入済みの項目は、書かない。
4. `write_intake.py`で、入力シートのコピーに下書きを書く。
   出力先は利用者に確かめる。
   指定が無ければ、元の入力シートと同じフォルダに、名前の末尾に「_下書き」を付けて作る。
   元の入力シートは変更しない。
5. 次を報告する。
   - 下書きの出力先。
   - 書いた項目と、その根拠（資料名とシート・ページ）。
   - 資料から決められなかった必須の項目と、誰に何を確かめればよいか。

## 記入漏れを確かめる

1. `read_intake.py --missing`で、空欄の必須の項目と、条件に当てはまる条件付き必須の項目を取る。
2. `read_intake.py`の出力で、項目どうしの食い違いを確かめる。
   例：業務の塊（サービス）とサービス略称の数が合わない、GitHub Actionsを入れないのに使う機能が書かれている、画面とメニューのメニューが業務の塊と対応しない。
3. 結果だけを報告する。
   入力シートは変更しない。

## 環境を作る

1. 対象場所、既存の指示とファイルを確認する。
   元プロジェクトや作業中のリポジトリを対象と誤認しない。
2. 入力シートを読む。
   1. `read_intake.py --missing`を実行する。
      空欄が1件でもあれば、環境は作らず、空欄の一覧（シート、項目、理由）を利用者に返して止める。
      利用者が入力シートに記入してから、やり直す。
   2. 空欄が無ければ、`read_intake.py`の出力（項目ごとの値と状態、一覧シートの行）を、以降の手順の入力にする。
      以降、入力シートにある項目を質問しない。
   3. [反映の記録](assets/project-intake.md)を、対象プロジェクトの`.agents/state/bootstrap-ai-harness/project-intake.md`にコピーし、入力シートのパスを書く。
3. [適用手順](references/design.md)、[必須スキルの導入](references/skills.md)、[固有情報の反映](references/customization.md)、[記入要領](references/intake-guide.md)を読み、`assets/project-template/`の内容を対象へ適合させる。
   項目ごとの反映先は、記入要領の「反映先」に従う。
   未決定事項や未実装のものを確定済みの事実にしない。
   対象に既存ファイルがある場合は上書きせず、内容を確認して統合する。
   [インフラ設計の適用](references/infra-design.md)に従い、APIの公開方式に対応するAWSインフラ設計書を配置し、規約とデプロイ手順をそろえる。
   反映した項目と反映先、未決定の項目を、反映の記録に書く。
4. [必須スキルの導入](references/skills.md)に従い、設計書・図、汎用版、外部のスキルを導入する。
   公開スキルのリポジトリは、入力シートの「公開スキルのリポジトリ」を使う。
   初期構築時に画面規約を生成し、設計書は仕様・対象が決まった時点で対応スキルを使って作成する。
   サービスの資料は`assets/service-template/`を`backend/<サービス名>/docs/`へ、`assets/service-root-template/`（サービスの`AGENTS.md`・`CLAUDE.md`と、単体テストのレポートを出すスクリプト）を`backend/<サービス名>/`へ、入力シートの業務の塊（サービス）ごとに適用する。
   [GitHub Actionsの設定](references/github-actions/setup.md)と[おすすめの設定](references/recommended-settings/setup.md)は、入力シートの「ハーネスの設定」シートの値に従う。
   値は`.agents/config/bootstrap-ai-harness/settings.md`に保存する。
5. 出力の未置換箇所、相対リンク、規約とAI指示の整合、元プロジェクト固有の値、実在しない実装への参照を確認する。
   画面規約生成スキルが要求する検証を実施し、未決定事項や不足する依存関係を明示する。
   構築結果、反映した値、未決定事項、利用者の確認待ち（画面規約のモックなど）、検証の実施範囲を報告する。

## 入力シートのスクリプト

スクリプトはスキルのディレクトリの`scripts/project-intake/`にある。
`openpyxl`が要る。

| スクリプト | 使い方 |
| --- | --- |
| `read_intake.py <入力シート>` | 項目ごとの値・既定値を当てた値・状態と、一覧シートの行をJSONで出す。`--missing`で空欄の必須の項目だけを出す（あれば終了コード1）。`--sheet`、`--id`で絞る。入力シートは変更しない |
| `write_intake.py <元の入力シート> <出力先> --values <JSON>` | 入力シートのコピーを作り、記入欄に下書きの値を書く。記入済みの欄は上書きしない |
| `build_intake.py` | `assets/project-intake/items.toml`から、入力シートのひな形と記入要領を作り直す。項目を変えたときに使う |
| `make_service_figure.py` | アプリ構成シートの図を描き直す。Pillowと日本語のフォントが要る |

入力シートの項目を変えるときは、`items.toml`を直し、`build_intake.py`を実行する。
入力シートのひな形と記入要領を、手で直さない。

## 同梱する資料とテンプレート

| ファイル・ディレクトリ | 内容と使う場面 |
| --- | --- |
| [references/intake-guide.md](references/intake-guide.md) | 入力シートの記入要領。項目ごとの意味、選択肢、既定値、未定・不明のときの扱い、反映先。どの使い方でも読む。`items.toml`から作る |
| [references/design.md](references/design.md) | 対象アプリの構成、テンプレートの配置・適用手順、元資料から引き継ぐ範囲。テンプレートを適用するときに読む。 |
| [references/customization.md](references/customization.md) | 入力シートの値の反映方法と、標準案と異なる値の場合の調整。入力シートの値を資料に反映するときに読む。 |
| [references/infra-design.md](references/infra-design.md) と `assets/infra-design/` | APIの公開方式に対応するAWSインフラ設計書と適用手順。 |
| [references/skills.md](references/skills.md) | 導入するスキル（設計書・図、汎用版、外部）の用途、導入コマンド、`.gitignore`の扱い、画面規約と設計書の作成手順。スキルの導入や成果物の作成時に読む。 |
| [references/github-actions/setup.md](references/github-actions/setup.md) | GitHub Actions（PRのAIレビュー、Issueの自動ラベル付け、デプロイ前のテスト）を設定する任意の手順。入力シートで「する」と記入されたときに読む。 |
| [references/recommended-settings/setup.md](references/recommended-settings/setup.md) | Claude Codeのおすすめの設定（承認なしの許可・確認・禁止、保存時の整形のフック）を反映する任意の手順と、設定の保存方法。環境を作るときに読む。 |
| `assets/project-intake/` | 入力シートのひな形（`プロジェクト入力シート.xlsx`）、項目の正本（`items.toml`）、アプリ構成シートの図。ひな形は、利用者に渡して記入してもらう |
| [assets/project-intake.md](assets/project-intake.md) | 入力シートの値をどこに反映したかと、未決定の項目を記録する作業用のひな形。対象プロジェクトにコピーして使用する。 |
| `assets/project-template/` | Webアプリ全体のAI向け指示、Issueテンプレート、共通規約・仕様・用語集、フロントエンド規約と手順書、AI駆動開発の運用（役割、処理フロー、図）のひな形。対象プロジェクトのルートへ適用する。 |
| `scripts/project-intake/` | 入力シートを読む・下書きを書く・ひな形を作るスクリプト。使い方は「入力シートのスクリプト」に書いた。 |
| `scripts/recommended-settings/` | おすすめの設定を対象へ反映する`apply_recommended_settings.py`。既定は確認だけで、`--apply`で実行する。既存の`settings.json`は、上書きせず、足りないものだけを足す。 |
| `scripts/github-actions/` | GitHub Actionsのひな形を対象へ写す`install_github_actions.py`と、足りないラベルを作る`create_missing_labels.py`。どちらも、既定は確認だけで、`--apply`で実行する。 |
| `assets/optional/recommended-settings/` | 設定の保存先のひな形、許可の規則、整形のフック（Prettier、Black）とその設定、規約に追記する整形の決まりのひな形。`project-template/`とは別に置き、設定を選んだときだけ対象へ写す。 |
| `assets/optional/github-actions/` | GitHub Actionsのワークフロー、ラベル付けのコマンドとスクリプトのひな形。`project-template/`とは別に置き、設定を選んだときだけ対象へ写す。 |
| `assets/service-root-template/` | サービスの直下に置く`AGENTS.md`（このディレクトリについて、技術スタック、テストの実行と報告）、`CLAUDE.md`、単体テストのレポートを出す`tests/unit_report.py`とその部品（`spec_report.py`、`report.css`、`conftest.py`）。`backend/<サービス名>/`へ適用する。 |
| `assets/service-template/` | サービス単位の資料案内、アーキテクチャ、リソース一覧と手順書のひな形。`backend/<サービス名>/docs/`へ適用する。 |
