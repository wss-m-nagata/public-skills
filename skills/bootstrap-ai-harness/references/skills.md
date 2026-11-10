# 必須スキルの導入と使用

## 標準で導入するスキル

| スキル | 用途 | 実行するタイミング |
| --- | --- | --- |
| `generate-screen-design-rules` | DADSを主、Carbonを補完として、具体値と部品の状態を含む画面設計規約を作る。 | 初期構築時と規約の更新時。 |
| `process-flow-diagram` | 画面、バックエンド処理、テーブルやファイルの関係を処理フロー図に整理する。 | 機能の洗い出し、見積もり、設計の前段階。 |
| `nablarch-frontend-design-excel` | 画面一覧・画面遷移・画面機能設計・画面単体テスト仕様などをExcelの様式で作る。 | 対象と内容が決まり、設計書を作成・更新するとき。 |
| `nablarch-basic-design-excel` | API、機能、外部インタフェース、テーブルなどのバックエンド設計書や単体テスト仕様をExcelの様式で作る。 | 対象と内容が決まり、設計書を作成・更新するとき。 |

この4つを基本セットとし、明示されたプロジェクト方針により不要なものがあれば理由を示して除外する。
`design-standards`は画面規約で必要に応じて用いる任意の補完スキルであり、必須ではない。
Playwrightの補助スキルは必要に応じて追加する。

## 導入

1. 新規プロジェクトのGitリポジトリのルートで、公開リポジトリから基本セットをプロジェクト単位で導入する。
   Claude Codeの場合は次のコマンドを使う。

   ```powershell
   gh skill install wss-m-nagata/public-skills generate-screen-design-rules --agent claude-code --scope project
   gh skill install wss-m-nagata/public-skills process-flow-diagram --agent claude-code --scope project
   gh skill install wss-m-nagata/public-skills nablarch-frontend-design-excel --agent claude-code --scope project
   gh skill install wss-m-nagata/public-skills nablarch-basic-design-excel --agent claude-code --scope project
   ```

   Codexでも使用する場合は、同じ各コマンドの `--agent claude-code` を `--agent codex` に置き換えて実行する。
   それぞれの配置先、正本と同期方法を定める。
   取得する版の指定が必要なら利用者の方針に従って `--pin` を指定し、指定しない場合はコマンドの既定の解決に従う。
2. 各コマンドの終了結果と導入先の `SKILL.md`、付属資料を確認する。
   公開版に目的のスキルがない場合や取得に失敗した場合は、導入済みと扱わず、スキル名とエラーを報告する。
   利用可能な版や公開が確認されるまで、そのスキルを必要とする作業は実施しない。
   導入先に同名スキルがある場合は強制上書きせず、内容と版の差を確認して既存の利用方針に合わせる。
   再配布条件と、Python、openpyxl、Excel等の必要な実行環境を各スキルの指示に従って確認する。
   環境の不足は報告し、未承認のインストールを行わない。
3. スキル名、配置先、実行する作業、参照する規約を新規プロジェクトのAI向け指示に追記する。
   対象AIが実際にその配置を読み込めることを確認し、認識に再読み込みが必要な場合は利用者に伝える。

## 画面規約の初期生成

1. 簡略版の画面規約を先に配置せず、出力先を`nuxt/docs/20_rules/screen-design-rules/`、部品ライブラリをVuetify、画面URL規約を`docs/20_rules/URL命名規則.md`として、導入したスキルの初回生成手順を実行する。
   Nuxt・VueのSPA、画面実装方針の置き場所 `nuxt/docs/20_rules/フロントエンド実装方針.md`、画面設計の置き場所 `nuxt/docs/60_design/`、DADS優先・Carbon補完も決定済みの前提として渡す。
   ユーザーが別の方針を決めていない場合、Vuetifyの部品を基本として規約との対応を実現方式に整理する。
   ボタンやフォームの具体的な表示・状態・属性は、生成スキルの資料と採用するVuetifyの版を確認し、規約・実現方式に分けて書く。
   実装コードをまだ作っていない場合は、設定ファイルや共通部品を実装済みと記載しない。
2. 対象プロジェクトで決定済みの情報を渡し、必要な画面・メニュー、色など未決定の事項はスキルの指示に沿って確認する。
   推測を確定事項として記載しない。
   ブランド色、対応端末、実際のメニュー構造、表示密度や操作上の例外は、技術スタックだけでは確定しない。
3. 同スキルの`check_output.py`と`list_pending.py`を実行し、生成物のリンクやプロジェクト固有設定、未決定事項を確認する。
   未決定事項が残る場合は完成と扱わず、管理先とともに報告する。

## 設計書の作成

機能の洗い出しや見積もりでは `process-flow-diagram` に従って処理フロー図を作成・更新する。
図の出力先とプロジェクト固有ルールは、同スキルの手順と対象プロジェクトの資料配置に従う。
画面設計は`nablarch-frontend-design-excel`を使い、`nuxt/docs/60_design/`へプロジェクトの採番と配置に従って作成する。
バックエンドは`nablarch-basic-design-excel`を使い、サービスのAPI仕様・詳細設計やDBの管理範囲に合う場所へ作成する。
共通のMarkdown API仕様とExcelの担当範囲・正本を決め、同じ契約を矛盾した二重の正本にしない。
スキルに付属する生成・検証手順と対象成果物の確認を実施する。
機能やDB仕様が未決定の段階で、実在する仕様や完成済みの設計書を捏造しない。
