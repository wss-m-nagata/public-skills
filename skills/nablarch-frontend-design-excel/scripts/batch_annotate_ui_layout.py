# 修正履歴
# 2026/11/11: 複数設計書の画像配置でExcelの起動を共有する。
"""複数の設計書に画像と要素IDを配置し、Excelの起動を共有する。

使い方: python -X utf8 batch_annotate_ui_layout.py ジョブ一覧.json
JSON: {"jobs":[{"source":"元.xlsx","definition":"画像配置.json","output":"作業版.xlsx"}]}
各パスはジョブ一覧JSONからの相対パス。出力はすべて未作成でなければならない。
途中の失敗時は中止する。処理済みの作業版は残るが、元ファイルは変更しない。
"""
import argparse
import json
from pathlib import Path

from annotate_ui_layout import annotate


def _jobs(manifest_path):
    """パスの重複や不足を、Excel起動前に確認する。"""
    manifest = Path(manifest_path).resolve()
    data = json.loads(manifest.read_text(encoding='utf-8'))
    entries = data.get('jobs')
    if not isinstance(entries, list) or not entries:
        raise ValueError('jobsに1件以上指定してください。')
    result = []
    outputs = set()
    for entry in entries:
        source, definition, output = ((manifest.parent / entry[key]).resolve() for key in ('source', 'definition', 'output'))
        if not source.is_file() or not definition.is_file():
            raise ValueError(f'入力ファイルがありません: {source}, {definition}')
        if source == output or output.exists() or output in outputs:
            raise ValueError(f'出力は未作成の異なるパスを指定してください: {output}')
        outputs.add(output)
        result.append((source, definition, output))
    if outputs.intersection(source for source, _, _ in result):
        raise ValueError('別ジョブの入力を出力として指定できません。')
    return result


def run(manifest_path):
    """Excelを一度だけ起動して、各作業版を順番に作成する。"""
    jobs = _jobs(manifest_path)
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    excel = None
    try:
        excel = win32com.client.DispatchEx('Excel.Application')
        excel.Visible = False
        excel.DisplayAlerts = False
        excel.AutomationSecurity = 3
        for source, definition, output in jobs:
            annotate(source, definition, output, excel=excel)
            print(f'作成しました: {output}')
    finally:
        if excel is not None:
            excel.Quit()
        pythoncom.CoUninitialize()


def main():
    """ジョブ一覧を受け取り、一括処理を実行する。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    args = parser.parse_args()
    run(args.manifest)


if __name__ == '__main__':
    main()
