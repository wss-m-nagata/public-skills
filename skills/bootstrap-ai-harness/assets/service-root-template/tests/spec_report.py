# 修正履歴
# <YYYY/MM/DD>: <会社の略称><氏名>: 新規作成。単体テストのレポートに、単体テスト仕様書の内容を載せる。
"""単体テストのレポート(pytest-html)に、単体テスト仕様書の内容を載せる。

単体テスト仕様書(docs/40_spec/unit-test/)のケース一覧(JSON)を読み、
仕様書の「テストコード」の列とテストの名前(<ファイル名>::<関数名>)を突き合わせて、
レポートの各行に、ケースNo・分類・観点・テスト内容・想定結果・対応箇所を出す。
あわせて、レポートの概要に、仕様書にあるのにテストが無いケースと、仕様書に無いテストを出す。

レポートを出すとき(--html を付けたとき)だけ、conftest.py から登録する。
仕様書ごとのレポートは、tests/unit_report.py が --spec-name で仕様書を1つに絞って出す。
"""

import html
import json
import re
from collections import Counter
from pathlib import Path

import pytest

# サービスの名前(レポートの題名に出す)
SERVICE_NAME = Path(__file__).resolve().parents[1].name

# 単体テスト仕様書を置く場所と、ケース一覧(build_unit_test_spec.py の --cases-json で出したもの)のファイル名の終わり
SPEC_DIR = Path(__file__).resolve().parents[1] / "docs" / "40_spec" / "unit-test"
CASE_LIST_SUFFIX = "_ケース一覧.json"

# pytest で確かめるケースが書かれているシート(クラス単体)の名前の終わり
CLASS_SHEET_SUFFIX = "_クラス単体"

# --spec-name に渡すと、どの仕様書のケースも載せない(仕様書に対応しないテストのレポートにする)値
NO_SPEC = "-"

# レポートに足す列(見出し, 見た目用のクラス, ケースから値を作る関数)
_COLUMNS = (
    ("ケースNo", "col-spec-no", lambda c: c["ケースNo"]),
    (
        "分類・観点",
        "col-spec-viewpoint",
        lambda c: " / ".join(c["分類"]) + "\n" + c["観点"],
    ),
    ("テスト内容", "col-spec-content", lambda c: c.get("テスト内容", "")),
    ("想定結果", "col-spec-expected", lambda c: c.get("想定結果", "")),
    (
        "対応箇所",
        "col-spec-place",
        lambda c: " ".join(v for v in (c.get("対応設計書"), c.get("対応箇所")) if v),
    ),
)


def _test_key(nodeid):
    """テストの名前を、仕様書の「テストコード」と同じ形(<ファイル名>::<関数名>)にする。

    パラメータ付きのテスト(test_x[値])は、パラメータを外して1つのケースに当てる。
    """
    path, _, name = nodeid.partition("::")
    return f"{Path(path).name}::{re.sub(r'\[.*\]$', '', name)}"


def spec_case_files():
    """pytest で確かめる仕様書のケース一覧(JSON)のファイルを、名前の順に返す。

    Node.js（Vitest）で確かめる仕様書（テストコードが .py のファイルでないもの）は、同じフォルダにあっても返さない。

    Returns:
        list[Path]: ケース一覧のファイル。
    """
    return sorted(
        path for path in SPEC_DIR.rglob(f"*{CASE_LIST_SUFFIX}") if _is_pytest_spec(path)
    )


def _is_pytest_spec(path):
    """クラス単体シートのPython用または未記入のケースを持つ仕様書を返す。"""
    return any(
        not row.get("テストコード")
        or row["テストコード"].partition("::")[0].endswith(".py")
        for sheet, rows in json.loads(path.read_text(encoding="utf-8")).items()
        if sheet.endswith(CLASS_SHEET_SUFFIX)
        for row in rows
        if row.get("テスト内容")
    )


def spec_name_of(path):
    """ケース一覧のファイルから、仕様書の名前(Excel のファイル名から拡張子を除いたもの)を返す。"""
    return path.name.removesuffix(CASE_LIST_SUFFIX)


def load_cases(only_spec=None):
    """仕様書のケース一覧を読み、テストで確かめるケース(クラス単体のシートのケース)を返す。

    Args:
        only_spec: 読む仕様書の名前。None はすべての仕様書、NO_SPEC はどの仕様書も読まない。

    Returns:
        list[dict]: ケースの一覧。各ケースに「仕様書」(ファイル名)と「シート」を足したもの。
    """
    cases = []
    for path in spec_case_files():
        spec_name = spec_name_of(path)
        if only_spec is not None and spec_name != only_spec:
            continue
        for sheet, rows in json.loads(path.read_text(encoding="utf-8")).items():
            if not sheet.endswith(CLASS_SHEET_SUFFIX):
                continue
            for row in rows:
                # 対象外のケースは、テストが無くてよい
                if row.get("テスト内容"):
                    cases.append({**row, "仕様書": spec_name, "シート": sheet})
    return cases


def _cell(text, css_class):
    """レポートの表のセル(HTML)にする。改行は改行のまま見えるようにする。"""
    return (
        f'<td class="{css_class}">'
        + html.escape(str(text)).replace("\n", "<br>")
        + "</td>"
    )


def _test_name_cell(nodeid):
    """Test 列のセル(HTML)を作る。1行目にテストファイル名、2行目にテストのメソッド名を出す。

    メソッド名には、クラス名とパラメータを含める。
    pytest はパラメータの日本語を \\uXXXX の形で出すため、元の文字に戻す。
    """
    path, _, name = nodeid.partition("::")
    name = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), name)
    return _cell(f"{Path(path).name}\n{name}", "col-testId")


def _listing(title, items):
    """レポートの概要に出す一覧(HTML)を作る。"""
    lines = (
        "".join(f"<li>{html.escape(item)}</li>" for item in items) or "<li>なし</li>"
    )
    return f"<p><strong>{html.escape(title)}（{len(items)}件）</strong></p><ul>{lines}</ul>"


class SpecReportPlugin:
    """単体テスト仕様書の内容を、pytest-html のレポートに載せるプラグイン。"""

    def __init__(self, spec_name=None, summary_path=None):
        """
        Args:
            spec_name: 載せる仕様書の名前。None はすべての仕様書、NO_SPEC はどの仕様書も載せない。
            summary_path: 結果の件数と食い違いを書き出す JSON のパス。None は書き出さない。
        """
        self._spec_name = spec_name
        self._summary_path = summary_path
        # テストコード → ケースの一覧(同じテストで複数のケースを確かめる場合がある)
        self._cases_by_code = {}
        for case in load_cases(spec_name):
            self._cases_by_code.setdefault(case.get("テストコード", ""), []).append(
                case
            )
        # 実行したテストの名前(<ファイル名>::<関数名>)
        self._executed = set()
        # テストの nodeid → 結果(passed・failed・skipped・error)
        self._outcomes = {}

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        """テストの結果に、当てはまる仕様書のケースを付ける。"""
        outcome = yield
        report = outcome.get_result()
        key = _test_key(item.nodeid)
        self._executed.add(key)
        report.spec_cases = self._cases_by_code.get(key, [])

        # 結果の記録(準備・後始末の失敗は error、本体は passed・failed、どこかで飛ばしたら skipped)
        if report.when == "call" or report.outcome != "passed":
            if report.outcome == "failed" and report.when != "call":
                outcome = "error"
            else:
                outcome = report.outcome
            self._outcomes.setdefault(item.nodeid, outcome)

    def pytest_html_report_title(self, report):
        """レポートの題名を付ける。"""
        report.title = f"単体テストのレポート（{SERVICE_NAME}）"
        if self._spec_name == NO_SPEC:
            report.title += " 仕様書に対応しないテスト"
        elif self._spec_name is not None:
            report.title += " " + self._spec_name

    def pytest_html_results_table_header(self, cells):
        """レポートの表に、仕様書の列の見出しを足す(テストの名前の後ろ)。"""
        for offset, (title, css_class, _) in enumerate(_COLUMNS):
            cells.insert(
                2 + offset, f'<th class="{css_class}">{html.escape(title)}</th>'
            )

    def pytest_html_results_table_row(self, report, cells):
        """レポートの表の各行に、仕様書のケースの内容を足す。Test 列は、ファイル名とメソッド名の2行にする。"""
        cases = getattr(report, "spec_cases", [])
        cells[1] = _test_name_cell(report.nodeid)
        for offset, (_, css_class, value_of) in enumerate(_COLUMNS):
            # 1つのテストで複数のケースを確かめる場合は、改行して並べる
            text = (
                "\n".join(str(value_of(case)) for case in cases)
                if cases
                else "（仕様書に無い）"
            )
            cells.insert(2 + offset, _cell(text, css_class))

    def _mismatch(self):
        """仕様書とテストの食い違いを返す。

        Returns:
            tuple[list[str], list[str]]: 仕様書にあるのにテストが無いケースと、仕様書に無いテスト。
        """
        missing = [
            f"{case['仕様書']} {case['シート']} {case['ケースNo']}：{case.get('テストコード') or '（テストコード未記入）'}"
            for cases in self._cases_by_code.values()
            for case in cases
            if case.get("テストコード", "") not in self._executed
        ]
        unknown = sorted(
            key for key in self._executed if key not in self._cases_by_code
        )
        return missing, unknown

    def pytest_html_results_summary(self, prefix, summary, postfix, session):
        """レポートの概要に、仕様書とテストの食い違いを出す。"""
        missing, unknown = self._mismatch()
        postfix.append(_listing("NG：仕様書にあるのに、テストが無いケース", missing))
        postfix.append(_listing("警告：仕様書に無いテスト", unknown))

    def pytest_sessionfinish(self, session):
        """結果の件数と食い違いを、JSON に書き出す(tests/unit_report.py が index.html を作るのに使う)。"""
        if self._summary_path is None:
            return

        missing, unknown = self._mismatch()
        summary = {
            "outcomes": self._outcomes,
            "counts": dict(Counter(self._outcomes.values())),
            "missing": missing,
            "unknown": unknown,
        }
        Path(self._summary_path).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
