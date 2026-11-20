# 修正履歴
# <YYYY/MM/DD>: <会社の略称><氏名>: 新規作成。単体テストを単体テスト仕様書ごとに流し、レポートを出す。
"""単体テストを単体テスト仕様書ごとに流し、仕様書ごとのレポートと、全体の結果をまとめた index.html を出す。

仕様書ごとのレポートには、その仕様書のケースを確かめるテストのファイルだけを流した結果が載る。
どの仕様書にも当たらないテストのファイルは、「仕様書に対応しないテスト」のレポートにまとめる。

使い方(サービスの直下で実行する):
    uv run python tests/unit_report.py            # 実行日は今日
    uv run python tests/unit_report.py 20261008   # 実行日を指定する

出力先: tests/output/report/unit/<実行日>/
"""

import datetime
import html
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from spec_report import NO_SPEC, SERVICE_NAME, spec_case_files, spec_name_of

# サービスの直下・単体テストの置き場所・レポートの出力先
SERVICE_DIR = Path(__file__).resolve().parents[1]
UNIT_TEST_DIR = SERVICE_DIR / "tests" / "unit"
REPORT_ROOT = SERVICE_DIR / "tests" / "output" / "report" / "unit"

# レポートの見た目(仕様書ごとのレポートと同じ CSS)
CSS_PATH = SERVICE_DIR / "tests" / "report.css"

# 仕様書に対応しないテストのレポートの名前と、ファイル名
NO_SPEC_TITLE = "仕様書に対応しないテスト"
NO_SPEC_FILE = "no_spec.html"

# 仕様書の名前から読む ID の形(サービスの英字2文字 + 数字4桁。バッチは英字2文字 + B + 数字4桁)。
# 例：AB0101、ABB0101。プロジェクトの ID の付け方に合わせて直す
_SPEC_ID_PATTERN = r"(?:^|_)([A-Z]{2}B?\d{4})_"

# 結果の種類(表に出す順)
OUTCOMES = (
    ("passed", "成功"),
    ("failed", "失敗"),
    ("error", "エラー"),
    ("skipped", "スキップ"),
)


def _test_files_by_spec():
    """仕様書ごとに、そのケースを確かめるテストのファイルを返す。

    Returns:
        dict[str, list[Path]]: 仕様書の名前 → テストのファイル。
    """
    paths_by_name = {path.name: path for path in UNIT_TEST_DIR.rglob("test_*.py")}
    files_by_spec = {}
    for case_file in spec_case_files():
        names = {
            row["テストコード"].partition("::")[0]
            for sheet, rows in json.loads(case_file.read_text(encoding="utf-8")).items()
            if sheet.endswith("_クラス単体")
            for row in rows
            if row.get("テストコード")
        }
        # 存在しないファイルのケースも、仕様書との突き合わせで不足として表示する。
        files_by_spec[spec_name_of(case_file)] = sorted(
            paths_by_name[name] for name in names if name in paths_by_name
        )
    return files_by_spec


def _report_file(spec_name):
    """仕様書ごとのレポートのファイル名(<API ID>.html)を返す。

    pytest-html のレポートは、表を描く前に URL を unescape して書き換えるため、
    日本語や括弧を含むファイル名を file:// で開くと、書き換えが拒まれて行が表示されない。
    そのため、ファイル名は英数字だけにする。
    """
    # 仕様書の名前から、API ID を読む。ID の付け方は、プロジェクトの決まりに合わせて _SPEC_ID_PATTERN を直す
    match = re.search(_SPEC_ID_PATTERN, spec_name)
    if match is None:
        raise SystemExit(f"{spec_name} から API ID を読み取れません")
    return f"{match.group(1)}.html"


def _run(title, report_name, files, spec_name, out_dir, work_dir):
    """テストのファイルを流して、レポートを出し、結果を返す。

    Args:
        title: レポートの名前(index.html に出す)。
        report_name: レポートのファイル名。英数字だけにする。
        files: 流すテストのファイル。
        spec_name: レポートに載せる仕様書の名前(NO_SPEC はどれも載せない)。
        out_dir: レポートの出力先。
        work_dir: 結果の JSON を一時的に置く場所。

    Returns:
        dict: レポートのファイル名・結果(outcomes・counts・missing・unknown)。
    """
    summary_path = Path(work_dir) / f"{len(list(Path(work_dir).iterdir()))}.json"
    print(f"--- {title}", flush=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *(
                [str(path.relative_to(SERVICE_DIR)) for path in files]
                if files
                else [str(UNIT_TEST_DIR), "-k", "__spec_without_test__"]
            ),
            f"--html={out_dir / report_name}",
            "--self-contained-html",
            f"--spec-name={spec_name}",
            f"--spec-summary={summary_path}",
        ],
        cwd=SERVICE_DIR,
        check=False,
    )
    if not summary_path.exists():
        raise SystemExit(
            f"{title} のテストを流せませんでした（上のエラーを確かめてください）"
        )

    return {
        "title": title,
        "report": report_name,
        **json.loads(summary_path.read_text(encoding="utf-8")),
    }


def _judge(counts):
    """テスト結果を判定する。すべてのテストが通った(失敗・エラー・スキップが無い)ときだけ合格とする。"""
    if any(counts.get(key, 0) for key in ("failed", "error", "skipped")):
        return '<span class="failed">不合格</span>'
    return '<span class="passed">合格</span>'


def _check_spec(missing, unknown):
    """仕様書との突き合わせを判定する。

    仕様書にあるのにテストが無いケース(不足)があれば NG、仕様書に無いテスト(追加)だけなら警告とする。
    テスト結果の合否には入れない。
    """
    if missing:
        return '<span class="failed">NG</span>'
    if unknown:
        return '<span class="skipped">警告</span>'
    return '<span class="passed">OK</span>'


def _row(cells):
    """表の行(HTML)を作る。"""
    return "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"


def _details(results):
    """仕様書との突き合わせで NG・警告になった中身(HTML)を、仕様書ごとに作る。"""
    blocks = []
    for result in results:
        items = [
            f"NG：仕様書にあるのに、テストが無いケース {item}"
            for item in result["missing"]
        ]
        items += [f"警告：仕様書に無いテスト {item}" for item in result["unknown"]]
        if items:
            lines = "".join(f"<li>{html.escape(item)}</li>" for item in items)
            blocks.append(f"<h3>{html.escape(result['title'])}</h3><ul>{lines}</ul>")
    return "".join(blocks) or "<p>なし</p>"


def _write_index(out_dir, results, started_at):
    """全体の結果と、仕様書ごとのレポートへのリンクを載せた index.html を出す。

    全体の件数は、同じテストを複数の仕様書で流しても1件として数える。
    """
    headers = [
        "テスト結果",
        "テスト件数",
        *[label for _, label in OUTCOMES],
        "仕様書との突き合わせ",
        "仕様書にあるのに、テストが無いケース（NG）",
        "仕様書に無いテスト（警告）",
    ]

    # 全体の結果
    outcomes = {}
    for result in results:
        outcomes.update(result["outcomes"])
    counts = Counter(outcomes.values())
    missing = [item for result in results for item in result["missing"]]
    unknown = [item for result in results for item in result["unknown"]]
    total_row = _row(
        [
            _judge(counts),
            len(outcomes),
            *[counts.get(key, 0) for key, _ in OUTCOMES],
            _check_spec(missing, unknown),
            len(missing),
            len(unknown),
        ]
    )

    # 仕様書ごとの結果
    spec_rows = "".join(
        _row(
            [
                f'<a href="{quote(result["report"])}">{html.escape(result["title"])}</a>',
                _judge(result["counts"]),
                len(result["outcomes"]),
                *[result["counts"].get(key, 0) for key, _ in OUTCOMES],
                _check_spec(result["missing"], result["unknown"]),
                len(result["missing"]),
                len(result["unknown"]),
            ]
        )
        for result in results
    )

    header_cells = "".join(f"<th>{html.escape(text)}</th>" for text in headers)
    css = CSS_PATH.read_text(encoding="utf-8")
    page = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>単体テストのレポート（{SERVICE_NAME}）</title>
<style>
{css}
.index-table {{ border-collapse: collapse; margin-bottom: 24px; font-size: 14px; }}
.index-table th, .index-table td {{ border: 1px solid #cccccc; padding: 8px 12px; text-align: left; }}
.index-table th {{ background-color: #f2f2f2; white-space: nowrap; }}
</style>
</head>
<body>
<h1>単体テストのレポート（{SERVICE_NAME}）</h1>
<p>実行日時：{started_at:%Y-%m-%d %H:%M:%S}</p>
<p>テスト結果は、すべてのテストが通った（失敗・エラー・スキップが無い）ときに合格になる。<br>
仕様書との突き合わせは、テスト結果とは別に判定する。仕様書にあるのにテストが無いケースがあれば NG、仕様書に無いテストだけなら警告になる。</p>
<h2>全体の結果</h2>
<table class="index-table">
<thead><tr>{header_cells}</tr></thead>
<tbody>{total_row}</tbody>
</table>
<h2>単体テスト仕様書ごとの結果</h2>
<table class="index-table">
<thead><tr><th>単体テスト仕様書</th>{header_cells}</tr></thead>
<tbody>{spec_rows}</tbody>
</table>
<h2>仕様書との突き合わせの NG・警告</h2>
{_details(results)}
</body>
</html>
"""
    (out_dir / "index.html").write_text(page, encoding="utf-8", newline="\n")


def main():
    """仕様書ごとにテストを流し、レポートと index.html を出す。"""
    started_at = datetime.datetime.now()
    run_date = sys.argv[1] if len(sys.argv) > 1 else f"{started_at:%Y%m%d}"
    out_dir = REPORT_ROOT / run_date
    out_dir.mkdir(parents=True, exist_ok=True)

    files_by_spec = _test_files_by_spec()
    covered = {path for files in files_by_spec.values() for path in files}
    uncovered = sorted(
        path for path in UNIT_TEST_DIR.rglob("test_*.py") if path not in covered
    )

    with tempfile.TemporaryDirectory() as work_dir:
        # 仕様書ごとのレポート
        results = [
            _run(name, _report_file(name), files, name, out_dir, work_dir)
            for name, files in files_by_spec.items()
        ]

        # 仕様書に対応しないテストのレポート
        if uncovered:
            results.append(
                _run(NO_SPEC_TITLE, NO_SPEC_FILE, uncovered, NO_SPEC, out_dir, work_dir)
            )

    _write_index(out_dir, results, started_at)
    print(f"レポート：{out_dir / 'index.html'}")

    # 失敗・エラーがあれば、終了コードで知らせる
    failed = any(
        result["counts"].get(key, 0)
        for result in results
        for key in ("failed", "error")
    )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
