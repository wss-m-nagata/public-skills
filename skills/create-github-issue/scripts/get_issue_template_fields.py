#!/usr/bin/env python3
"""Issue テンプレート（.github/ISSUE_TEMPLATE/*.yml）の一覧と、項目の一覧を出すスクリプト。

どの種別があるか、各種別でどの項目を聞くかを、SKILL.md の記述ではなく、
実際のテンプレートから取る。テンプレートが変わっても、手順が古いままにならない。

テンプレートは、.github/ISSUE_TEMPLATE/ の *.yml と *.yaml を自動で拾う（config.yml は除く）。
PyYAML が必要である（無いときは、導入のしかたを表示して終わる）。

使い方:
    python get_issue_template_fields.py --list
    python get_issue_template_fields.py <種別>
    python get_issue_template_fields.py <種別> --dir path/to/ISSUE_TEMPLATE

種別は、テンプレートのファイル名（拡張子なし）、またはテンプレートの name で指定する
（大文字小文字は区別しない）。

--list の出力 JSON:
    templates[]:
        type                    ファイル名（拡張子なし）
        name                    テンプレートの name
        description             テンプレートの description
        title_prefix            テンプレートの title（タイトルの接頭辞）
        labels                  テンプレートの labels
        suggested_branch_prefix 既定の規則で作るブランチ接頭辞
                                （種別か name に bug・fix・不具合を含めば fix/、それ以外は feature/）

種別を指定したときの出力 JSON:
    type / name / template_path / title_prefix / labels / suggested_branch_prefix
    fields[]: id / type / label / description / options / required
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Windows のコンソールは UTF-8 以外のことがあり、日本語の出力が化けるため、UTF-8 に切り替える。
for _stream in (sys.stdout, sys.stderr):
    if _stream.encoding is None or _stream.encoding.lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8")


def _fail(message):
    """メッセージを標準エラーに出して、終了コード 1 で終わる。"""
    print(message, file=sys.stderr)
    sys.exit(1)


def _load_yaml_module():
    """PyYAML を読み込む。無いときは、導入のしかたを示して終わる。"""
    try:
        import yaml
    except ImportError:
        _fail(
            "PyYAML が入っていない。`pip install pyyaml`（または `py -m pip install pyyaml`）で入れてから、もう一度実行すること。"
        )
    return yaml


def _find_template_dir(start):
    """今のディレクトリから親方向にたどり、.github/ISSUE_TEMPLATE を探す。"""
    current = Path(start).resolve()
    for candidate in [current, *current.parents]:
        path = candidate / ".github" / "ISSUE_TEMPLATE"
        if path.is_dir():
            return path
    return None


def _branch_prefix(type_name, name):
    """種別と name から、既定の規則でブランチ接頭辞を作る。"""
    if re.search(r"bug|fix|不具合", f"{type_name} {name}", re.IGNORECASE):
        return "fix/"
    return "feature/"


def _load_templates(template_dir):
    """テンプレートのファイルをすべて読み、(ファイル名の語幹, パス, 中身) のリストを返す。"""
    yaml = _load_yaml_module()
    templates = []
    for path in sorted(
        list(template_dir.glob("*.yml")) + list(template_dir.glob("*.yaml"))
    ):
        if path.stem.lower() == "config":
            continue
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict) and "body" in data:
            templates.append((path.stem, path, data))
    return templates


def _summary(stem, data):
    """テンプレート1つぶんの、一覧用の情報を作る。"""
    name = data.get("name") or ""
    return {
        "type": stem,
        "name": name,
        "description": data.get("description") or "",
        "title_prefix": data.get("title") or "",
        "labels": data.get("labels") or [],
        "suggested_branch_prefix": _branch_prefix(stem, name),
    }


def list_templates(template_dir):
    """テンプレートの一覧を返す。"""
    return {
        "template_dir": str(template_dir),
        "templates": [
            _summary(stem, data) for stem, _path, data in _load_templates(template_dir)
        ],
    }


def extract_fields(template_dir, wanted):
    """種別（ファイル名または name）に合うテンプレートの、項目の一覧を返す。"""
    templates = _load_templates(template_dir)

    # ファイル名の一致を先に、次に name の一致を探す。
    key = wanted.strip().lower()
    match = next((t for t in templates if t[0].lower() == key), None)
    if match is None:
        match = next(
            (
                t
                for t in templates
                if str(t[2].get("name") or "").strip().lower() == key
            ),
            None,
        )
    if match is None:
        available = ", ".join(t[0] for t in templates) or "（テンプレートなし）"
        _fail(f"種別 '{wanted}' に合うテンプレートが無い。使える種別: {available}")

    stem, path, data = match

    # body の各項目から、ヒアリングに要る情報だけを取り出す（markdown の説明文は、項目に数えない）。
    fields = []
    for item in data.get("body", []):
        if item.get("type") == "markdown":
            continue
        attributes = item.get("attributes", {}) or {}
        fields.append(
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "label": attributes.get("label"),
                "description": attributes.get("description"),
                "options": attributes.get("options"),
                "required": (item.get("validations") or {}).get("required", False),
            }
        )

    result = _summary(stem, data)
    result["template_path"] = str(path)
    result["fields"] = fields
    return result


def main():
    """引数を読み、一覧または項目の一覧を JSON で出力する。"""
    parser = argparse.ArgumentParser(
        description="Issue テンプレートの一覧と項目を出す。"
    )
    parser.add_argument(
        "type",
        nargs="?",
        help="種別（ファイル名（拡張子なし）またはテンプレートの name）",
    )
    parser.add_argument("--list", action="store_true", help="テンプレートの一覧を出す")
    parser.add_argument(
        "--dir",
        help="テンプレートのディレクトリ（省略時は、今のディレクトリから親方向に探す）",
    )
    args = parser.parse_args()

    if args.list == bool(args.type):
        parser.error("--list か、種別のどちらか一方を指定すること。")

    # テンプレートのディレクトリを決める。
    template_dir = Path(args.dir) if args.dir else _find_template_dir(Path.cwd())
    if template_dir is None or not template_dir.is_dir():
        _fail(
            "テンプレートのディレクトリ（.github/ISSUE_TEMPLATE）が見つからない。--dir で指定すること。"
        )

    result = (
        list_templates(template_dir)
        if args.list
        else extract_fields(template_dir, args.type)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
