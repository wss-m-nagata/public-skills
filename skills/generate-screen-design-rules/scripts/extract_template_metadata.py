# 修正履歴
# 2026/10/28: テンプレート専用情報を台帳に移す処理を追加。

"""生成先のテンプレート専用情報を管理台帳に移す。"""

import argparse
from pathlib import Path
import re
import sys


START = '<!-- template-only:start -->'
END = '<!-- template-only:end -->'
LEDGER = 'デザインシステム管理台帳.md'
TEMPLATE = (Path(__file__).resolve().parent.parent / 'assets' / 'screen-design-rules-template').resolve()
FIELDS = re.compile(r'^- \*\*([^*]+):\*\*\s*(.*)$')
MANAGEMENT_FIELDS = {
    '状態', '出典', '主な出典', '基本', '基本方針', '補完', '補完元',
    '高度な操作の補完', '使い分けの補完', '参考', '参照ヒント',
    '検索キーワード', 'ローカル参照', '参照URL', '候補', '確認事項',
}


def _cell(value: str) -> str:
    """表のセルに収まるように改行と区切り文字を変換する。"""
    return value.replace('|', r'\|').replace('\n', '<br>')


def _extract(path: Path) -> tuple[str, dict[str, list[str]]]:
    """明示された範囲と対応する見出しを取得する。"""
    lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
    output = []
    groups: dict[str, list[str]] = {}
    headings: dict[int, str] = {}
    block = None
    block_key = None
    fenced = False
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('```') or stripped.startswith('~~~'):
            fenced = not fenced
        if fenced and stripped not in (START, END):
            output.append(line)
            continue
        match = re.match(r'^(#{2,6})\s+(.+?)\s*$', line)
        if match and block is None:
            level = len(match.group(1))
            headings = {key: value for key, value in headings.items() if key < level}
            headings[level] = match.group(2)
        if stripped == START:
            if block is not None or 2 not in headings or fenced:
                raise ValueError(f'{path}:{number}: 開始位置が不正です。')
            # 確認事項は、その直前の対象見出しに関連づける。
            generic = {'確認事項', '説明', '規約', '対象', '禁止事項', '参考例', 'NG例'}
            relevant = [value for _, value in sorted(headings.items()) if value not in generic]
            block_key = f'{path.name} / ' + ' / '.join(relevant)
            block = []
        elif stripped == END:
            if block is None:
                raise ValueError(f'{path}:{number}: 対応する開始マーカーがありません。')
            if not any(item.strip() for item in block):
                raise ValueError(f'{path}:{number}: 空の管理情報です。')
            groups.setdefault(block_key, []).extend(block)
            block = None
        elif block is not None:
            if match and match.group(2) != '確認事項':
                raise ValueError(f'{path}:{number}: 管理情報の範囲に見出しを含められません。')
            # 値・説明・表は規約に残す。誤って囲まれた場合は書き換える前に停止する。
            field = FIELDS.match(stripped)
            if stripped and stripped != '### 確認事項' and not re.match(r'^- \[[ xX]\]\s+', stripped):
                if not field or field.group(1) not in MANAGEMENT_FIELDS:
                    raise ValueError(f'{path}:{number}: 管理情報以外の内容が含まれています: {stripped}')
            block.append(line.rstrip('\n'))
        else:
            output.append(line)
    if block is not None:
        raise ValueError(f'{path}: 終了マーカーがありません。')
    return ''.join(output), groups


def _row(key: str, lines: list[str]) -> str:
    """管理情報を失わず台帳の行にする。"""
    state = ''
    sources = []
    references = []
    other = []
    for line in lines:
        if not line.strip():
            continue
        field = FIELDS.match(line)
        if field:
            label, value = field.groups()
            if label == '状態':
                if state and state != value:
                    raise ValueError(f'{key}: 異なる状態が同じ対象にあります。項目ごとに分けてください。')
                state = value
            elif label in ('出典', '主な出典', '基本', '基本方針', '補完', '補完元', '高度な操作の補完', '使い分けの補完', '参考'):
                sources.append(f'{label}: {value}')
            elif label in ('参照ヒント', '検索キーワード', 'ローカル参照', '参照URL'):
                references.append(f'{label}: {value}')
            else:
                other.append(line)
        else:
            other.append(line)
    if not state:
        raise ValueError(f'{key}: 状態がありません。')
    return '| ' + ' | '.join(_cell(value) for value in (key, state, '\n'.join(other), '\n'.join(sources), '\n'.join(references))) + ' |\n'


def main() -> int:
    """生成先を検証し、台帳への追記とマーカー部分の削除を行う。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='生成先ディレクトリ')
    parser.add_argument('--dry-run', action='store_true', help='変更せず対象を表示する')
    args = parser.parse_args()
    output = args.output.resolve()
    if output == TEMPLATE or TEMPLATE in output.parents:
        parser.error('テンプレート本体は変更できません。生成先を指定してください。')
    ledger_path = output / LEDGER
    if not ledger_path.is_file():
        parser.error(f'管理台帳がありません: {ledger_path}')
    try:
        # すべてを検証してから書き込む。既存行は変更しない。
        ledger = ledger_path.read_text(encoding='utf-8')
        anchor = '|---|---|---|---|---|\n'
        if ledger.count(anchor) != 1:
            raise ValueError('管理台帳の項目一覧を特定できません。')
        existing = {line.split('|', 2)[1].strip() for line in ledger.splitlines() if line.startswith('|') and line.count('|') >= 2}
        changes = {}
        rows = []
        for path in sorted(output.glob('*.md')):
            if path.name == LEDGER:
                continue
            updated, groups = _extract(path)
            if groups:
                changes[path] = updated
            for key, lines in groups.items():
                if key in existing:
                    raise ValueError(f'{key}: 台帳に同じ対象があります。自動上書きは行いません。')
                existing.add(key)
                rows.append(_row(key, lines))
        if not rows:
            print('移動するテンプレート専用情報はありません。')
            return 0
        print(f'対象: {len(changes)}ファイル、{len(rows)}項目。')
        if args.dry_run:
            return 0
        # 新規に抽出した行は確認の優先順位で並べ、既存の行には手を加えない。
        order = {'要確認': 0, '暫定': 1, '確定': 2}
        rows.sort(key=lambda row: order.get(row.split('|')[2].strip(), 3))
        ledger = ledger.replace(anchor, anchor + ''.join(rows), 1)
        ledger_path.write_text(ledger, encoding='utf-8', newline='\n')
        for path, updated in changes.items():
            path.write_text(updated, encoding='utf-8', newline='\n')
        return 0
    except (ValueError, OSError) as error:
        print(f'エラー: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
