#!/usr/bin/env python3
"""DADSのDesign Token（tokens.json）から、値の早見表（Markdown）を生成する。

手で書き写すと元の資料とずれるおそれがあるため、トークンから作れる値（色、文字、角丸、影）は、
このスクリプトで生成する。トークンの別名（例: {Color.Primitive.Red.800}）は、実際の値まで解決する。

使い方:
    python scripts/gen_quick_values.py [<tokens.json> [<出力先.md>]]

既定:
    tokens.json : references/dads/design-tokens/tokens.json
    出力先      : references/dads/quick-values-tokens.md

tokens.json を再取得したときに、もう一度実行して、早見表を更新する。
"""

import json
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TOKENS = SKILL_DIR / "references/dads/design-tokens/tokens.json"
DEFAULT_OUTPUT = SKILL_DIR / "references/dads/quick-values-tokens.md"

# 別名の形（例: {Color.Primitive.Red.800}）
_ALIAS = re.compile(r"^\{(.+)\}$")


def _find_color_root(tokens: dict) -> dict:
    """トークンのファイルから、色のトークンの根（Primitive、Neutral、Semantic、Keyを持つ辞書）を探す。

    ファイルによって、色のトークンが「Color」の直下にある場合と、「Color.Color」の下にある場合がある。

    Args:
        tokens: tokens.json の内容。

    Returns:
        色のトークンの根。

    Raises:
        KeyError: 見つからない場合。
    """
    color = tokens["Color"]
    return color["Color"] if "Primitive" not in color and "Color" in color else color


def _lookup(tokens: dict, path: str):
    """「Color.Primitive.Red.800」のような経路で、トークンを引く。

    Args:
        tokens: tokens.json の内容。
        path: ドットで区切った経路。先頭が「Color」で、色の根が「Color.Color」の下にある場合も引ける。

    Returns:
        経路の先にある値（辞書または葉のトークン）。
    """
    node = tokens
    for key in path.split("."):
        # 色のトークンが「Color」の下に、もう1つ「Color」を挟んで入っている場合は、1つ下へ降りてから引く
        if key not in node and isinstance(node.get("Color"), dict):
            node = node["Color"]
        node = node[key]
    return node


def _resolve(tokens: dict, value: str, depth: int = 0) -> str:
    """別名を、実際の値まで解決する。

    Args:
        tokens: tokens.json の内容。
        value: トークンの値（別名の場合がある）。
        depth: 循環を防ぐための深さ。

    Returns:
        解決後の値。
    """
    match = _ALIAS.match(value)
    if not match or depth > 10:
        return value
    try:
        leaf = _lookup(tokens, match.group(1))
        return _resolve(tokens, str(leaf["$value"]), depth + 1)
    except (KeyError, TypeError):
        return value


def _is_leaf(node) -> bool:
    """辞書がトークンの葉（$value を持つ）かどうか。"""
    return isinstance(node, dict) and "$value" in node


def _steps(tokens: dict, node: dict) -> list[tuple[str, str]]:
    """段階（50、100、…）ごとの、解決後の値の一覧を返す。"""
    return [(key, _resolve(tokens, str(leaf["$value"]))) for key, leaf in node.items() if _is_leaf(leaf)]


def _shadow_css(shadows: list[dict]) -> str:
    """影のトークンを、CSS の box-shadow の値に変換する。"""
    return ", ".join(f"{s['x']} {s['y']} {s['blur']} {s['spread']} {s['color']}" for s in shadows)


def generate(tokens: dict) -> str:
    """早見表の本文（Markdown）を作る。

    Args:
        tokens: tokens.json の内容。

    Returns:
        Markdown の文字列。
    """
    color = _find_color_root(tokens)
    lines = [
        "# DADS Design Token 早見表（生成物）",
        "",
        "`scripts/gen_quick_values.py` が `design-tokens/tokens.json` から生成した。**手で書き換えない。**",
        "tokens.json を更新したら、スクリプトをもう一度実行して作り直す。",
        "値の出典は、DADS の Design Token（https://github.com/digital-go-jp/design-tokens）。",
        "別名（例: Semantic が Primitive を指す）は、実際の値まで解決してある。",
        "",
        "## 色",
        "",
        "### キー（既定の色相）",
        "",
        "| 段階 | 値 |",
        "| --- | --- |",
    ]
    lines += [f"| {k} | `{v}` |" for k, v in _steps(tokens, color["Key"])]

    lines += ["", "### ニュートラル", "", "| 名前 | 値 |", "| --- | --- |"]
    neutral = color["Neutral"]
    for name, node in neutral.items():
        if _is_leaf(node):
            lines.append(f"| {name} | `{_resolve(tokens, str(node['$value']))}` |")
        else:
            lines += [f"| {name} {k} | `{v}` |" for k, v in _steps(tokens, node)]

    lines += ["", "### セマンティック（成功・エラー・警告）", "", "| 名前 | 参照先 | 値 |", "| --- | --- | --- |"]

    def walk_semantic(prefix: str, node: dict) -> None:
        for key, child in node.items():
            if _is_leaf(child):
                raw = str(child["$value"])
                lines.append(f"| {prefix}.{key} | `{raw}` | `{_resolve(tokens, raw)}` |")
            elif isinstance(child, dict):
                walk_semantic(f"{prefix}.{key}", child)

    walk_semantic("Semantic", color["Semantic"])

    lines += ["", "### プリミティブ（色相ごと）", ""]
    for hue, node in color["Primitive"].items():
        lines.append(f"- **{hue}**: " + "、".join(f"{k} `{v}`" for k, v in _steps(tokens, node)))

    typography = tokens["Typography"]
    lines += ["", "## 文字", "", "| 種類 | 値 |", "| --- | --- |"]
    for group in ("FontFamily", "FontWeight", "FontSize", "LineHeight"):
        values = "、".join(f"{k}: `{_resolve(tokens, str(leaf['$value']))}`" for k, leaf in typography[group].items() if _is_leaf(leaf))
        lines.append(f"| {group} | {values} |")

    size = tokens["Size"]
    lines += ["", "## 角丸", "", "| 名前 | 値 |", "| --- | --- |"]
    lines += [f"| {k} | `{leaf['$value']}` |" for k, leaf in size["BorderRadius"].items() if _is_leaf(leaf)]

    lines += ["", "## 影（エレベーション）", "", "| スタイル | box-shadow |", "| --- | --- |"]
    lines += [f"| {k} | `{_shadow_css(leaf['$value'])}` |" for k, leaf in size["Elevation"].items() if _is_leaf(leaf)]
    return "\n".join(lines) + "\n"


def main() -> int:
    """引数を読み、早見表を書き出す。

    Returns:
        終了コード。
    """
    tokens_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_TOKENS
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    tokens = json.loads(tokens_path.read_text(encoding="utf-8"))
    output_path.write_text(generate(tokens), encoding="utf-8", newline="\n")
    print(f"書き出しました: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
