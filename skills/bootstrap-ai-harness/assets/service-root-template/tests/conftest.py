# 修正履歴
# <YYYY/MM/DD>: <会社の略称><氏名>: 新規作成。単体テストのレポートに、単体テスト仕様書の内容を載せる設定。
"""単体テストに共通する設定。

既存の conftest.py があるときは、ここの関数を、既存のものに統合する。
"""

from pathlib import Path

import pytest


def pytest_addoption(parser):
    """仕様書との突き合わせに使うオプションを登録する。"""
    parser.addoption("--spec-name", default=None)
    parser.addoption("--spec-summary", default=None)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """レポートを生成するときだけ、仕様書のプラグインを登録する。"""
    if getattr(config.option, "htmlpath", None):
        from spec_report import SpecReportPlugin

        config.pluginmanager.register(
            SpecReportPlugin(
                config.getoption("--spec-name"), config.getoption("--spec-summary")
            ),
            "spec_report",
        )
        config.option.css.append(str(Path(__file__).parent / "report.css"))
