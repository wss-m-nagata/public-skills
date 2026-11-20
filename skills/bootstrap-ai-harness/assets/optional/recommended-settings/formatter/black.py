# Revision History
# <YYYY/MM/DD>: <会社の略称><氏名>: 新規作成。Blackで整形する。
"""AIが編集した `.py` を、Blackで整形する（PostToolUse フック）。

- ファイルから上に辿って、最初に見つかった `pyproject.toml` のディレクトリ（サービスのルート）で、`uv run black` を実行する。
- `pyproject.toml` に `black` がないサービスは、整形しない（警告だけを出す）。
- 起動する拡張子は、`.claude/settings.json` の `if` で決める。
"""

import shutil
from pathlib import Path

import _common


def _find_service_root(path: Path) -> Path | None:
    """ファイルから上に辿って、最初に見つかった `pyproject.toml` のディレクトリを返す。アプリのルートより上へは辿らない。"""
    for parent in path.parents:
        if (parent / "pyproject.toml").is_file():
            return parent
        if parent == _common.APP:
            break
    return None


def main() -> None:
    """編集されたファイルを、そのサービスのBlackで整形する。"""
    _common.setup_output()
    path = _common.read_target_path()
    if path is None:
        return

    service_root = _find_service_root(path)
    if service_root is None:
        return
    if "black" not in (service_root / "pyproject.toml").read_text(encoding="utf-8"):
        _common.warn_and_exit(f"{service_root.name} の pyproject.toml に black がないため、整形しませんでした（uv add --dev black で追加します）")

    uv = shutil.which("uv")
    if uv is None:
        _common.warn_and_exit("uv が見つからないため、Blackで整形しませんでした")
    code, output = _common.run([uv, "run", "black", "-q", str(path)], service_root)
    if code != 0:
        _common.fail(f"Blackで整形できませんでした（構文エラーの可能性があります）:\n{output}")


if __name__ == "__main__":
    main()
