# -*- coding: utf-8 -*-
r"""レビュー用の置き場へ上げるスクリプトと、正本へ反映するスクリプトを、作業フォルダに出力する。

使い方:
    python make_scripts.py <仕様JSON> --folder <手元の作業フォルダ> [--only upload|reflect]

場所（設計書のルート・正本・レビュー用の置き場）は、設定ファイル
（.agents/config/design-doc-revision/settings.md）から読む。

仕様JSON（assets/examples/scripts.example.json を参照）:
    folder_name : レビュー用の置き場の、今回のフォルダ名
    suffix      : 上げるスクリプトの名前の後ろ（アップ_レビュー用置き場_<suffix>）
    upload      : 置き場へ上げる資料（作業フォルダからの相対パス）。確認資料は、「作成中」を外した名前で書く
    allow_in_progress : 名前に「作成中」を含んでいても、上げてよい資料（upload に書いたもののうち）。省略時は、無し。
                    レビュー中の確認資料を、作成中の名前のまま上げ直すときに、ユーザーの指示で書く
    move_scope  : 上げるときに、置き場の既存のファイルを old\ へ移す範囲（省略時は all）
                    all      … 置き場にある .xlsx・.drawio のすべて（置き場の資料を、すべて作り直すとき）。
                               今回上げない資料も old\ へ移され、置き場から無くなる（ドライランで警告が出る）
                    uploaded … 今回上げる資料と同じ場所・名前のものだけ（一部だけを直すとき。ほかの資料は、そのまま残る）
    server_root : 置き場の親フォルダ（設計書のルートからの相対パス）。省略時は、設定の「レビュー用の置き場の場所」。
                  段階（区分）を使い、作業フォルダそのものが設計書の置き場のときに書く
    reflect     : 正本へ反映する設計書 [{path, root, local, new, base_file, sha256}]。省略可（省略したときは、反映のスクリプトを作らない）
                  path は、反映先（root）の中の相対パス。root は、反映先のフォルダ（設計書のルートからの相対パス。省略時は、設定の「正本の場所」）。
                  local は、置き場・手元の中の相対パス（省略時は、path から決める）。new が true なら、反映先に新しく置く（元の版が無い）。
                  元の版の SHA-256 は、sha256 か、base_file（元の版の写しのファイル）か、取得の記録ファイルのどれかで渡す。
                  reflect_name を書くと、反映のスクリプトの名前（既定：正本反映）を変えられる
                  変更箇所一覧・確認資料は、反映しない（ここに書かない）

出力（作業フォルダの直下）:
    アップ_レビュー用置き場_<suffix>.ps1 / .bat   … 置き場へ上げる。ドライランのあと、確認して実行する
    正本反映.ps1 / .bat                           … レビュー担当者の合意のあと、正本へ反映する

反映のスクリプトが、「正本のファイルが、修正の元にした版のままか」を確かめるのに使う SHA-256 は、
sha256・base_file、または fetch_from_source.py が残した取得の記録ファイルから取る（new が true のものは要らない）。
スクリプトを作るだけで、実行はしない（ファイルサーバーに触れない）。実行は、ユーザーが行う。
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import SKILL_DIR, ensure_utf8, load_config, local_relative, sha256  # noqa: E402

TEMPLATES = SKILL_DIR / "assets" / "templates"


def write_ps1(path, text):
    """UTF-8（BOMあり）・CRLF で書く（Windows PowerShell 5.1 が日本語を読めるように）。"""
    Path(path).write_bytes(
        b"\xef\xbb\xbf"
        + text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
    )


def write_bat(path, text):
    """Shift-JIS・CRLF で書く（cmd が日本語を読めるように）。"""
    Path(path).write_bytes(
        text.replace("\r\n", "\n").replace("\n", "\r\n").encode("cp932")
    )


def fill(template, values):
    for k, v in values.items():
        template = template.replace("{{" + k + "}}", v)
    # 埋まっていない欄（{{名前}}）が残っていないか
    left = re.findall(r"\{\{[A-Z_]+\}\}", template)
    assert not left, f"埋まっていない欄: {left}"
    return template


def main():
    ensure_utf8()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("spec")
    ap.add_argument("--folder", required=True)
    ap.add_argument("--only", choices=["all", "upload", "reflect"], default="all",
                    help="作るスクリプトを絞る（置き場へ上げる upload／正本へ反映する reflect）。既存のスクリプトを上書きしないために使う")
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    folder = Path(args.folder)
    cfg = load_config(folder)
    record_path = folder / cfg["record_file"]
    record = (
        json.loads(record_path.read_text(encoding="utf-8"))
        if record_path.exists()
        else {}
    )
    name = spec["folder_name"]
    up_ps1 = f'アップ_レビュー用置き場_{spec["suffix"]}'
    # server_root があるときは、サーバー側の基準を design_root にし、フォルダ名に server_root を含める
    # （server_root のフォルダが、まだ無くても、実行のときに作れるようにする）
    if spec.get("server_root"):
        server_root_path = str(Path(cfg["design_root"]))
        server_name = spec["server_root"].replace("/", chr(92)) + chr(92) + name
    else:
        server_root_path = str(Path(cfg["design_root"]) / cfg["review_dir"])
        server_name = name
    bs = lambda s: s.replace("/", chr(92))  # noqa: E731
    bat = (TEMPLATES / "run.bat.tmpl").read_text(encoding="utf-8")

    reflect_items = spec.get("reflect", [])
    do_reflect = args.only in ("all", "reflect") and bool(reflect_items)
    if args.only == "reflect" and not reflect_items:
        print("仕様JSONに reflect が無いため、何も作りませんでした。")
        sys.exit(1)

    reflect_name = spec.get("reflect_name", "正本反映")
    BS = chr(92)

    def _reflect_base(t):
        """反映する1件の、元の版の SHA-256（大文字16進）を返す。new のときは None。決められないときは、False。"""
        if t.get("new"):
            return None
        if t.get("sha256"):
            return t["sha256"].upper()
        if t.get("base_file"):
            return sha256(t["base_file"])
        key = t["path"].replace(BS, "/")
        return record[key]["sha256"] if key in record else False

    if do_reflect:
        # --- 先に確かめる（問題があれば、何も書かずに止まる）
        missing = [t["path"].replace(BS, "/") for t in reflect_items if _reflect_base(t) is False]
        if missing:
            print("元の版の SHA-256 を決められないため、何も作りませんでした（sha256 か base_file を書くか、取得の記録.json に残すか、new を true にする）:")
            for m in missing:
                print("  ", m)
            sys.exit(1)

    if args.only in ("all", "upload"):
        # --- レビュー用の置き場へ上げる
        allow = spec.get("allow_in_progress", [])
        for rel in allow:
            assert rel in spec["upload"], f"allow_in_progress は upload に書いたものだけ: {rel}"
        for rel in spec["upload"]:
            assert "作成中" not in rel or rel in allow, f"作成中の名前は書かない（確定したら外す。上げるなら allow_in_progress に書く）: {rel}"
        allow_items = ",\n".join(f'    "{bs(r)}"' for r in allow)
        items = ",\n".join(f'    "{bs(r)}"' for r in spec["upload"])
        move_scope = spec.get("move_scope", "all")
        assert move_scope in ("all", "uploaded"), f"move_scope は all か uploaded: {move_scope}"
        text = fill(
            (TEMPLATES / "upload.ps1.tmpl").read_text(encoding="utf-8"),
            {
                "FOLDER_NAME": server_name,
                "UPLOAD_SCRIPT": up_ps1,
                "UPLOAD_ITEMS": items,
                "MOVE_SCOPE": move_scope,
                "ALLOW_IN_PROGRESS": allow_items,
                "SERVER_ROOT": server_root_path,
            },
        )
        write_ps1(folder / f"{up_ps1}.ps1", text)
        write_bat(
            folder / f"{up_ps1}.bat",
            fill(
                bat,
                {
                    "PS1": f"{up_ps1}.ps1",
                    "DESCRIPTION": f"ファイルサーバーのレビュー用の置き場（{name}）に、修正した資料を上げる。",
                },
            ),
        )

    if do_reflect:
        # --- 正本へ反映する
        targets = []
        for t in reflect_items:
            p = t["path"].replace(BS, "/")
            local = t.get("local") or local_relative(p, cfg)
            root = t.get("root", cfg["source_dir"])
            base = _reflect_base(t)
            base_text = "$null" if base is None else f'"{base}"'
            targets.append(
                f'    @{{ Root = "{bs(root)}"; Path = "{bs(p)}"; Local = "{bs(local)}"; Base = {base_text} }}'
            )
        review_root = bs(spec["server_root"]) if spec.get("server_root") else cfg["review_dir"]
        text = fill(
            (TEMPLATES / "reflect.ps1.tmpl").read_text(encoding="utf-8"),
            {
                "FOLDER_NAME": name,
                "DESIGN_ROOT": cfg["design_root"],
                "REVIEW_ROOT": review_root,
                "TARGET_ITEMS": chr(10).join(targets),
            },
        )
        write_ps1(folder / f"{reflect_name}.ps1", text)
        write_bat(
            folder / f"{reflect_name}.bat",
            fill(
                bat,
                {
                    "PS1": f"{reflect_name}.ps1",
                    "DESCRIPTION": f"レビュー用の置き場（{name}）でレビューした修正版を、正本（反映先）に反映する。",
                },
            ),
        )
    made = []
    if args.only in ("all", "upload"):
        made.append(f"{up_ps1}.ps1/.bat")
    if do_reflect:
        made.append(f"{reflect_name}.ps1/.bat")
    print("作成:", " と ".join(made), "→", folder)
    print("実行は、ユーザーが行う（ドライラン → 確認 → 実行）。")


if __name__ == "__main__":
    main()
