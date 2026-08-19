# public-skills

公開用の Claude Code スキルを管理するリポジトリです。

`gh skill publish` で各スキルを公開します。

## 収録スキル

| スキル | 概要 |
| --- | --- |
| [ai-development-assessment](skills/ai-development-assessment/SKILL.md) | プロジェクトのAI駆動開発の実践状況を「AI駆動開発 実践力カタログ」評価基準に基づいて確認・採点し、Excelへ出力する。 |

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
