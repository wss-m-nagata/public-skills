# 修正履歴
# 2026/10/28: 規約の参照と色見本の整合確認を追加。
#   - ディレクトリ参照と手動確認が必要な色見本を区別。

"""生成した規約のマーカー、ローカルリンク、色見本を確認する。"""

import argparse
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


def main() -> int:
    """機械的に確認できる不整合を報告する。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='生成先ディレクトリ')
    args = parser.parse_args()
    if not args.output.is_dir():
        parser.error('生成先ディレクトリがありません。')
    errors = []
    warnings = []
    for path in sorted(args.output.glob('*.md')):
        text = path.read_text(encoding='utf-8')
        # コード例の中の仮パスとマーカーは出力上の参照として扱わない。
        text = re.sub(r'(?ms)^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\1\s*$', '', text)
        if '<!-- template-only:' in text:
            errors.append(f'{path}: テンプレート専用マーカーが残っています。')
        for line in text.splitlines():
            for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', line):
                target = link.split('#', 1)[0]
                if not target or re.match(r'^[a-zA-Z][\w+.-]*:', target):
                    continue
                if not (path.parent / target).exists():
                    errors.append(f'{path}: 参照先がありません: {target}')
            # 同一行のSVGとHEX色が1対1の場合だけ自動比較する。
            refs = re.findall(r'!\[[^\]]*\]\(([^)]+\.svg)\)', line)
            colors = re.findall(r'(?<![\w])#[0-9a-fA-F]{6}(?![0-9a-fA-F])', line)
            if refs and len(refs) == len(colors):
                for ref, color in zip(refs, colors):
                    try:
                        root = ET.parse(path.parent / ref).getroot()
                        fills = {element.attrib.get('fill', '').lower() for element in root.iter()}
                        if color.lower() not in fills:
                            errors.append(f'{path}: {ref} と {color} が一致しません。')
                    except (OSError, ET.ParseError) as error:
                        errors.append(f'{path}: {ref} を解析できません: {error}')
            elif refs and colors:
                warnings.append(f'{path}: 色見本と値の対応は手動確認が必要です: {line}')
    # 台帳から参照する規約ファイルと見出しの存在を確認する。
    ledger = args.output / 'デザインシステム管理台帳.md'
    if not ledger.is_file():
        errors.append(f'{ledger}: 管理台帳がありません。')
    else:
        for line in ledger.read_text(encoding='utf-8').splitlines():
            if not line.startswith('|'):
                continue
            cells = [cell.strip() for cell in re.split(r'(?<!\\)\|', line)[1:-1]]
            if len(cells) != 5 or cells[1] not in ('要確認', '暫定', '確定'):
                continue
            parts = cells[0].split(' / ', 1)
            if len(parts) < 2 or not parts[0].endswith('.md'):
                errors.append(f'{ledger}: 規約ファイル・見出しを特定できません: {cells[0]}')
                continue
            target = args.output / parts[0]
            if not target.is_file():
                errors.append(f'{ledger}: 規約ファイルがありません: {parts[0]}')
                continue
            headings = re.findall(r'^#{2,6}\s+(.+?)\s*$', target.read_text(encoding='utf-8'), re.M)
            # 見出し自体に「 / 」が含まれるため、先頭から実在する見出しに一致させる。
            remaining = parts[1]
            while remaining:
                candidates = [heading for heading in headings if remaining == heading or remaining.startswith(heading + ' / ')]
                if not candidates:
                    break
                matched = max(candidates, key=len)
                remaining = remaining[len(matched):].removeprefix(' / ')
            if remaining:
                errors.append(f'{ledger}: 対応する見出しがありません: {cells[0]}')
    if warnings:
        print('\n'.join(warnings), file=sys.stderr)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('マーカー、ローカルリンク、対応づけ可能なSVG色見本を確認しました。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
