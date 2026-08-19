---
name: ai-development-assessment
description: プロジェクトにおけるAI駆動開発の実践状況を、「AI駆動開発 実践力カタログ」評価基準に基づいて確認・採点し、Excelへ出力する。確認済みの項目は state ファイルに保存し、次回評価時は原則再確認しない。「AI駆動開発の実践度を診断して」「実践力カタログで評価して」「前回の続きから評価して」等で使う。
disable-model-invocation: false
license: MIT
allowed-tools: Read Grep Glob Write Bash(./skills/ai-development-assessment/scripts/*)
---

# AI駆動開発 実践力診断

## これは何をするスキルか

プロジェクトにおけるAI駆動開発の実践状況を、`references/criteria.json` の評価基準（0/25/50/75/100点の5段階、全20項目）に基づいて確認し、点数化した上で、既存の「AI駆動開発 実践力カタログ」Excelへ出力する。

確認済みの項目はGit管理されたstateとして保存され、次回評価時は原則としてスキップする。同じ質問を評価のたびに繰り返さないための仕組みである。

## 役割分担の原則

- **AIが担当するもの**：確認結果の意味判断、リポジトリ調査、ユーザーへの質問、「推奨対応」文章の作成。
- **スクリプトが担当するもの**：JSONの生成・更新、点数計算、整合性チェック、Excel出力。点数判定やExcel転記をAIが目測で行ってはならない。必ず `scripts/` 配下のスクリプト経由で行う。
- **`check-results.json` を直接編集しない。** 更新は必ず `update_check_result.py` 経由で行う。

## 評価処理の全体フロー

1. `python scripts/get_assessment_state.py` で現在の評価状態を取得する。
2. 返された `items[].checks[]` のうち `status` が `unconfirmed` または `needs_recheck` の項目を、次回の確認対象として特定する（`confirmed` と `not_applicable` は原則スキップ）。
3. 確認対象のうち、リポジトリ内のコード・ドキュメント・設定ファイル等の調査で判断できるものは、AI自身が調査して判断する。ユーザーへ質問する前に、まずこの調査を行うこと。
4. リポジトリだけでは判断できない項目（運用実態、チームの利用状況など）のみ、ユーザーへ質問する。
5. 判断できた項目ごとに `python scripts/update_check_result.py --check-id <id> --status <status> --result <true|false> --evidence <証跡> --notes <所見>` を実行し、結果を保存する。
6. 全て確認し終えたら `python scripts/validate_assessment.py` で整合性を検証する。エラーがあれば内容に応じて修正する。
7. `python scripts/calculate_score.py` で各評価項目の点数を算出する（`update_check_result.py` を呼ぶたびに保存はされるが、最終結果の確認用に明示的に呼んでもよい）。
8. 「推奨対応」（現在の到達段階から次の段階へ進むための具体的な対応案）をAIが評価項目ごとに作成し、`{criteria_id: 推奨対応の文章}` 形式のJSONファイルとして `.agents/state/ai-development-assessment/narratives.tmp.json` に保存する。
9. `python scripts/export_assessment.py --output .agents/state/ai-development-assessment/exports/AI駆動開発_実践力カタログ_評価結果.xlsx --narratives-file .agents/state/ai-development-assessment/narratives.tmp.json --force` でExcelへ出力する。2回目以降は同じファイルへ上書きするため `--force` を付ける。テンプレート自体（`assets/AI駆動開発_実践力カタログ.xlsx`）は変更されない。

## `criteria.json` の参照方法

`references/criteria.json` に評価基準の正本がある。各評価項目（`criteria`）は `id` / `phase` / `name` / `levels`（0・25・50・75・100点それぞれの到達状態を表す `state` 文言）を持つ。

`criteria_version` フィールドを持ち、`check-results.json` 側の `criteria_version` と一致している必要がある（`validate_assessment.py` が検証する）。評価基準を改訂した場合は、両方のバージョンを合わせて更新すること。

## `check-results.json` の扱い

このファイルは `get_assessment_state.py` で読み取り、`update_check_result.py` で更新する。**直接編集はしない。** JSONの構造を壊さず、確認済み項目の履歴を正しく残すためである。

Git管理されておりチームで共有されるため、他メンバーが次回評価しても `confirmed` の項目は再確認されない。

各評価項目（`items[]`）は4つの到達条件（`checks[]`、`score_threshold` = 25/50/75/100）を持つ。`status` は以下の4値で、AIが確認結果に応じてどれを設定するか判断する。

- `unconfirmed`：未確認。確認対象。
- `confirmed`：確認済み。次回以降は原則スキップ。
- `needs_recheck`：再確認対象（評価基準の改訂時など）。
- `not_applicable`：対象プロジェクトに適用しない。採点対象外。

ある評価項目の4つの到達条件が**すべて** `not_applicable` の場合のみ、その評価項目全体を採点対象外として扱う（一部だけ `not_applicable` にしても採点対象外にはならない）。

## このSkillが生成するファイルのパス

以下2つは `check-results.json` とは異なり、`check-results.json` さえあればいつでも再生成できるためGit管理しない（`.gitignore` で除外済み）。パスは固定なので、実行のたびにAIが場所を考える必要はない。

| ファイル | パス | 性質 |
|---|---|---|
| 推奨対応の一時JSON | `.agents/state/ai-development-assessment/narratives.tmp.json` | 使い捨て。export実行のたびに上書きしてよい。 |
| Excel出力(最終成果物) | `.agents/state/ai-development-assessment/exports/AI駆動開発_実践力カタログ_評価結果.xlsx` | 評価のたびに `--force` で上書きする。過去分を残したい場合はユーザーが別途コピーする。 |

## 各スクリプトの役割

| スクリプト | 役割 |
|---|---|
| `get_assessment_state.py` | 現在の評価状態を取得する。読み取り専用で、呼ぶだけでは何も変更されない。 |
| `update_check_result.py` | 確認結果を1件更新し、保存する（初回呼び出し時に自動で保存先を作成するので、別途初期化操作は不要）。AIはこれ以外の方法で確認結果を書き換えない。 |
| `calculate_score.py` | 保存済みの確認結果から、各評価項目の点数を機械的に算出する（AIは点数を目測しない）。 |
| `validate_assessment.py` | criteria_idの存在、check_idの重複、score_thresholdの妥当性、confirmedなのにresult未設定でないか、criteria_versionの整合性、必須項目の欠落を検証する。 |
| `export_assessment.py` | 評価結果をExcelへ出力する。テンプレートはコピーして使い、元ファイルは変更しない。 |

各スクリプトは `python <script>.py --help` で単独動作確認できる。

## Excel出力時にAIが書くのは「推奨対応」だけ

Excelの自由記述4列（評価根拠・到達段階・次の段階・推奨対応）のうち、**推奨対応以外はexport_assessment.pyが確認結果とcriteria.jsonから自動生成する。** AIがこの3列の文章を考える必要はない。

**推奨対応**（現在の到達段階から次の段階へ進むための具体的な対応案）だけはAIが評価項目ごとに作成する。export実行前に `{criteria_id: 推奨対応の文章}` 形式のJSONファイルを `narratives.tmp.json`（パスは前節）に保存し、`--narratives-file` で渡すこと。

## 注意事項

- リポジトリ内から確認できる内容は、必ずユーザーへ聞く前にAI自身で調査すること。
- `confirmed` の確認項目は、評価基準のバージョンが変わらない限り再質問しないこと。
- `check-results.json` を直接編集せず、必ず `update_check_result.py` を経由すること。
- 最終的な評価結果は、固定パス `.agents/state/ai-development-assessment/exports/AI駆動開発_実践力カタログ_評価結果.xlsx` へ出力すること。元のテンプレート（`assets/AI駆動開発_実践力カタログ.xlsx`）は変更しないこと。
