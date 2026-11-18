# -*- coding: utf-8 -*-
"""DDL（*.sql）から、機能別ER図の箱（entities）の下書きを JSON で出す。

DDLの読み取りは、同じフォルダの parse_ddl.py を使う。

出した下書きは、そのまま図にするものではない。
その機能で使わない列を消し、★・✕・注記（キャッシュ、値のみ保持など）を書き足してから spec に入れる。

使い方:
    py ddl_entities.py --ddl-dir <DDLのフォルダ> shop.order shop.customer
    py ddl_entities.py --ddl-dir <DDLのフォルダ> --list        # テーブルの一覧だけを出す
    py ddl_entities.py --ddl-dir <DDLのフォルダ> --alter-file-pattern "^[0-9]+_alter_" --list   # ALTER TABLE を置くファイルの名前の形を渡す
"""

import argparse
import json
import sys
from pathlib import Path

# 監査列。機能別ER図では、その機能で意味を持つとき（作成日時を画面に出すなど）だけ載せる
AUDIT_COLUMNS = ("created_at", "updated_at", "created_by", "updated_by", "deleted_at")


def load_tables(ddl_dir, alter_file_pattern=None):
    """DDLのフォルダの *.sql を同じフォルダの parse_ddl.py で読み、{schema.table: Table} を返す。

    引数:
        ddl_dir: DDL（*.sql）を置いたフォルダ。
        alter_file_pattern: ALTER TABLE を置いてよいファイル名の正規表現。省くと ALTER TABLE はエラーで止める。
    """
    migrations = Path(ddl_dir)
    if not migrations.is_dir():
        raise SystemExit(f"エラー: DDLのフォルダが見つからない: {migrations}（--ddl-dir にDDLのフォルダを指定する）")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import parse_ddl  # noqa: E402
    try:
        return parse_ddl.parse_directory(str(migrations), alter_file_pattern)
    except parse_ddl.DdlParseError as error:
        # 読めない書式（ALTER TABLE など）は、トレースバックではなく文言だけを出して止める
        raise SystemExit(f"エラー: DDLを読めない: {error}") from None


def _fk_columns(table):
    """外部キーに含まれる列名の集合を返す。"""
    return {c for fk in table.fks for c in fk.columns}


def _column_line(col, fk_cols, single_uniques):
    """列1つを「論理名（物理名） PK/FK/U」の書き方にする。"""
    marks = []
    if col.is_pk:
        marks.append("PK")
    if col.name in fk_cols:
        marks.append("FK")
    if col.name in single_uniques and not col.is_pk:
        marks.append("U")
    suffix = (" " + " ".join(marks)) if marks else ""
    return f"{col.logical}（{col.name}）{suffix}"


def entity_draft(table, include_audit):
    """1テーブル分の箱の下書きを作る。"""
    fk_cols = _fk_columns(table)
    single_uniques = {u[0] for u in table.uniques if len(u) == 1}
    pk, cols = [], []
    for col in table.columns:
        if col.name in AUDIT_COLUMNS and not include_audit:
            continue
        line = _column_line(col, fk_cols, single_uniques)
        (pk if col.is_pk else cols).append(line)
    # 複数列の一意制約は、列の並びのあとに U（a, b）で書く
    for u in table.uniques:
        if len(u) > 1:
            cols.append(f"U（{', '.join(u)}）")
    return {
        "table": table.key,
        "logical": table.logical,
        "status": "unchanged",
        "pk": pk,
        "cols": cols,
    }


def fk_drafts(tables, keys):
    """指定したテーブルどうしの外部キーを、線（edges）の下書きにする。

    戻り値: (線の下書き, 自分自身への外部キーの説明)。
    自分自身への外部キーは線にすると箱を貫くため、注記に書く候補として分けて返す。
    外部キーの列に一意制約も付いているもの（1件しか持てない子）は、1対0..1（zero_to_one）にする。
    """
    short = {k: k.split(".")[1] for k in keys}
    edges, self_refs = [], []
    for k in keys:
        t = tables[k]
        uniques = {tuple(sorted(u)) for u in t.uniques}
        for fk in t.fks:
            if fk.ref_key == k:
                self_refs.append(f"{k}.{', '.join(fk.columns)} は自分自身（{k}）を参照する外部キーである。")
                continue
            if fk.ref_key not in keys:
                continue
            label = f"ON DELETE {fk.on_delete}" if fk.on_delete else ""
            one = tuple(sorted(fk.columns)) in uniques
            edge = {"from": short[fk.ref_key], "to": short[k], "kind": "zero_to_one" if one else "fk"}
            if len(fk.columns) > 1:
                label = ("複合FK " + label).strip()
            if one:
                label = ("1:0..1（UNIQUE） " + label).strip()
            if label:
                edge["label"] = label
            edges.append(edge)
    return edges, self_refs


def main():
    """コマンドラインから呼ぶ入口。"""
    ap = argparse.ArgumentParser(description="DDLから機能別ER図の箱の下書きを出す")
    ap.add_argument("tables", nargs="*", help="スキーマ.物理名（例: shop.order）")
    ap.add_argument("--ddl-dir", required=True, help="DDL（*.sql）のフォルダ")
    ap.add_argument("--alter-file-pattern", help="ALTER TABLE を置いてよいファイル名の正規表現。省くと ALTER TABLE はエラーで止める")
    ap.add_argument("--list", action="store_true", help="テーブルの一覧だけを出す")
    ap.add_argument("--include-audit", action="store_true", help="監査列（created_at など）も出す")
    args = ap.parse_args()

    tables = load_tables(args.ddl_dir, args.alter_file_pattern)
    if args.list:
        for key, t in tables.items():
            print(f"{key:50s} {t.logical}  ({t.source})")
        return 0

    missing = [k for k in args.tables if k not in tables]
    if missing:
        print(f"エラー: DDLに無いテーブル: {missing}（新規テーブルは spec に直接書く）", file=sys.stderr)
        return 1
    # 箱のキーは物理名（スキーマ無し）にする。重なる場合はスキーマを付けるよう知らせる
    names = [k.split(".")[1] for k in args.tables]
    if len(set(names)) != len(names):
        print("エラー: 物理名が重なるテーブルがある。spec の箱のキーを手で付け直すこと", file=sys.stderr)
        return 1
    edges, self_refs = fk_drafts(tables, args.tables)
    out = {
        "entities": {k.split(".")[1]: entity_draft(tables[k], args.include_audit) for k in args.tables},
        "edges": edges,
        "sources": {k: tables[k].source for k in args.tables},
    }
    if self_refs:
        # 線にはしない。必要なら point の注記に書く
        out["self_references"] = self_refs
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
