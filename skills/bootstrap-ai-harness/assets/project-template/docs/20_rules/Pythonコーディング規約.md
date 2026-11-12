<!--
# 修正履歴
# {{作成日}}: 初版作成。
-->

# Pythonコーディング規約

## インデントと命名

インデントは半角スペース4つ、UTF-8 BOMなし、LFとする。
モジュール、関数、変数はsnake_case、クラスはUpperCamelCase、定数はUPPER_SNAKE_CASEとする。
内部用の関数・メソッドは先頭にアンダースコアを付ける。

## コメント（docstring）

クラスとメソッドには役割が分かるdocstringを書く。
概要を最初の1行に書き、詳細がある場合は空行を挟む。
必要に応じて引数、戻り値、例外、属性を記載する。
docstringはクラスやメソッドの定義の直後に置く。

### クラスのdocstring

クラスの目的と、利用者が知る必要のある属性や注意事項を記載する。

```python
class PriceRange:
    """許容する価格の範囲を表す。

    Attributes:
        minimum: 許容する最小価格。
        maximum: 許容する最大価格。
    """

    def __init__(self, minimum: int, maximum: int) -> None:
        """価格の範囲を設定する。"""
        self.minimum = minimum
        self.maximum = maximum
```

### メソッドのdocstring

引数と戻り値、呼び出し側が扱う必要のある例外を説明する。

```python
def calculate_total(price: int, count: int) -> int:
    """単価と数量から合計を求める。

    Args:
        price: 単価。
        count: 数量。

    Returns:
        単価と数量の積。
    """
    return price * count
```

## 実装とエラー

複雑な処理は主要な処理段階にコメントを付ける。
データクラスの各項目と列挙値には意味を示す。
一箇所だけの短い処理は、名前を付けることで理解が良くなる場合を除き、無理に関数に分けない。

仕様で許されない入力はエラーとして検出し、不必要な既定値で吸収しない。
外部連携のように仕様上揺れがある場合は、許容範囲を明示する。

## ログ

DEBUG時以外に不要なJSON変換などはログレベルを確認してから評価する。
秘密情報をログに出さず、想定外の例外は原因を追跡できる情報を記録する。
ログの形式や共通ライブラリは、採用する環境で定める。

```python
import json
import logging

LOGGER = logging.getLogger(__name__)

if LOGGER.isEnabledFor(logging.DEBUG):
    LOGGER.debug("処理対象: %s", json.dumps(safe_data, ensure_ascii=False))
```

`safe_data`には秘密情報や不必要な個人情報を含めない。
ログレベルがDEBUGでないときにシリアライズ処理自体を行わないため、出力しないログのための処理負荷を避けられる。

## 改版履歴

ソースの先頭に改版履歴コメントを置き、作成・変更の目的を日付とともに記す。
関連する小さな修正は同じ項目の下に記載する。
同じ目的の小さな修正は`  - `で字下げし、別の日付で対応した場合はその日付も記載する。

```python
# Revision History
# 2026/01/10: 一覧取得処理を追加。
#   - 入力条件の検証を調整。
#   - 2026/01/12: エラー時のログを修正。
```

Python APIの層と責務は[API実装方針](API実装方針.md)に従う。
