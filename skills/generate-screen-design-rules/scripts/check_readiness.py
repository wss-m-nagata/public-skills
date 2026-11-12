# 修正履歴
# 2026/11/12: 形式検査と管理台帳の未決定項目をまとめて確認。

"""画面規約の形式と管理台帳の確認待ちを別々に報告する。"""

import argparse
from pathlib import Path
import subprocess
import sys


def main() -> int:
    """形式不備と確認待ちを区別し、確認できない台帳を成功扱いしない。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='画面規約の生成先ディレクトリ')
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent

    # 既存の形式検査を使い、手動確認の警告もそのまま表示する。
    check = subprocess.run(
        [sys.executable, '-X', 'utf8', str(scripts / 'check_output.py'), str(args.output)],
        capture_output=True, text=True, encoding='utf-8',
    )
    print('【形式検査】')
    if check.stdout:
        print(check.stdout, end='')
    if check.stderr:
        print(check.stderr, end='', file=sys.stderr)

    # 管理台帳を別途確認し、出典や管理先を調べる必要を残す。
    print('【管理台帳の確認待ち】')
    ledger = args.output / 'デザインシステム管理台帳.md'
    if not ledger.is_file():
        print('管理台帳がないため、確認待ちの有無は未確認です。', file=sys.stderr)
        return 2
    pending = subprocess.run(
        [sys.executable, '-X', 'utf8', str(scripts / 'list_pending.py'), str(ledger)],
        capture_output=True, text=True, encoding='utf-8',
    )
    if pending.stdout:
        print(pending.stdout, end='')
    if pending.stderr:
        print(pending.stderr, end='', file=sys.stderr)
    if pending.returncode:
        print('管理台帳を確認できないため、完成とは判断できません。', file=sys.stderr)
        return 2
    lines = pending.stdout.splitlines()
    required = sum(line.startswith('要確認: ') for line in lines)
    tentative = sum(line.startswith('暫定: ') for line in lines)
    print(f'要確認: {required}件、暫定: {tentative}件。')
    print('形式検査と台帳の結果だけでは、内容の妥当性や利用者の確認は証明できません。')
    return 1 if check.returncode or required or tentative else 0


if __name__ == '__main__':
    sys.exit(main())
