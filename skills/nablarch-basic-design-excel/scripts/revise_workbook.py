# -*- coding: utf-8 -*-
"""
既存の設計書（Excel）の版を上げる一連の流れを、仕様JSON1つで行う。

【背景】既存の設計書を直すときは、次の手順を順に行う。
同じ変更を、値・赤字にするセル・変更履歴のセル一覧の3か所に別々に書くと、ずれたり、書き漏れたりする。
このスクリプトは、変更の中身を、仕様JSONの mapping と groups の2か所に書けば済むようにする。

やること（既存のスクリプトを、この順に呼ぶ）:
  1. mark_changed_cells.py --reset-all   前の版の赤字を、黒に戻す
  2. pre_steps                            構造を変える操作（行の挿入・特記事項の行の追加）
  3. apply_mapping.py --emit-changed      値を反映し、値が変わったセルの一覧を得る
  4. fit_row_heights.py                   行の高さを調整する（fit の指定どおり）
  5. groups と、変わったセルを突き合わせる
       - どの groups にも属さない、変わったセルがあれば、エラーで止まる（変更履歴の書き漏れを防ぐ）
       - groups の cells は、変わったセルとの積に絞る（範囲に、変わっていないセルがあっても警告しない）
  6. mark_changed_cells.py                変わったセルを、赤字にする
  7. normalize_change_history.py → add_change_history.py
                                           変更履歴に、新しい版の行を書く（表紙の版数も合わせる）
  8. verify_layout.py                     構造の検証（構造を変える操作の直後の版と比べる）

使い方:
    python revise_workbook.py <仕様JSON>

    出力：仕様JSONの output（xlsx）。work_dir に、中間のファイルと、次の2つを残す。
      - changed.json … 値が変わったセル（{"シート名": ["セル", ...]}）
      - history.json … add_change_history.py に渡した変更履歴JSON
    source は変更しない。仕様JSONを直して、何度でも流し直せる。

仕様JSONの形:
{
  "source": "取得した写しのxlsx",
  "output": "出力のxlsx（source と同じパスは不可）",
  "work_dir": "中間ファイルの置き場",
  "pre_steps": [                                  // 構造を変える操作（省略可。上から順に実行）
    {"op": "insert_rows", "sheet": "シート名", "at_row": 24, "count": 9, "style_row": 23},
    {"op": "extend_remarks", "count": 3, "sheet": "1. 外部インタフェース仕様"}   // sheet は省略可
  ],
  "mapping": {"sheets": {"シート名": {"セル": "値"}}},   // または "mapping_file": "mapping.json"
  "fit": [                                        // 行の高さの調整（省略可）
    {"sheet_prefix": "3.", "rows": ["10-32"], "only_merged": true, "line_height": 15, "shrink": true}
    // sheet / sheet_prefix / body_sheets のどれか、rows、only_merged、line_height、shrink、until_text
  ],
  "history": {"version": "第2.0版", "date": "YYYY-MM-DD", "kind": "変更", "author": "担当者", "summary": "対応内容を1行で"},
  "strict": true,                                 // 省略時 true。変更履歴の突き合わせの警告で止める
  "groups": [                                     // 変更のまとまり。変更履歴と、変更箇所一覧（draft_change_list.py）の元
    {
      "sheet": "シート名",
      "place": "特記事項（E39〜E41）",              // 変更箇所と、変更内容の見出し
      "cells": ["E39:E41"],                       // 範囲でよい。変わったセルとの積になる
      "cleared": true,                            // 省略可。セルを空にしただけ（値が変わったセルが無い）のまとまりのときに書く。警告が出なくなる
      "type": "追加",                             // 追加・変更・削除
      "text": "変更前：…　変更後：…",
      "confirm": "要確認",                        // 省略時「任意」（draft_change_list.py が使う）
      "before": "…", "after": "…"                 // 省略可（draft_change_list.py が使う）
    }
  ]
}

終了コード:
    0 = 正常終了
    1 = 入力が正しくない／どれかの手順が失敗した／groups に属さない変更がある／構造の検証でNG
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS))
from add_change_history import _expand  # noqa: E402
from xlsx_common import ensure_utf8_stdio  # noqa: E402

# mark_changed_cells.py に、一度に渡すセルの数（コマンドラインの長さの上限を避ける）
MARK_CHUNK = 150
# 変更履歴・表紙は、add_change_history.py が書くため、mapping では書かない
HISTORY_SHEETS = ("変更履歴", "表紙")


class StepError(Exception):
    """手順の失敗。"""


def _run(script, *args):
    """既存のスクリプトを実行し、標準出力を返す。失敗したときは StepError にする。

    Args:
        script (str): scripts/ の中のスクリプトのファイル名。
        *args: スクリプトに渡す引数。

    Returns:
        str: 標準出力。
    """
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *[str(a) for a in args]],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if result.returncode != 0:
        tail = (result.stdout + result.stderr).strip().splitlines()[-12:]
        raise StepError(
            f"{script} が失敗しました（終了コード {result.returncode}）:\n  "
            + "\n  ".join(tail)
        )
    return result.stdout


def _load_mapping(spec):
    """仕様JSONから、マッピング（{"sheets": {...}}）を取り出す。

    Args:
        spec (dict): 仕様JSON。

    Returns:
        dict: {"sheets": {シート名: {セル: 値}}}。
    """
    if "mapping_file" in spec:
        mapping = json.loads(Path(spec["mapping_file"]).read_text(encoding="utf-8"))
    else:
        mapping = spec.get("mapping", {})
    return mapping if "sheets" in mapping else {"sheets": mapping}


def _check_spec(spec):
    """仕様JSONの、必須の項目と、組み合わせを確かめる。

    Args:
        spec (dict): 仕様JSON。

    Raises:
        StepError: 入力が正しくないとき。
    """
    for key in ("source", "output", "work_dir", "history", "groups"):
        if key not in spec:
            raise StepError(f"仕様JSONに「{key}」がありません。")
    if Path(spec["source"]).resolve() == Path(spec["output"]).resolve():
        raise StepError(
            "source と output は、別のパスにしてください（元の写しを上書きしないため）。"
        )
    # 出力先が、Excel などで開かれていると、書き込めずに途中で止まる。先に、わかりやすく知らせる
    output = Path(spec["output"])
    opened = [
        lock.name
        for lock in output.parent.glob("~$*")
        if output.name.startswith(lock.name[2:])
    ]
    if opened:
        raise StepError(
            f"出力先のファイルが、開かれています（ロックファイル {opened[0]} があります）: {output}"
            + chr(10)
            + "  Excel などで開いていれば、保存して閉じてから、もう一度実行してください。"
        )
    if output.exists():
        try:
            with open(output, "ab"):
                pass
        except PermissionError:
            raise StepError(
                f"出力先のファイルに、書き込めません（開かれているか、読み取り専用です）: {output}"
            )
    for key in ("version", "date", "kind", "author", "summary"):
        if key not in spec["history"]:
            raise StepError(f"history に「{key}」がありません。")
    for index, group in enumerate(spec["groups"], 1):
        for key in ("sheet", "cells", "type", "text"):
            if key not in group:
                raise StepError(f"groups の {index} 番目に「{key}」がありません。")


def _apply_pre_steps(spec, current, work):
    """構造を変える操作を、上から順に実行する。

    Args:
        spec (dict): 仕様JSON。
        current (Path): 入力のxlsx。
        work (Path): 中間ファイルの置き場。

    Returns:
        Path: 操作を終えたxlsx。
    """
    for index, step in enumerate(spec.get("pre_steps", []), 1):
        out = work / f"pre{index}.xlsx"
        op = step.get("op")
        if op == "insert_rows":
            _run(
                "insert_rows.py",
                current,
                step["sheet"],
                step["at_row"],
                step["count"],
                step["style_row"],
                out,
            )
        elif op == "extend_remarks":
            args = [current, out, "--count", step["count"]]
            if "sheet" in step:
                args += ["--sheet", step["sheet"]]
            _run("extend_remarks_rows.py", *args)
        else:
            raise StepError(
                f"pre_steps の {index} 番目の op「{op}」は、使えません（insert_rows・extend_remarks）。"
            )
        current = out
    return current


def _fit_args(fit):
    """fit の1件を、fit_row_heights.py の引数にする。

    Args:
        fit (dict): fit の1件。

    Returns:
        list: 引数。
    """
    args = []
    if "sheet" in fit:
        args += ["--sheet", fit["sheet"]]
    if "sheet_prefix" in fit:
        args += ["--sheet-prefix", fit["sheet_prefix"]]
    if fit.get("body_sheets"):
        args += ["--body-sheets"]
    for rows in fit["rows"]:
        args += ["--rows", rows]
    if fit.get("only_merged"):
        args += ["--only-merged"]
    if "line_height" in fit:
        args += ["--line-height", fit["line_height"]]
    if fit.get("shrink"):
        args += ["--shrink"]
    if "until_text" in fit:
        args += ["--until-text", fit["until_text"]]
    return args


def _assign_groups(spec, changed):
    """groups と、変わったセルを突き合わせ、groups ごとのセルを求める。

    Args:
        spec (dict): 仕様JSON。
        changed (dict): 値が変わったセル（{"シート名": ["セル", ...]}）。

    Returns:
        list[list[str]]: groups と同じ順の、groups ごとの（変わった）セル。

    Raises:
        StepError: どの groups にも属さない、変わったセルがあるとき。
    """
    remaining = {sheet: set(cells) for sheet, cells in changed.items()}
    per_group = []
    for group in spec["groups"]:
        wanted = _expand(group["cells"])
        hit = sorted(remaining.get(group["sheet"], set()) & wanted, key=_cell_order)
        # 変わったセルのうち、このgroupsの範囲にあるものを、このgroupsのものにする
        per_group.append(
            sorted(wanted & set(changed.get(group["sheet"], [])), key=_cell_order)
        )
        remaining.get(group["sheet"], set()).difference_update(hit)
        # セルを空にしただけの変更のまとまり（cleared: true）は、変わったセルが無くてよい（赤字にもできない）
        if not per_group[-1] and not group.get("cleared"):
            print(
                f"  ! 変わったセルが無い groups があります: {group['sheet']} {group.get('place', '')}"
            )

    orphans = {
        sheet: sorted(cells, key=_cell_order)
        for sheet, cells in remaining.items()
        if cells
    }
    if orphans:
        lines = [
            f"{sheet}: {', '.join(cells[:12])}{' ほか' if len(cells) > 12 else ''}"
            for sheet, cells in orphans.items()
        ]
        raise StepError(
            "どの groups にも属さない、変わったセルがあります（変更履歴の書き漏れ）:\n  "
            + "\n  ".join(lines)
        )
    return per_group


def _cell_order(coord):
    """セル座標を、行・列の順に並べるためのキー。

    Args:
        coord (str): セル座標（例：AB12）。

    Returns:
        tuple[int, int]: （行, 列の順位）。
    """
    letters = "".join(ch for ch in coord if ch.isalpha())
    row = int("".join(ch for ch in coord if ch.isdigit()))
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - 64)
    return (row, col)


def revise(spec):
    """仕様JSONのとおりに、設計書を改訂する。

    Args:
        spec (dict): 仕様JSON。

    Returns:
        dict: 出力のパスなどの、結果。
    """
    _check_spec(spec)
    work = Path(spec["work_dir"])
    work.mkdir(parents=True, exist_ok=True)

    # 1. 前の版の赤字を黒に戻す
    current = work / "step1_reset.xlsx"
    _run("mark_changed_cells.py", spec["source"], "--reset-all", "--output", current)

    # 2. 構造を変える操作（検証の基準は、この直後の版にする）
    current = _apply_pre_steps(spec, current, work)
    baseline = current

    # 3. 値の反映（値が変わったセルの一覧も得る）
    mapping_path = work / "mapping.json"
    mapping_path.write_text(
        json.dumps(_load_mapping(spec), ensure_ascii=False, indent=1), encoding="utf-8"
    )
    changed_path = work / "changed.json"
    applied = work / "step3_applied.xlsx"
    _run(
        "apply_mapping.py",
        current,
        mapping_path,
        applied,
        "--emit-changed",
        changed_path,
    )
    current = applied
    changed = (
        json.loads(changed_path.read_text(encoding="utf-8"))
        if changed_path.exists()
        else {}
    )
    for sheet in HISTORY_SHEETS:
        if sheet in changed:
            raise StepError(
                f"mapping に、{sheet}シートのセルがあります。{sheet}は、変更履歴の書き込みが行うため、mapping では書きません。"
            )

    # 4. 行の高さの調整
    for index, fit in enumerate(spec.get("fit", []), 1):
        out = work / f"step4_fit{index}.xlsx"
        _run("fit_row_heights.py", current, out, *_fit_args(fit))
        current = out

    # 5. groups と、変わったセルの突き合わせ
    per_group = _assign_groups(spec, changed)

    # 6. 変わったセルを赤字にする（シートごと）
    for index, (sheet, cells) in enumerate(changed.items(), 1):
        for chunk_index in range(0, len(cells), MARK_CHUNK):
            out = work / f"step6_red{index}_{chunk_index}.xlsx"
            _run(
                "mark_changed_cells.py",
                current,
                sheet,
                *cells[chunk_index : chunk_index + MARK_CHUNK],
                "--output",
                out,
            )
            current = out

    # 7. 変更履歴
    history = {
        **spec["history"],
        "changes": [
            {
                "sheet": g["sheet"],
                "place": g.get("place", ""),
                "cells": cells,
                "type": g["type"],
                "text": g["text"],
            }
            for g, cells in zip(spec["groups"], per_group)
        ],
    }
    history_path = work / "history.json"
    history_path.write_text(
        json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    normalized = work / "step7_normalized.xlsx"
    _run("normalize_change_history.py", current, normalized)
    final = work / "step7_history.xlsx"
    args = [normalized, history_path, final]
    if spec.get("strict", True):
        args.append("--strict")
    _run("add_change_history.py", *args)

    # 8. 構造の検証
    verify_args = [
        baseline,
        final,
        "--allow-font-colors",
        "--allow-history-row-heights",
    ]
    fits = spec.get("fit", [])
    if any(f.get("shrink") for f in fits):
        verify_args.append("--allow-row-height-changes")
    elif fits:
        verify_args.append("--allow-row-heights")
    verify_out = _run("verify_layout.py", *verify_args)

    output = Path(spec["output"])
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(final, output)
    return {
        "output": str(output),
        "changed": {sheet: len(cells) for sheet, cells in changed.items()},
        "changed_json": str(changed_path),
        "history_json": str(history_path),
        "verify": next(
            (line for line in verify_out.splitlines() if line.startswith(("OK", "NG"))),
            "",
        ),
    }


def main():
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("spec", help="仕様JSON")
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    try:
        result = revise(spec)
    except StepError as error:
        print(f"NG: {error}")
        sys.exit(1)

    print(f"OK: {result['output']}")
    print(f"  変わったセル: {result['changed']}")
    print(f"  構造の検証: {result['verify']}")
    print(f"  変更箇所の一覧: {result['changed_json']}")
    print(f"  変更履歴JSON: {result['history_json']}")


if __name__ == "__main__":
    main()
