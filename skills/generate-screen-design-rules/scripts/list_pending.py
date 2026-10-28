# 修正履歴
# 2026/10/28: 管理台帳から確認待ちを一覧表示する処理を追加。
#   - 対応形式を検証し、外部管理形式を空の一覧として扱わない。

"""管理台帳の要確認・暫定項目を表示する。"""

import argparse
from pathlib import Path
import re
import sys


def main() -> int:
    """管理台帳を変更せず、状態の順に確認待ちを表示する。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path, help='デザインシステム管理台帳.md')
    args = parser.parse_args()
    rows = []
    lines = args.ledger.read_text(encoding='utf-8').splitlines()
    if not any(line.startswith('|') and '状態' in line and ('規約ファイル' in line or line.startswith('| 規約 |')) for line in lines):
        print('管理台帳の状態欄を読み取れません。確認事項の管理先を確認してください。', file=sys.stderr)
        return 2
    for line in lines:
        if not line.startswith('|'):
            continue
        cells = [cell.strip() for cell in re.split(r'(?<!\\)\|', line)[1:-1]]
        if len(cells) == 5 and cells[1] in ('要確認', '暫定'):
            rows.append(cells)
    rows.sort(key=lambda cells: (cells[1] != '要確認', cells[0]))
    for target, state, content, _, _ in rows:
        print(f'{state}: {target}\n  {content.replace("<br>", " / ")}')
    if not rows:
        print('確認待ちの項目はありません。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
