---
name: bootstrap-ai-harness
description: Nuxt・Vue・VuetifyのWeb画面、サービス単位のPython API、AWS CDK、Playwrightを前提に、新規WebアプリのAI駆動開発ハーネスを構築する。規約・AI向け指示・設計資料の配置をテンプレートから整え、プロジェクト固有の事項を確認し、画面規約・設計書用のスキルを導入するときに使用する。アプリやインフラの実装コードの生成には使用しない。
license: MIT
---

# WebアプリのAI開発ハーネス構築

ハーネスに詳しくない利用者でも、同じ技術スタックのWebアプリでAI駆動開発を始められるよう、規約・AI向け指示・設計資料の配置と作成手順を整える。
アプリコード、CDKコード、デプロイは作成しない。
CI実装は、運用に必要な自動化（PRのAIレビュー、Issueの自動ラベル付け）のひな形を配置する場合に限る。
これは任意の機能であり、利用者が設定を選んだときだけ行う。
新規Webアプリをリポジトリのルートとし、資料とAI指示がその中で完結するようにする。

## 適用方針

- テンプレートの共通規約・章立て・具体例は引き継ぎ、プロジェクト固有の値と明示された変更点だけを調整する。
- 技術スタックから決まる事項は適用し、標準案がある事項は採否を確認し、環境・接続先・業務要件など推測できない事項は利用者に尋ねる。
- 外部スキルは同梱せず、導入先の`SKILL.md`に従って使う。
  このスキルでは用途・実行時期・渡す前提・成果物の配置を定め、外部スキルの内部手順は重複して定義しない。

## 手順

1. 対象場所、既存の指示とファイル、ユーザーの決定事項を確認する。
   元プロジェクトや作業中のリポジトリを対象と誤認しない。
2. [適用手順](references/design.md)、[必須スキルの導入](references/skills.md)、[固有情報の反映](references/customization.md)を読み、`assets/project-template/`の内容を対象へ適合させる。
   未決定事項や未実装のものを確定済みの事実にしない。
   対象に既存ファイルがある場合は上書きせず、内容を確認して統合する。
3. 対象アプリの目的、サービス、DB管理責任、認証、AWSの識別名と環境を確認し、決定済みの事項を該当する正本へ反映する。
   [入力シート](assets/project-intake.md)を対象プロジェクトの作業用領域にコピーし、確認結果と反映先を記録する。
   大きな未決定事項は確認し、決まっている範囲を先に進める。
4. [必須スキルの導入](references/skills.md)に従い、設計書・図、汎用版、外部のスキルを導入する。
   公開スキルのリポジトリは、設定ファイル`.agents/config/bootstrap-ai-harness/settings.md`を先に確かめ、無ければ尋ねて保存する。
   初期構築時に画面規約を生成し、設計書は仕様・対象が決まった時点で対応スキルを使って作成する。
   サービスの資料は`assets/service-template/`を`backend/<サービス名>/docs/`へ、`assets/service-root-template/`（サービスの`AGENTS.md`・`CLAUDE.md`と、単体テストのレポートを出すスクリプト）を`backend/<サービス名>/`へ、サービスごとに適用する。
   あわせて、[GitHub Actionsの設定](references/github-actions/setup.md)を行うかを尋ね、「設定する」と答えたときだけ、その手順に従う。
   [おすすめの設定](references/recommended-settings/setup.md)（承認なしの許可・確認・禁止、保存時の整形のフック）は、設定ファイル`.agents/config/bootstrap-ai-harness/settings.md`を先に確かめ、「未確認」の項目だけを尋ねる。回答は、設定ファイルに保存し、「しない」も記録して、以後は聞かない。
5. 出力の未置換箇所、相対リンク、規約とAI指示の整合、元プロジェクト固有の値、実在しない実装への参照を確認する。
   画面規約生成スキルが要求する検証を実施し、未決定事項や不足する依存関係を明示する。
   構築結果、反映した決定、未決定事項、検証の実施範囲を報告する。

## 同梱する資料とテンプレート

| ファイル・ディレクトリ | 内容と使う場面 |
| --- | --- |
| [references/design.md](references/design.md) | 対象アプリの構成、テンプレートの配置・適用手順、元資料から引き継ぐ範囲。テンプレートを適用するときに読む。 |
| [references/customization.md](references/customization.md) | プロジェクト固有情報の確認方法と反映先、標準案を変更する場合の調整。利用者の回答を資料に反映するときに読む。 |
| [references/skills.md](references/skills.md) | 導入するスキル（設計書・図、汎用版、外部）の用途、導入コマンド、`.gitignore`の扱い、画面規約と設計書の作成手順。スキルの導入や成果物の作成時に読む。 |
| [references/github-actions/setup.md](references/github-actions/setup.md) | GitHub Actions（PRのAIレビュー、Issueの自動ラベル付け、デプロイ前のテスト）を設定する任意の手順。利用者が「設定する」と答えたときに読む。 |
| [references/recommended-settings/setup.md](references/recommended-settings/setup.md) | Claude Codeのおすすめの設定（承認なしの許可・確認・禁止、保存時の整形のフック）を反映する任意の手順と、回答の保存方法。初回のセットアップで読む。 |
| [assets/project-intake.md](assets/project-intake.md) | 利用者への確認項目と決定・未決定の状態を記録する作業用シート。対象プロジェクトにコピーして使用する。 |
| `assets/project-template/` | Webアプリ全体のAI向け指示、Issueテンプレート、共通規約・仕様・用語集、フロントエンド規約と手順書、AI駆動開発の運用（役割、処理フロー、図）のひな形。対象プロジェクトのルートへ適用する。 |
| `scripts/recommended-settings/` | おすすめの設定を対象へ反映する`apply_recommended_settings.py`。既定は確認だけで、`--apply`で実行する。既存の`settings.json`は、上書きせず、足りないものだけを足す。 |
| `scripts/github-actions/` | GitHub Actionsのひな形を対象へ写す`install_github_actions.py`と、足りないラベルを作る`create_missing_labels.py`。どちらも、既定は確認だけで、`--apply`で実行する。 |
| `assets/optional/recommended-settings/` | 設定の保存先のひな形、許可の規則、整形のフック（Prettier、Black）とその設定、規約に追記する整形の決まりのひな形。`project-template/`とは別に置き、設定を選んだときだけ対象へ写す。 |
| `assets/optional/github-actions/` | GitHub Actionsのワークフロー、ラベル付けのコマンドとスクリプトのひな形。`project-template/`とは別に置き、設定を選んだときだけ対象へ写す。 |
| `assets/service-root-template/` | サービスの直下に置く`AGENTS.md`（このディレクトリについて、技術スタック、テストの実行と報告）、`CLAUDE.md`、単体テストのレポートを出す`tests/unit_report.py`とその部品（`spec_report.py`、`report.css`、`conftest.py`）。`backend/<サービス名>/`へ適用する。 |
| `assets/service-template/` | サービス単位の資料案内、アーキテクチャ、リソース一覧と手順書のひな形。`backend/<サービス名>/docs/`へ適用する。 |
