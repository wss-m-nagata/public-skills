# 修正履歴
# 2026/10/28: 色見本のSVGを生成する処理を追加。

"""色と必要な背景を指定してSVGの色見本を作る。"""

import argparse
from pathlib import Path
import re
import sys


def _color(value: str) -> str:
    """指定された6桁のHEX色を検証する。"""
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        raise argparse.ArgumentTypeError('色は #RRGGBB 形式で指定してください。')
    return value.lower()


def main() -> int:
    """値と不透明度から見本を作り、既存ファイルは明示時のみ更新する。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path, help='保存するSVGファイル')
    parser.add_argument('color', type=_color, help='色（#RRGGBB）')
    parser.add_argument('--opacity', type=float, default=1.0, help='不透明度（0〜1）')
    parser.add_argument('--background', type=_color, help='透明色を重ねる背景色')
    parser.add_argument('--force', action='store_true', help='既存の見本を上書きする')
    args = parser.parse_args()
    if not 0 <= args.opacity <= 1:
        parser.error('不透明度は0から1の範囲で指定してください。')
    if args.opacity < 1 and not args.background:
        parser.error('透明色の見本には背景色が必要です。')
    if args.path.suffix.lower() != '.svg':
        parser.error('出力先は.svgファイルを指定してください。')
    if args.path.exists() and not args.force:
        parser.error('出力先が既にあります。更新する場合は --force を指定してください。')
    # 白でも識別できる枠を付け、透明色は指定背景に重ねる。
    background = f'<rect width="64" height="20" fill="{args.background}"/>' if args.background else ''
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="20" viewBox="0 0 64 20">'
           f'<title>{args.color} opacity {args.opacity}</title>{background}'
           f'<rect x="0.5" y="0.5" width="63" height="19" fill="{args.color}" '
           f'fill-opacity="{args.opacity}"/><rect x="0.5" y="0.5" width="63" height="19" '
           'fill="none" stroke="#767676"/></svg>\n')
    args.path.parent.mkdir(parents=True, exist_ok=True)
    args.path.write_text(svg, encoding='utf-8', newline='\n')
    print(f'作成しました: {args.path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
