# -*- coding: utf-8 -*-
"""DDL（*.sql）を読み、機能別ER図の下書き（ddl_entities.py）と検査（validate_feature_er.py）に必要な情報だけを抜き出す。

ddl_entities.py は parse_directory() の戻り値（Table・Column・ForeignKey の属性）に直接頼っている。戻り値の形を変えるときは、あちらも直して動かす。

DDLが次の書式に統一されている前提で読むため、汎用SQLパーサは使わない。

  - テーブル定義は ``CREATE TABLE IF NOT EXISTS <schema>.<table> ( ... );`` のみ。
  - 主キーは全て列レベルの ``PRIMARY KEY``（表レベルの ``PRIMARY KEY (...)`` は存在しない）。
  - テーブルの最終形は CREATE だけで表す。
    ``ALTER TABLE`` は、``alter_file_pattern``（ファイル名の正規表現）に合うファイル（作り直さない DB を追いつかせるためのもの）にだけ置かれる。
    パターンを渡さないときは、``ALTER TABLE`` を読めない文として止める。
  - ``DROP TABLE`` は使われていない。
  - 論理名は ``COMMENT ON TABLE`` / ``COMMENT ON COLUMN`` から取得する（全表・全列に付与済み）。
    ALTER で足す列のコメントは、ALTER のファイルの ``COMMENT ON COLUMN`` から取得する。

仕様外の書式を見つけた場合は握り潰さず ``DdlParseError`` で止める。
パターンに合わないファイルの ``ALTER TABLE``（パターンが無いときはすべての ``ALTER TABLE``）、``DROP TABLE``・``IF NOT EXISTS`` の無い ``CREATE TABLE``・
``CREATE UNLOGGED TABLE``・``LIKE``・``INHERITS``・``PARTITION`` も、読めない書き方として止める。
パターンに合うファイルの ``ALTER TABLE`` は図に使わず、足す列・外部キー・変える列が、型・参照先まで CREATE と同じであることだけを確かめる。
NULL 可で足した列が、CREATE では NOT NULL なのに、あとの ALTER で SET NOT NULL を付けていなければ、止めずに警告を標準エラーに出す
（2段階で NOT NULL を付ける途中は正しい状態のため）。
ただし、``EXECUTE format('ALTER TABLE ...')`` のように文字列で組み立てた文は見つけられない。
黙って取りこぼすと、図に出ないテーブルや列が発生しても誰も気付けないためである。
"""

import glob
import os
import re
import sys
from dataclasses import dataclass, field

# 監査列の名前。このファイルの中では使っていない（機能別ER図で監査列を扱う決まりは ddl_entities.py の AUDIT_COLUMNS にある）
AUDIT_COLUMNS = ("created_at", "updated_at", "created_by", "updated_by", "deleted_at")

# このパーサが読めない、テーブルの形を変える文。見つけたら止める（黙って読み飛ばすと列が落ちる）
_UNSUPPORTED_STATEMENTS = (
    (r"\bALTER\s+TABLE\b", "ALTER TABLE"),
    (r"\bDROP\s+TABLE\b", "DROP TABLE"),
    (r"\bCREATE\s+TABLE\b(?!\s+IF\s+NOT\s+EXISTS\b)", "IF NOT EXISTS の無い CREATE TABLE"),
    (r"\bCREATE\s+(?:(?:GLOBAL|LOCAL)\s+)?UNLOGGED\s+TABLE\b", "CREATE UNLOGGED TABLE"),
    (r"\bINHERITS\s*\(", "INHERITS"),
    (r"\bPARTITION\s+(?:BY|OF)\b", "PARTITION"),
)

# 列定義ではなく表レベルの制約であることを示す先頭キーワード
_CONSTRAINT_HEADS = ("PRIMARY KEY", "UNIQUE", "FOREIGN KEY", "CONSTRAINT", "CHECK", "EXCLUDE", "LIKE")

# 識別子（スキーマ名・テーブル名・列名）。数字は2文字目から使える
_IDENT = r"[a-z_][a-z0-9_]*"

# 作り直さない DB 向けの ALTER のファイル名（<番号>_<スキーマ>_alter_<内容>.sql）。
# ALTER のファイルは、呼び出し側が渡す名前の形（alter_file_pattern）で見分ける。形が無いときは、ALTER のファイルは無いものとして扱う

# 型の別名を正式な名前にそろえる対応表。ALTER と CREATE の型を比べるときに使う（int8 と BIGINT を同じ型として扱うため）
_TYPE_ALIASES = {
    "INT8": "BIGINT", "INT": "INTEGER", "INT4": "INTEGER", "INT2": "SMALLINT",
    "TIMESTAMPTZ": "TIMESTAMP WITH TIME ZONE", "TIMETZ": "TIME WITH TIME ZONE",
    "VARCHAR": "CHARACTER VARYING", "BOOL": "BOOLEAN", "FLOAT8": "DOUBLE PRECISION", "DECIMAL": "NUMERIC",
}

# データ型の書き方。空白を含む型を先に並べ、最後に「1トークン＋桁指定」で受ける。
# 単純に「英字と空白の並び」で受けると GENERATED ALWAYS AS IDENTITY PRIMARY KEY まで
# 型として飲み込んでしまい、主キーを取りこぼすため、型の形を明示する。
_TYPE_PATTERN = (
    r"(?:TIMESTAMP(?:\s*\(\d+\))?\s+WITH(?:OUT)?\s+TIME\s+ZONE"
    r"|TIME(?:\s*\(\d+\))?\s+WITH(?:OUT)?\s+TIME\s+ZONE"
    r"|DOUBLE\s+PRECISION"
    r"|CHARACTER\s+VARYING(?:\s*\([^)]*\))?"
    r"|BIT\s+VARYING(?:\s*\([^)]*\))?"
    r"|[A-Za-z_][A-Za-z0-9_]*(?:\s*\([^)]*\))?)"
    r"(?:\s*\[\s*\])*"
)


class DdlParseError(RuntimeError):
    """DDLが想定書式から外れているときに送出する。"""


@dataclass
class ForeignKey:
    """外部キー1本。複合外部キーも1本として表す。"""

    columns: tuple            # 子側（FKを持つ側）の列名
    ref_schema: str           # 参照先スキーマ
    ref_table: str            # 参照先テーブル（スキーマ無しの物理名）
    ref_columns: tuple        # 参照先の列名
    on_delete: str = ""       # ON DELETE の挙動（"CASCADE" / "SET NULL" など。無指定は空文字）

    @property
    def ref_key(self):
        """参照先を ``schema.table`` の形で返す。"""
        return f"{self.ref_schema}.{self.ref_table}"


@dataclass
class Column:
    """テーブルの1列。"""

    name: str                 # 物理列名
    type: str                 # データ型（桁を含む）
    not_null: bool = False    # NOT NULL 制約の有無
    is_pk: bool = False       # 主キーかどうか
    is_unique: bool = False   # 単独のUNIQUE制約を持つかどうか
    logical: str = ""         # 論理名（COMMENT ON COLUMN から取得）
    comment: str = ""         # 列コメント全文


@dataclass
class Table:
    """1テーブル。"""

    schema: str                                   # スキーマ名
    name: str                                     # 物理テーブル名（スキーマ無し）
    columns: list = field(default_factory=list)   # 列（DDLの定義順）
    pk: list = field(default_factory=list)        # 主キーの列名
    uniques: list = field(default_factory=list)   # 一意制約（列名のタプル。単独UNIQUEも含む）
    fks: list = field(default_factory=list)       # 外部キー
    logical: str = ""                             # 論理名（COMMENT ON TABLE の先頭文）
    comment: str = ""                             # テーブルコメント全文
    source: str = ""                              # 由来のDDLファイル名

    @property
    def key(self):
        """``schema.table`` の形で返す。図中の一意キーとして使う。"""
        return f"{self.schema}.{self.name}"

    def column(self, name):
        """列名から Column を引く。存在しなければ None。"""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def fk_columns(self):
        """外部キーに含まれる列名の集合を返す。"""
        return {c for fk in self.fks for c in fk.columns}

    def unique_columns(self):
        """一意制約に含まれる列名の集合を返す。"""
        return {c for u in self.uniques for c in u}


def _strip_line_comments(text):
    """``--`` 以降の行コメントを落とす。文字列リテラル内の ``--`` は保護する。

    複数行にまたがる文字列があるため、文字列の中かどうかは行をまたいで引き継ぐ。
    """
    out = []
    in_str = False
    for line in text.split("\n"):
        cut = len(line)
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == "'":
                in_str = not in_str
            elif not in_str and ch == "-" and i + 1 < len(line) and line[i + 1] == "-":
                cut = i
                break
            i += 1
        out.append(line[:cut])
    return "\n".join(out)


def _split_top_level(body):
    """括弧の深さ0のカンマで分割する。型の桁指定や複合キーの括弧を壊さないため。"""
    items = []
    depth = 0
    buf = []
    in_str = False
    for ch in body:
        if ch == "'":
            in_str = not in_str
        if not in_str:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                items.append("".join(buf).strip())
                buf = []
                continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        items.append(tail)
    return [i for i in items if i]


def _parse_reference(text):
    """``REFERENCES schema.table (col, ...) [ON DELETE X]`` を読み取る。

    引数:
        text: 列定義または表レベル制約の本文。

    戻り値:
        (ref_schema, ref_table, ref_columns, on_delete) のタプル。該当が無ければ None。
    """
    m = re.search(r"REFERENCES\s+(%s)\.(%s)\s*\(([^)]*)\)" % (_IDENT, _IDENT), text, re.I)
    if not m:
        return None
    ref_cols = tuple(c.strip() for c in m.group(3).split(",") if c.strip())

    # ON DELETE は REFERENCES の後ろにしか現れない
    on_delete = ""
    d = re.search(r"ON\s+DELETE\s+(CASCADE|SET\s+NULL|SET\s+DEFAULT|RESTRICT|NO\s+ACTION)",
                  text[m.end():], re.I)
    if d:
        on_delete = re.sub(r"\s+", " ", d.group(1).upper())
    return m.group(1), m.group(2), ref_cols, on_delete


def _normalize_type(type_text):
    """型の書き方をそろえる。大文字にし、空白をつめ、別名を正式な名前にする（桁の指定は残す）。"""
    t = re.sub(r"\s+", " ", type_text.strip().upper())
    t = re.sub(r"\s*\(\s*", "(", re.sub(r"\s*\)", ")", re.sub(r"\s*,\s*", ",", t)))
    base, paren, size = t.partition("(")
    return _TYPE_ALIASES.get(base.strip(), base.strip()) + paren + size


def _parse_column(item, table):
    """列定義1件を読み取り、Table へ足す。"""
    # 先頭は「列名 型」。型は括弧付きの桁指定や空白を含むことがある
    m = re.match(r"^([a-z_][a-z0-9_]*)\s+(%s)" % _TYPE_PATTERN, item, re.I)
    if not m:
        raise DdlParseError(f"列定義として読めない: {item[:80]!r}")
    col = Column(name=m.group(1), type=re.sub(r"\s+", " ", m.group(2).strip()))
    rest = item[m.end():]

    # 列レベルの制約を拾う
    col.not_null = bool(re.search(r"\bNOT\s+NULL\b", rest, re.I))
    col.is_pk = bool(re.search(r"\bPRIMARY\s+KEY\b", rest, re.I))
    col.is_unique = bool(re.search(r"\bUNIQUE\b", rest, re.I))

    if col.is_pk:
        table.pk.append(col.name)
    if col.is_unique:
        table.uniques.append((col.name,))

    # 列レベルの外部キー。REFERENCES があるのに読めないときは、黙って外部キーを落とさずに止める
    ref = _parse_reference(rest)
    if ref is None and re.search(r"\bREFERENCES\b", rest, re.I):
        raise DdlParseError(f"外部キーの参照先として読めない（REFERENCES スキーマ.テーブル (列) の形で書く）: {item[:80]!r}")
    if ref:
        table.fks.append(ForeignKey(
            columns=(col.name,),
            ref_schema=ref[0], ref_table=ref[1], ref_columns=ref[2], on_delete=ref[3]))

    table.columns.append(col)


def _parse_constraint(item, table):
    """表レベルの制約1件を読み取り、Table へ足す。"""
    # CONSTRAINT <名前> を剥がしてから中身を見る
    body = re.sub(r"^CONSTRAINT\s+[a-z_][a-z0-9_]*\s+", "", item, flags=re.I).strip()

    if re.match(r"^PRIMARY\s+KEY", body, re.I):
        cols = re.search(r"\(([^)]*)\)", body)
        if cols:
            table.pk.extend(c.strip() for c in cols.group(1).split(",") if c.strip())
        return

    if re.match(r"^UNIQUE", body, re.I):
        cols = re.search(r"\(([^)]*)\)", body)
        if cols:
            table.uniques.append(tuple(c.strip() for c in cols.group(1).split(",") if c.strip()))
        return

    if re.match(r"^FOREIGN\s+KEY", body, re.I):
        cols = re.search(r"^FOREIGN\s+KEY\s*\(([^)]*)\)", body, re.I)
        ref = _parse_reference(body)
        if not cols or not ref:
            raise DdlParseError(f"外部キーとして読めない: {item[:80]!r}")
        table.fks.append(ForeignKey(
            columns=tuple(c.strip() for c in cols.group(1).split(",") if c.strip()),
            ref_schema=ref[0], ref_table=ref[1], ref_columns=ref[2], on_delete=ref[3]))
        return

    # CHECK / EXCLUDE はER図に描かないため読み飛ばす
    if re.match(r"^(CHECK|EXCLUDE)", body, re.I):
        return

    raise DdlParseError(f"未知の表レベル制約: {item[:80]!r}")


def _logical_from_table_comment(comment):
    """テーブルコメントから論理名を取り出す。先頭の1文（``。`` まで）を論理名とする。"""
    head = comment.split("。")[0].strip()
    return head or comment.strip()


def _logical_from_column_comment(comment):
    """列コメントから論理名を取り出す。

    列コメントの丸括弧は「（主キー）」「（shop.customer）」のように
    補足か参照先の説明であり、論理名そのものではないため落とす。
    """
    head = comment.split("。")[0]
    head = head.split("（")[0]
    return head.strip() or comment.strip()


def parse_directory(migrations_dir, alter_file_pattern=None):
    """DDLのフォルダを読み、``{schema.table: Table}`` を返す。

    引数:
        migrations_dir: DDL（*.sql）のフォルダ。
        alter_file_pattern: ALTER TABLE を置いてよいファイル名（拡張子つき）の正規表現。None なら、ALTER TABLE はエラーで止める。

    戻り値:
        物理名をキーにした Table の辞書。挿入順はDDLの適用順（ファイル名順）。
    """
    alter_file_re = re.compile(alter_file_pattern) if alter_file_pattern else None
    files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
    if not files:
        raise DdlParseError(f"SQLファイルが1件も無い: {migrations_dir}")

    tables = {}
    comments_table = {}
    comments_column = {}
    # ALTER のファイルの ALTER TABLE（ファイル名, 行番号, schema.table, 操作の文）
    alter_checks = []

    for path in files:
        raw = open(path, encoding="utf-8").read()
        # ブロックコメントは、行番号がずれないよう中の改行だけ残して落とす
        raw = re.sub(r"/\*.*?\*/", lambda b: "\n" * b.group(0).count("\n"), raw, flags=re.S)
        sql = _strip_line_comments(raw)
        name = os.path.basename(path)

        # --- 読めない文が無いかを確かめる（文字列リテラルの中は見ない） ---
        # 文字列は、行番号がずれないよう中の改行だけ残して空にする
        code = re.sub(r"'(?:[^']|'')*'", lambda q: "'" + "\n" * q.group(0).count("\n") + "'", sql)
        is_alter_file = bool(alter_file_re and alter_file_re.search(name))
        for pattern, label in _UNSUPPORTED_STATEMENTS:
            # 既存の DB 向けの ALTER のファイルでは、ALTER TABLE を後で CREATE と突き合わせる
            if is_alter_file and label == "ALTER TABLE":
                continue
            found = re.search(pattern, code, re.I)
            if found:
                line_no = code[:found.start()].count("\n") + 1
                raise DdlParseError(
                    f"{name}:{line_no}: {label} は読めない。このパーサは CREATE TABLE IF NOT EXISTS だけを読むため、"
                    "このままでは列やテーブルが下書き・検査から落ちる。"
                    "CREATE を書き換えるか、ALTER TABLE を置くファイルの名前の形を --alter-file-pattern で渡す")

        # --- ALTER のファイルの ALTER TABLE を拾う（CREATE との突き合わせは、全ファイルを読んだ後に行う） ---
        if is_alter_file:
            alter_count = len(re.findall(r"\bALTER\s+TABLE\b", code, re.I))
            alter_read = 0
            for m in re.finditer(r"\bALTER\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:ONLY\s+)?(%s\.%s)\s+([^;]*);"
                                 % (_IDENT, _IDENT), code, re.I):
                alter_read += 1
                line_no = code[:m.start()].count("\n") + 1
                # カンマで続けた操作も、1つずつ確かめる
                for action in _split_top_level(m.group(2)):
                    alter_checks.append((name, line_no, m.group(1), " ".join(action.split())))
            # 読めた数が ALTER TABLE の数と違えば、確かめずに通る文がある（スキーマ無しの名前など）
            if alter_read != alter_count:
                raise DdlParseError(
                    f"{name}: ALTER TABLE が {alter_count} 件あるが、{alter_read} 件しか読めない。"
                    "「ALTER TABLE [IF EXISTS] [ONLY] スキーマ.テーブル 操作;」の形だけを読む")

        # --- CREATE TABLE を括弧対応で切り出す ---
        create_count = len(re.findall(r"\bCREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\b", code, re.I))
        read_count = 0
        for m in re.finditer(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(%s)\.(%s)\s*\(" % (_IDENT, _IDENT),
                             sql, re.I):
            read_count += 1
            depth = 1
            i = m.end()
            while i < len(sql) and depth > 0:
                if sql[i] == "(":
                    depth += 1
                elif sql[i] == ")":
                    depth -= 1
                i += 1
            if depth != 0:
                raise DdlParseError(f"{name}: CREATE TABLE の括弧が閉じていない")

            table = Table(schema=m.group(1), name=m.group(2), source=name)
            heads = "|".join(h.replace(" ", r"\s+") for h in _CONSTRAINT_HEADS)
            for item in _split_top_level(sql[m.end():i - 1]):
                if re.match(r"^(%s)\b" % heads, item, re.I):
                    _parse_constraint(item, table)
                else:
                    _parse_column(item, table)

            if not table.pk:
                raise DdlParseError(f"{name}: {table.key} に主キーが無い")
            tables[table.key] = table

        # 読めた数が CREATE TABLE IF NOT EXISTS の数と違えば、読めない書き方がある（スキーマ無しの名前、AS SELECT など）
        if read_count != create_count:
            raise DdlParseError(
                f"{name}: CREATE TABLE IF NOT EXISTS が {create_count} 件あるが、{read_count} 件しか読めない。"
                "「CREATE TABLE IF NOT EXISTS スキーマ.テーブル ( 列の定義 )」の形だけを読む")

        # --- COMMENT ON を拾う（論理名の出どころ） ---
        for m in re.finditer(r"COMMENT\s+ON\s+TABLE\s+(%s\.%s)\s+IS\s+'((?:[^']|'')*)'" % (_IDENT, _IDENT),
                             sql, re.I | re.S):
            comments_table[m.group(1)] = m.group(2).replace("''", "'")
        for m in re.finditer(
                r"COMMENT\s+ON\s+COLUMN\s+(%s\.%s)\.(%s)\s+IS\s+'((?:[^']|'')*)'" % (_IDENT, _IDENT, _IDENT),
                sql, re.I | re.S):
            comments_column[(m.group(1), m.group(2))] = m.group(3).replace("''", "'")

    # --- コメントをテーブル・列へ結び付ける ---
    for key, table in tables.items():
        table.comment = comments_table.get(key, "")
        table.logical = _logical_from_table_comment(table.comment) if table.comment else table.name
        for col in table.columns:
            col.comment = comments_column.get((key, col.name), "")
            col.logical = _logical_from_column_comment(col.comment) if col.comment else col.name

    # --- 参照先が実在するかを確かめる ---
    for table in tables.values():
        for fk in table.fks:
            if fk.ref_key not in tables:
                raise DdlParseError(f"{table.key} の外部キー参照先が存在しない: {fk.ref_key}")

    # --- ALTER のファイルで変える列・外部キーが、CREATE にもあるかを確かめる ---
    # NOT NULL を付けずに足した列のうち、CREATE では NOT NULL の列（2段階目の SET NOT NULL を待っている列）
    pending_not_null = {}
    # ALTER で SET NOT NULL を付けた列。並び順によらず判定するため、最後に pending_not_null との差を取る
    set_not_null = set()
    for name, line_no, key, action in alter_checks:
        where = f"{name}:{line_no}: ALTER TABLE {key}"
        table = tables.get(key)
        if table is None:
            raise DdlParseError(f"{where} の対象が CREATE TABLE に無い")
        columns_by_name = {c.name: c for c in table.columns}
        add_column = re.match(r"ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?(%s)\s+(%s)" % (_IDENT, _TYPE_PATTERN),
                              action, re.I)
        alter_column = re.match(r"ALTER\s+COLUMN\s+(%s)\s+(.*)$" % _IDENT, action, re.I)
        add_fk = re.match(r"ADD\s+CONSTRAINT\s+%s\s+FOREIGN\s+KEY\s*\(([^)]*)\)" % _IDENT, action, re.I)
        if add_column or alter_column:
            column = (add_column or alter_column).group(1)
            created = columns_by_name.get(column)
            if created is None:
                raise DdlParseError(f"{where} の列 {column} が CREATE に無い。CREATE も書き換える")
            # 足す型・変える型が、CREATE の型と同じかを確かめる
            if add_column:
                new_type = add_column.group(2)
            else:
                to_type = re.match(r"(?:SET\s+DATA\s+)?TYPE\s+(%s)" % _TYPE_PATTERN, alter_column.group(2), re.I)
                new_type = to_type.group(1) if to_type else None
            if new_type is not None and _normalize_type(new_type) != _normalize_type(created.type):
                raise DdlParseError(f"{where} の列 {column} の型 {new_type} が、CREATE の型 {created.type} と違う")
            # ADD COLUMN に書いた NOT NULL・外部キーも、CREATE と合っているかを確かめる
            # （NOT NULL を書かずに足すのは、2段階で付けるときの書き方なのでよい）
            if add_column:
                rest = action[add_column.end():]
                # CHECK (x IS NOT NULL) の「NOT NULL」を、列の NOT NULL と取り違えないよう除いてから探す
                adds_not_null = bool(re.search(r"\bNOT\s+NULL\b", re.sub(r"\bIS\s+NOT\s+NULL\b", "", rest, flags=re.I), re.I))
                if adds_not_null and not created.not_null:
                    raise DdlParseError(f"{where} で列 {column} を NOT NULL で足すが、CREATE は NULL 可のまま")
                if not adds_not_null and created.not_null:
                    pending_not_null[(key, column)] = where
                inline_ref = _parse_reference(rest)
                if inline_ref is None and re.search(r"\bREFERENCES\b", rest, re.I):
                    raise DdlParseError(f"{where} の列 {column} の外部キーの参照先が読めない（REFERENCES スキーマ.テーブル (列) の形で書く）")
                if inline_ref and not any(
                        fk.columns == (column,) and (fk.ref_schema, fk.ref_table, fk.ref_columns, fk.on_delete) == inline_ref
                        for fk in table.fks):
                    raise DdlParseError(f"{where} の列 {column} の外部キー（参照先 {inline_ref[0]}.{inline_ref[1]}、"
                                        f"ON DELETE {inline_ref[3] or '指定なし'}）が CREATE に無い。CREATE も同じ定義に書き換える")
            # NOT NULL を付ける・外すなら、CREATE の NOT NULL と合っているかを確かめる
            if alter_column and re.match(r"SET\s+NOT\s+NULL$", alter_column.group(2), re.I):
                if not created.not_null:
                    raise DdlParseError(f"{where} で列 {column} に NOT NULL を付けるが、CREATE は NULL 可のまま")
                set_not_null.add((key, column))
            if alter_column and re.match(r"DROP\s+NOT\s+NULL$", alter_column.group(2), re.I) and created.not_null:
                raise DdlParseError(f"{where} で列 {column} の NOT NULL を外すが、CREATE は NOT NULL のまま")
        elif add_fk:
            columns = tuple(c.strip() for c in add_fk.group(1).split(","))
            ref = _parse_reference(action)
            if ref is None:
                raise DdlParseError(f"{where} の外部キーの参照先が読めない（REFERENCES スキーマ.テーブル (列) の形で書く）")
            # 参照先と ON DELETE まで、CREATE の外部キーと同じかを確かめる
            if not any(fk.columns == columns and (fk.ref_schema, fk.ref_table, fk.ref_columns, fk.on_delete) == ref
                       for fk in table.fks):
                raise DdlParseError(f"{where} の外部キー {columns}（参照先 {ref[0]}.{ref[1]}、ON DELETE {ref[3] or '指定なし'}）"
                                    "が CREATE に無い。CREATE も同じ定義に書き換える")
        else:
            raise DdlParseError(
                f"{where} の操作は読めない（{action[:40]}）。ADD COLUMN・ALTER COLUMN・ADD CONSTRAINT … FOREIGN KEY だけを読む")

    # --- 2段階目の SET NOT NULL が無い列を知らせる ---
    # 2段階で NOT NULL を付ける途中（1回目だけをデプロイした間）は正しい状態なので、止めずに警告にとどめる
    for (key, column), where in pending_not_null.items():
        if (key, column) in set_not_null:
            continue
        print(f"警告: {where} で列 {column} を NULL 可で足したが、NOT NULL を付ける2段階目の ALTER が無い。"
              "CREATE は NOT NULL のため、作り直さない DB だけ NULL 可のまま残る（段階的に NOT NULL を付ける運用か確かめる）", file=sys.stderr)

    return tables


def summarize(tables):
    """解析結果の件数をまとめて返す。このファイルを直接実行したときの確認表示に使う。"""
    fk_count = sum(len(t.fks) for t in tables.values())
    schemas = {}
    for t in tables.values():
        schemas[t.schema] = schemas.get(t.schema, 0) + 1
    cross = sum(1 for t in tables.values() for fk in t.fks if fk.ref_schema != t.schema)
    return dict(tables=len(tables), fks=fk_count, cross_schema_fks=cross,
                schemas=dict(sorted(schemas.items())))


if __name__ == "__main__":
    import json
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "."
    parsed = parse_directory(target, sys.argv[2] if len(sys.argv) > 2 else None)
    print(json.dumps(summarize(parsed), ensure_ascii=False, indent=2))
    for key in sorted(parsed):
        t = parsed[key]
        print(f"  {key:45s} {t.logical}  ({len(t.columns)}列 / FK {len(t.fks)}本)")
