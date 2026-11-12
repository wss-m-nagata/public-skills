# {{サービス名}}の資料

このサービスの責務と実装構成は[アーキテクチャ](20_rules/アーキテクチャ.md)に記載する。
個別APIの一覧と外部インタフェース設計書は`nablarch-basic-design-excel`で作成し、`40_spec/api-spec/`に正本として置く。
テーブルを使う場合は、同スキルで作成したテーブル一覧と定義書の正本を`40_spec/table-definition/`に置く。
機能ごとの主要処理フローと、DBを使う機能のER図は`40_spec/detailed-design/<機能名>/`に置き、正本を参照する。
専用インフラの詳細設計は`40_spec/detailed-design/`に置く。
サービス固有のセットアップと運用は、それぞれ`10_installation/`と`50_operation/`に置く。
共通ルールは[アプリ全体の資料](../../../docs/README.md)に従う。
リソース一覧はサービスの設計と管理範囲が決まった後に`40_spec/detailed-design/`へ作成し、共有インフラの一覧とは分ける。
