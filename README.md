# public-skills

公開用の AI エージェント向けスキルを管理するリポジトリです。
各スキルの対象環境や利用条件は、リンク先の `SKILL.md` を参照してください。

`gh skill publish` で各スキルを公開します。

## 収録スキル

| スキル | 概要 |
| --- | --- |
| [a5er-editor](skills/a5er-editor/SKILL.md) | A5:SQL Mk-2のER図ファイル（`.a5er`）を解析・編集・新規生成する。テーブル・カラム、PK/FK、インデックス、論理名、リレーションなどを、仕様に沿って安全に更新する。 |
| [ai-development-assessment](skills/ai-development-assessment/SKILL.md) | プロジェクトのAI駆動開発の実践状況を「AI駆動開発 実践力カタログ」評価基準に基づいて確認・採点し、Excelへ出力する。 |
| [bootstrap-ai-harness](skills/bootstrap-ai-harness/SKILL.md) | Nuxt・Vue・Vuetify、Python API、AWS CDK、Playwrightを前提とする新規Webアプリ向けに、AI開発用の資料・指示・スキルの配置と運用を整える。 |
| [data-flow-volume](skills/data-flow-volume/SKILL.md) | 設計資料を基にデータの流れとテーブル別の想定件数、更新頻度、保持期間などを整理し、Excelにまとめる。 |
| [genai-knowledge-comic](skills/genai-knowledge-comic/SKILL.md) | 生成AIの活用・導入・不活用リスクなどを説明する、複数ページのナレッジコミックを作成する。コミックの生成には別途 `baoyu-comic` スキルを使用する。 |
| [generate-screen-design-rules](skills/generate-screen-design-rules/SKILL.md) | プロジェクト向けの画面設計ルールを作成・更新し、デザイン原則や参照資料を基に画面の共通ルールを整理する。 |
| [nablarch-basic-design-excel](skills/nablarch-basic-design-excel/SKILL.md) | Nablarch開発標準のバックエンド基本設計書と単体テスト仕様書のExcelを作成・更新する。 |
| [nablarch-frontend-design-excel](skills/nablarch-frontend-design-excel/SKILL.md) | Nablarch開発標準の画面設計書や単体テスト仕様書のExcelを、SPA向けに読み替えて作成・更新する。 |
| [process-flow-diagram](skills/process-flow-diagram/SKILL.md) | 画面・バックエンド処理・テーブルやファイルの関係を示す処理フロー図を、draw.io形式で作成・更新・確認する。 |
| [prompt-8-plus-1](skills/prompt-8-plus-1/SKILL.md) | 8+1の公式を用いて、再利用可能なプロンプトを設計・改善・レビューする。 |

## skills CLI でのインストール

Node.js と npm が利用できる環境で、インストール先のプロジェクトから実行します。
エージェントやスキルは対話形式で選択できます。

```bash
npx skills add wss-m-nagata/public-skills

# スキルを指定する例
npx skills add wss-m-nagata/public-skills --skill prompt-8-plus-1

# Claude Code または Codex のプロジェクトにインストールする例
npx skills add wss-m-nagata/public-skills --skill prompt-8-plus-1 --agent claude-code
npx skills add wss-m-nagata/public-skills --skill prompt-8-plus-1 --agent codex
```

GitHub 上の公開済み内容がインストールされます。
各スキルの実行環境や外部依存は、インストール後に `SKILL.md` を確認してください。

## gh-skill でのインストール方法

`gh` の [`gh-skill`](https://github.com/github/gh-skill) 拡張を使って、`gh skill install` でインストールします。

```
# 対話式でスキルを選択してインストール
gh skill install wss-m-nagata/public-skills

# スキルを指定してインストール（例: ai-development-assessment）
gh skill install wss-m-nagata/public-skills ai-development-assessment

# バージョンを指定してインストール
gh skill install wss-m-nagata/public-skills ai-development-assessment --pin v1.0.0

# すべてのスキルをまとめてインストール
gh skill install wss-m-nagata/public-skills --all
```

`--agent` でインストール先のエージェント（例: `claude-code`）、`--scope` でインストール範囲（`project` または `user`）を指定できます。

```
gh skill install wss-m-nagata/public-skills ai-development-assessment --agent claude-code --scope project
```

## スキルの更新方法

`gh skill update` でインストール済みのスキルを更新できます。

```bash
# 更新可能なスキルを確認（更新はしない）
gh skill update --dry-run

# 対話式で更新するスキルを確認して更新
gh skill update

# スキルを指定して更新（例: ai-development-assessment）
gh skill update ai-development-assessment

# インストール済みのすべてのスキルを更新（確認なし）
gh skill update --all
```

※ `--pin` でバージョンを固定したスキルは通常の更新対象から除外されます。


## 構成

```
skills/<スキル名>/
├── SKILL.md      # スキル定義（name / description / 手順）
├── scripts/      # 補助スクリプト
├── references/   # 評価基準などの参照データ
└── assets/       # テンプレート等の静的ファイル
```

## 公開方法

```
gh skill publish
```
