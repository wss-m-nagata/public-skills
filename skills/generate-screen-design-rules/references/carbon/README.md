# Carbon ローカルリファレンス（このファイルのみSkill独自の索引です）

このディレクトリ配下の各`.mdx`は、IBM Carbon Design Systemの公式サイトのソース（carbon-website リポジトリ）から、**本Skillのテンプレートが参照する範囲だけを未編集のまま**コピーしたものです。

このREADME.md自体はSkill側で作成した索引であり、Carbon本体のコンテンツではありません。

## 出典・取得情報

- リポジトリ: https://github.com/carbon-design-system/carbon-website
- パス: `src/pages/components/<component>/<page>.mdx`
- ライセンス: Apache License 2.0（リポジトリの`LICENSE`参照）
- 取得日: 2026-09-15（`main`ブランチ、コミット `ea81028857791c9bc5004ee9ae6e82e3e654dfc3` 時点）
- 機械可読な取得情報は同ディレクトリの `VERSION.txt` を参照してください。古いかどうかの判断はこのファイルのコミット/日付を基準にします。

## 利用条件

Apache-2.0ライセンスに従い、著作権表示・ライセンス表示を保持し、改変した場合はその旨を明記する必要があります。

**本ディレクトリのファイルは改変せず原文のまま保存しています。** 規約Markdownへ引用・転記する際は、Carbon Design Systemを出典として明記してください。

## 更新方針

このリファレンスは**取得時点のスナップショット**であり、自動更新は行いません。Carbonの内容が更新された場合、必要になったタイミングで対象`.mdx`を再取得し、取得日を更新してください（自動チェックの仕組みは持たせていません）。

## 収録ファイルと参照ヒントの対応

| 参照ヒント | ローカルファイル |
|---|---|
| UI shell header > Style > Structure | `UI-shell-header/style.mdx` |
| UI shell header > Usage | `UI-shell-header/usage.mdx` |
| UI shell left panel > Style | `UI-shell-left-panel/style.mdx` |
| UI shell left panel > Usage | `UI-shell-left-panel/usage.mdx` |
| UI shell right panel > Usage | `UI-shell-right-panel/usage.mdx` |
| Modal > Usage（Modalとサイドパネルの使い分け） | `modal/usage.mdx` |
| Tabs > Usage | `tabs/usage.mdx` |
| Data table > Usage > Table toolbar / Batch actions | `data-table/usage.mdx` |

上記以外の参照ヒントに該当するローカルファイルが無い場合は、`SKILL.md`の「参照ヒントが記載されていない項目」の手順に従い、公式サイト（https://carbondesignsystem.com/）を直接確認してください。
