#!/usr/bin/env python3
"""色の組み合わせのコントラスト比（WCAG 2.x の相対輝度による計算）を求めて、基準を満たすかを表示する。

使い方:
    python scripts/contrast.py <前景色> <背景色> [<前景色> <背景色> ...]
    python scripts/contrast.py --fg <色>[,<色>...] --bg <色>[,<色>...]

色は #RRGGBB または #RGB で指定する（例: "#3460fb"）。
シェルで # がコメントとして扱われないよう、色は引用符で囲む。
--fg と --bg を使うと、すべての組み合わせ（前景 × 背景）を一覧で確かめられる。

基準（DADS「コントラスト要件」）:
    テキスト          4.5:1 以上
    テキスト以外      3:1 以上（枠線、アイコン、フォーカスの表示など）
"""

import argparse
import itertools
import re
import sys

# テキストとテキスト以外の基準（DADSのコントラスト要件）
TEXT_MIN = 4.5
NON_TEXT_MIN = 3.0


def _parse_hex(value: str) -> tuple[int, int, int]:
    """#RRGGBB または #RGB を (R, G, B)（0〜255）に変換する。

    Args:
        value: 色の文字列。

    Returns:
        (R, G, B)。

    Raises:
        ValueError: 色の形式が正しくない場合。
    """
    text = value.strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{3}|[0-9a-fA-F]{6}", text):
        raise ValueError(f"色の形式が正しくありません: {value}（#RRGGBB または #RGB で指定してください）")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    """WCAGの相対輝度を返す。

    Args:
        rgb: (R, G, B)（0〜255）。

    Returns:
        相対輝度（0〜1）。
    """
    channels = []
    for value in rgb:
        srgb = value / 255
        channels.append(srgb / 12.92 if srgb <= 0.04045 else ((srgb + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(foreground: str, background: str) -> float:
    """2色のコントラスト比を返す。

    Args:
        foreground: 前景色。
        background: 背景色。

    Returns:
        コントラスト比（1〜21）。
    """
    lighter, darker = sorted(
        (_relative_luminance(_parse_hex(foreground)), _relative_luminance(_parse_hex(background))),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def _judge(ratio: float) -> str:
    """コントラスト比が、どの用途の基準を満たすかを文字で返す。"""
    if ratio >= TEXT_MIN:
        return "テキストOK（4.5:1以上）"
    if ratio >= NON_TEXT_MIN:
        return "テキスト以外のみOK（3:1以上）。テキストには使えない"
    return "NG（3:1未満）"


def main() -> int:
    """引数を読み、結果を表示する。

    Returns:
        終了コード。基準を満たさない組み合わせが1つでもあれば1、すべて満たせば0。
    """
    parser = argparse.ArgumentParser(description="色の組み合わせのコントラスト比を求める。")
    parser.add_argument("colors", nargs="*", help="前景色と背景色を交互に並べる")
    parser.add_argument("--fg", help="前景色（カンマ区切りで複数）")
    parser.add_argument("--bg", help="背景色（カンマ区切りで複数）")
    args = parser.parse_args()

    pairs: list[tuple[str, str]] = []
    if args.fg and args.bg:
        pairs += list(itertools.product(args.fg.split(","), args.bg.split(",")))
    if args.colors:
        if len(args.colors) % 2 != 0:
            parser.error("色は、前景色と背景色を2つ1組で指定してください。")
        pairs += list(zip(args.colors[0::2], args.colors[1::2]))
    if not pairs:
        parser.error("色を指定してください。")

    print(f"{'前景':<10}{'背景':<10}{'比':>7}  判定")
    has_ng = False
    for foreground, background in pairs:
        ratio = contrast_ratio(foreground, background)
        has_ng = has_ng or ratio < NON_TEXT_MIN
        print(f"{foreground:<10}{background:<10}{ratio:>6.2f}:1  {_judge(ratio)}")
    return 1 if has_ng else 0


if __name__ == "__main__":
    sys.exit(main())
