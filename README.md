# public-skills

公開用の Claude Code スキルを管理するリポジトリです。

`gh skill publish` で各スキルを公開します。

## 収録スキル

| スキル | 概要 |
| --- | --- |
| [ai-development-assessment](skills/ai-development-assessment/SKILL.md) | プロジェクトのAI駆動開発の実践状況を「AI駆動開発 実践力カタログ」評価基準に基づいて確認・採点し、Excelへ出力する。 |
| [nablarch-basic-design-excel](skills/nablarch-basic-design-excel/SKILL.md) | Nablarch開発標準のバックエンド基本設計書Excel（システム機能一覧・システム機能設計書・外部インタフェース一覧/設計書・WebサービスAPI一覧・テーブル一覧/定義書）を、結合セルや書式を壊さずに作成・更新する。 |

## インストール方法

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
