---
name: bootstrap-ai-harness
description: Nuxt・Vue・VuetifyのWeb画面、サービス単位のPython API、AWS CDK、Playwrightを前提に、新規WebアプリのAI開発ハーネスを構築する。資料・AI指示・スキルの配置と運用をテンプレートから整備するときに使用する。
license: MIT
allowed-tools: Read Grep Glob Write Bash(./skills/bootstrap-ai-harness/scripts/*)
---

# WebアプリのAI開発ハーネス構築

アプリコード、CDKコード、CI実装、デプロイは作成しない。
新規Webアプリをリポジトリのルートとし、資料とAI指示がその中で完結するようにする。

1. 対象場所、既存の指示とファイル、ユーザーの決定事項を確認する。
   元プロジェクトや作業中のリポジトリを対象と誤認しない。
2. [適用手順](references/design.md)、[必須スキルの導入](references/skills.md)、[固有情報の反映](references/customization.md)を読み、`assets/project-template/`の内容を対象へ適合させる。
   未決定事項や未実装のものを確定済みの事実にしない。
   対象に既存ファイルがある場合は上書きせず、内容を確認して統合する。
3. 対象アプリの目的、サービス、DB管理責任、認証、AWSの識別名と環境を確認し、決定済みの事項を該当する正本へ反映する。
   大きな未決定事項は確認し、決まっている範囲を先に進める。
4. [必須スキルの導入](references/skills.md)に従い、画面規約と設計書の作成に必要なスキルを導入する。
   初期構築時に画面規約を生成し、設計書は仕様・対象が決まった時点で対応スキルを使って作成する。
   サービスの資料は`assets/service-template/`をサービスごとに適用する。
5. 出力の未置換箇所、相対リンク、規約とAI指示の整合、元プロジェクト固有の値、実在しない実装への参照を確認する。
   画面規約生成スキルが要求する検証を実施し、未決定事項や不足する依存関係を明示する。
   構築結果、反映した決定、未決定事項、検証の実施範囲を報告する。
