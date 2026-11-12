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

1. 新規プロジェクトで利用するAIごとに、基本セットの所在と付属資料を先に確認する。
   `nablarch-frontend-design-excel`は利用可能なものを使う前提とし、同名スキルを無条件で再導入しない。
   不足するスキルだけを、新規プロジェクトのGitリポジトリのルートで公開リポジトリからプロジェクト単位で導入する。
   Claude Codeの場合は、必要なスキルに対応する次のコマンドを使う。

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
   `generate-screen-design-rules` は少なくとも `assets/screen-design-rules-template/`、`scripts/extract_template_metadata.py`、`scripts/check_output.py`、`scripts/list_pending.py` の存在を確認する。
   中断された導入ではディレクトリや `SKILL.md` が存在しても一部しか展開されていない場合があるため、導入成功と扱わず復旧する。
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
   URL命名規則の3階層はテンプレートの標準案として提示し、実際のメニューと照合して採用を確認する。
   別の階層を採用する場合はURL命名規則と画面規約を同時に調整し、互いに矛盾したまま確定しない。
3. 同スキルの`check_output.py`と`list_pending.py`を実行し、生成物のリンクやプロジェクト固有設定、未決定事項を確認する。
   初回のテンプレート複製後は、同スキルの`extract_template_metadata.py`で管理情報を台帳へ移してから検査する。
   `check_output.py`の成功はマーカーやリンクなどの形式確認であり、規約の具体化、Vuetifyとの対応、ユーザー判断の完了を意味しない。
   同スキルのモック確認手順に従い、実際のメニューや対象画面に基づく確認用モックを作り、ブラウザーで値と操作を確認する。
   付属のレイアウト例は参考素材であり、プロジェクトの規約を反映済みの確認用モックとして扱わない。
   少なくとも文字サイズ、ボタンの表示サイズと操作できる領域、余白、色、フォーカスを測定し、規約との差異を修正してから利用者に見せる。
   画面規約の確定には、モックを利用者に見せて判断を受け、指摘を反映する。
   モックの未確認項目や利用者の判断待ちは、形式検査の結果と分けて報告する。
   未決定事項が残る場合は完成と扱わず、管理先とともに報告する。

## 設計書の作成

機能の洗い出しや見積もりでは `process-flow-diagram` に従って処理フロー図を作成・更新する。
図の出力先とプロジェクト固有ルールは、同スキルの手順と対象プロジェクトの資料配置に従う。
画面設計は`nablarch-frontend-design-excel`を使い、`nuxt/docs/60_design/`へプロジェクトの採番と配置に従って作成する。
バックエンドのAPI一覧と外部インタフェース設計書は`nablarch-basic-design-excel`で作成し、各サービスの`docs/40_spec/api-spec/`に正本として置く。
全APIに共通する入出力・エラーの決まりは、アプリ全体の`docs/40_spec/API共通仕様.md`に置く。個別APIの契約はExcelに記載し、別のMarkdownを正本として作らない。
テーブルを使うサービスでは、同スキルでテーブル一覧とテーブル定義書を作成し、各サービスの`docs/40_spec/table-definition/`に正本として置く。
機能ごとの主要処理フローは`process-flow-diagram`を使い、`docs/40_spec/detailed-design/<機能名>/`に置く。DBを使う機能では、同じ機能のディレクトリにER図を置く。
機能別の一覧や図からサービスのAPI仕様・テーブル定義の正本を参照し、個別仕様書の複製を別の正本として管理しない。
DBを使わないサービスではテーブル一覧、テーブル定義とER図を作成しない。
スキルに付属する生成・検証手順と対象成果物の確認を実施する。
機能やDB仕様が未決定の段階で、実在する仕様や完成済みの設計書を捏造しない。
