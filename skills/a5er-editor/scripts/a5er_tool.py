#!/usr/bin/env python3
"""
A5:SQL Mk-2 の .a5er ファイル内で使われる EscapedString / Complex 値を
安全にエンコード・デコードし、ファイル全体の参照整合性を検証するための補助ツール。

このファイル形式は INI ライクだが、1行の中にカンマ区切り・ダブルクォート囲み・
独自エスケープを持つ「Complex」値が混在する。手作業でエスケープや引用符を
組み立てるとミスをしやすいため、SKILL.md の指示に従い、値の読み書きには
必ずこのツールを経由すること。

参照: ../references/a5er_specification.md
"""
import argparse
import json
import re
import sys

# ---------------------------------------------------------------------------
# 1. エスケープ / アンエスケープ (仕様書 1.2節)
# ---------------------------------------------------------------------------


def escape(s: str) -> str:
    """1文字ずつスキャンしてエスケープする。

    元の文字列を丸ごと複数回 str.replace() すると、あるルールの置換結果が
    別のルールの置換対象と偶然一致してしまうことがある(例えばバックスラッシュ+
    'n' という2文字が元々含まれていた場合、それを1文字ずつではなく行全体への
    replace() で処理すると、後続のルールが誤ってそれを改行の表現だと誤認する)。
    1文字ずつ順番に変換することで、この種の誤爆を避ける。
    """
    if s is None:
        return ""
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == "\"":
            out.append("\\Q")
        elif ch == "'":
            out.append("\\q")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\n":
            out.append("\\n")
        else:
            out.append(ch)
    return "".join(out)


_UNESCAPE_MAP = {"\\": "\\", "Q": "\"", "q": "'", "t": "\t", "n": "\n"}


def unescape(s: str) -> str:
    """エスケープ済み文字列を、先頭から1回だけ左から右へ走査して復元する。

    escape() と対になる実装。バックスラッシュを見つけたら次の1文字だけを見て
    デコードし、2文字分まとめて読み進める。全体に対して複数回 str.replace()
    をかけると、ある置換が作り出した文字列を別の置換ルールが誤って読み取って
    しまうことがあるため、1パスの走査でその問題を避けている。
    """
    if s is None:
        return ""
    out = []
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch == "\\" and i + 1 < n and s[i + 1] in _UNESCAPE_MAP:
            out.append(_UNESCAPE_MAP[s[i + 1]])
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


# ---------------------------------------------------------------------------
# 2. トークナイザ: Complex値 (カンマ区切り、文字列はダブルクォート) の分割・結合
# ---------------------------------------------------------------------------
# 各トークンは「元の生の文字列表現」を保持する (例: 空トークンは "" ではなく
# 空文字列、クォート付き文字列は先頭末尾のクォートを含んだまま保持)。
# こうすることで、触っていないトークンは 1文字も変えずに書き戻せる。

def tokenize(value: str):
    tokens = []
    i, n = 0, len(value)
    while True:
        if i >= n:
            tokens.append("")
            break
        if value[i] == '"':
            j = i + 1
            buf = ['"']
            while j < n:
                if value[j] == "\\" and j + 1 < n:
                    buf.append(value[j:j + 2])
                    j += 2
                    continue
                if value[j] == '"':
                    buf.append('"')
                    j += 1
                    break
                buf.append(value[j])
                j += 1
            tokens.append("".join(buf))
            i = j
            if i < n and value[i] == ",":
                i += 1
                continue
            elif i >= n:
                break
            else:
                # クォートの後にカンマ以外が続く想定外パターン。以降を bare として扱う。
                start = i
                comma = value.find(",", start)
                if comma == -1:
                    tokens.append(value[start:])
                    break
                tokens.append(value[start:comma])
                i = comma + 1
                continue
        else:
            comma = value.find(",", i)
            if comma == -1:
                tokens.append(value[i:])
                break
            tokens.append(value[i:comma])
            i = comma + 1
            continue
    return tokens


def join_tokens(tokens):
    return ",".join(tokens)


def token_to_value(tok: str):
    """生トークン -> Pythonの値 (文字列はアンエスケープ、それ以外はそのまま/空はNone)"""
    if tok == "":
        return None
    if tok.startswith('"') and tok.endswith('"') and len(tok) >= 2:
        return unescape(tok[1:-1])
    return tok


def value_to_token(value, kind: str):
    """Pythonの値 -> 生トークン。kind で引用要否を決める。
    kind:
      'str'       常にダブルクォートで囲む (空でも "" を出力)
      'strOrBare' 値があればダブルクォートで囲み、空ならクォート無しの空トークン
      'bare'      常にクォート無し (数値・$Color・列挙値など)。Noneや空は空トークン。
    """
    if kind == "bare":
        if value is None or value == "":
            return ""
        return str(value)
    if kind == "strOrBare":
        if value is None or value == "":
            return ""
        return '"' + escape(str(value)) + '"'
    # 'str'
    if value is None:
        value = ""
    return '"' + escape(str(value)) + '"'


# ---------------------------------------------------------------------------
# 3. Complex構造の定義 (仕様書 3〜4章)
#    フィールド名 -> kind のリスト。並び順が仕様書のフォーマット順。
# ---------------------------------------------------------------------------
SCHEMAS = {
    # [Entity] Field="論理名","物理名","データ型","NOT NULL",キー順,"デフォルト値","コメント",色,"オプション","追加オプション"
    # 注: NOT NULL は仕様書の書式表記・実例とも常にダブルクォート付きで出力されるため str とする
    # (CommonFieldのNOT NULLとは異なる。CommonFieldは実例で空の場合クォート無しになっている)。
    "Field": [
        ("lname", "str"), ("pname", "str"), ("dtype", "str"),
        ("notnull", "str"), ("pk_order", "bare"), ("default", "str"),
        ("comment", "str"), ("color", "bare"), ("option", "str"), ("disable", "str"),
    ],
    # [Manager] PageInfo="ページ名",表示モード,"用紙サイズ","背景色"
    "PageInfo": [
        ("page_name", "str"), ("view_mode", "bare"), ("paper_size", "str"), ("bg_color", "bare"),
    ],
    # [Manager] DomainInfo="ドメイン名","データ型","コメント","カラム物理名"
    "DomainInfo": [
        ("domain_name", "str"), ("dtype", "str"), ("comment", "str"), ("column_pname", "str"),
    ],
    # [Manager] CommonField="共通列論理名","共通列物理名","データ型","NOT NULL","キー順","デフォルト値","コメント",色
    # 注: 仕様書の書式表記では notnull/pk_order/default にクォートが付いているが、
    # 仕様書中の実例 (削除日時の例) では3つとも空の場合はクォート無しで出力されている。
    # 実データとの整合を優先し、ここでは実例に合わせて strOrBare とする。
    "CommonField": [
        ("lname", "str"), ("pname", "str"), ("dtype", "str"), ("notnull", "strOrBare"),
        ("pk_order", "bare"), ("default", "strOrBare"), ("comment", "str"), ("color", "bare"),
    ],
    # [Entity]/[View]/[Subtype] Position="ページ名",X,Y,幅,高さ  (幅・高さは省略可)
    "Position": [
        ("page_name", "str"), ("x", "bare"), ("y", "bare"), ("width", "bare"), ("height", "bare"),
    ],
    # [Relation] Position="ページ名",ラインモード,線位置1,線位置2,線位置3,端子位置1,端子位置2,"頂点座標リスト"
    "RelationPosition": [
        ("page_name", "str"), ("line_mode", "bare"), ("pos1", "bare"), ("pos2", "bare"),
        ("pos3", "bare"), ("term1", "bare"), ("term2", "bare"), ("vertices", "str"),
    ],
}


def parse_complex(value: str, schema_name: str) -> dict:
    """Complex値の文字列を dict にデコードする。
    仕様書に無い末尾の追加トークン(前方互換用)は "_extra" キーに生トークンのまま残す。
    """
    schema = SCHEMAS[schema_name]
    tokens = tokenize(value)
    result = {}
    for idx, (name, kind) in enumerate(schema):
        if idx < len(tokens):
            # 元の行にトークンが存在した(空文字でも「明示的に空」として扱う)
            result[name] = token_to_value(tokens[idx])
        # トークンが元々無かった(行が途中で終わっている)場合はキー自体を作らない。
        # これにより build_complex() に渡し戻したときに「未指定」として末尾から
        # 正しく省略され、元のファイルに無かった項目を新たに作り出さずに済む。
    if len(tokens) > len(schema):
        result["_extra"] = tokens[len(schema):]
    return result


_UNSET = object()


def build_complex(values: dict, schema_name: str) -> str:
    """dict から Complex値の文字列を組み立てる。

    values にキーが存在しない項目は「未指定(末尾なら省略可)」として扱い、
    末尾に連続する未指定項目はトークンごと切り詰める(例: disableを指定しなければ
    仕様書のサンプルと同じく行末に \",\" は追加されない)。
    一方、キーが存在して値が "" (空文字) の場合は「明示的に空を指定」として扱い、
    そのkindに応じたトークン("" ならクォート付き空文字など)を必ず出力する。

    注意: キーに明示的に null (Python の None) を指定した場合も「値は存在する」
    として扱われ、末尾切り詰めの対象にはならない(parse_complex() が返す、
    「元の行に空トークンとして存在していた」ことを表す None と区別しないため)。
    末尾の項目を本当に省略したい場合は、値を null にするのではなく、
    そのキー自体を values から取り除くこと。
    """
    schema = SCHEMAS[schema_name]
    toks = []
    unset_flags = []
    for name, kind in schema:
        raw = values.get(name, _UNSET)
        unset_flags.append(raw is _UNSET)
        toks.append(value_to_token(None if raw is _UNSET else raw, kind))
    extra = values.get("_extra") or []
    toks.extend(extra)
    unset_flags.extend([False] * len(extra))
    # 末尾から連続する「未指定」トークンのみ切り詰める
    while toks and unset_flags and unset_flags[-1]:
        toks.pop()
        unset_flags.pop()
    return join_tokens(toks)


# ---------------------------------------------------------------------------
# 4. Index (特殊フォーマット: 名前=ユニークフラグ,カラムリスト)
# ---------------------------------------------------------------------------
def parse_index(value: str) -> dict:
    # value 例: "users_ix1=0,user_name,birthday" または "=0,user_name,user_kana"
    name, _, rest = value.partition("=")
    parts = rest.split(",")
    unique = parts[0] if parts else ""
    columns = parts[1:] if len(parts) > 1 else []
    return {"index_name": name, "unique_flag": unique, "columns": columns}


def build_index(index_name: str, unique_flag, columns) -> str:
    name = index_name or ""
    cols = ",".join(columns)
    return f"{name}={unique_flag},{cols}" if cols else f"{name}={unique_flag}"


# ---------------------------------------------------------------------------
# 5. ファイル全体の参照整合性チェック
# ---------------------------------------------------------------------------
LINE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def parse_sections(text: str):
    """行ベースで [Section] ブロックに分割する。BOM・ヘッダコメントは無視。"""
    lines = text.splitlines()
    sections = []  # list of {"name": str, "start": int, "lines": [(key, raw_value, line_no)]}
    current = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current = {"name": stripped[1:-1], "start": i, "entries": []}
            sections.append(current)
            continue
        if current is None or not stripped:
            continue
        m = LINE_RE.match(line)
        if m:
            current["entries"].append((m.group(1), m.group(2), i))
    return sections


def validate_file(path: str):
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    sections = parse_sections(text)

    issues = []
    entity_names = {}  # lower(pname) -> (pname, section_index)
    entity_fields = {}  # pname -> set of field pnames

    for si, sec in enumerate(sections):
        if sec["name"] in ("Entity", "View", "Subtype"):
            pname = None
            fields = set()
            for key, raw, lineno in sec["entries"]:
                if key == "PName":
                    pname = token_to_value(raw) or raw.strip()
                if key == "Field":
                    f = parse_complex(raw, "Field")
                    if f.get("pname"):
                        fields.add(f["pname"])
            if pname:
                key_l = pname.lower()
                if key_l in entity_names:
                    issues.append(f"重複した物理名: '{pname}' (セクション#{si} と #{entity_names[key_l][1]})")
                else:
                    entity_names[key_l] = (pname, si)
                entity_fields[pname] = fields

    known_pnames_lower = set(entity_names.keys())

    for si, sec in enumerate(sections):
        if sec["name"] in ("Relation", "Relationship"):
            e1 = e2 = f1 = f2 = None
            for key, raw, lineno in sec["entries"]:
                if key == "Entity1":
                    e1 = raw.strip()
                elif key == "Entity2":
                    e2 = raw.strip()
                elif key == "Fields1":
                    f1 = [c.strip() for c in raw.split(",") if c.strip()]
                elif key == "Fields2":
                    f2 = [c.strip() for c in raw.split(",") if c.strip()]
            for label, ent in (("Entity1", e1), ("Entity2", e2)):
                if ent and ent.lower() not in known_pnames_lower:
                    issues.append(f"[Relation] (セクション#{si}) の {label}='{ent}' は存在しないエンティティを参照しています")
            for label, ent, flds in (("Fields1", e1, f1), ("Fields2", e2, f2)):
                if ent and ent.lower() in known_pnames_lower and flds:
                    real_pname = entity_names[ent.lower()][0]
                    known_cols = entity_fields.get(real_pname, set())
                    for c in flds:
                        if c not in known_cols:
                            issues.append(
                                f"[Relation] (セクション#{si}) の {label} 列 '{c}' はエンティティ '{ent}' に存在しません")
        if sec["name"] in ("Entity",):
            pname = None
            for key, raw, lineno in sec["entries"]:
                if key == "PName":
                    pname = token_to_value(raw) or raw.strip()
                if key == "Index":
                    idx = parse_index(raw)
                    known_cols = entity_fields.get(pname, set())
                    for c in idx["columns"]:
                        if c not in known_cols:
                            issues.append(
                                f"[Entity] '{pname}' の Index '{idx['index_name']}' が未知の列 '{c}' を参照しています")

    return issues


# ---------------------------------------------------------------------------
# 6. CLI
# ---------------------------------------------------------------------------

def main():
    # Windows環境ではコンソールのコードページによって日本語が文字化けすることがあるため、
    # 標準出力/標準エラーをUTF-8に固定する。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("escape", help="文字列をエスケープする")
    sp.add_argument("text")

    sp = sub.add_parser("unescape", help="エスケープ済み文字列を復元する")
    sp.add_argument("text")

    sp = sub.add_parser("parse", help="Complex値の行を JSON にデコードする")
    sp.add_argument("schema", choices=list(SCHEMAS.keys()))
    sp.add_argument("value", help="'キー=値' の値部分、またはキーを含む行全体")

    sp = sub.add_parser("build", help="JSON から Complex値の行を組み立てる")
    sp.add_argument("schema", choices=list(SCHEMAS.keys()))
    sp.add_argument("json_values", help='例: \'{"lname":"ID","pname":"id","dtype":"Serial","pk_order":0,"color":"$FFFFFFFF"}\'')

    sp = sub.add_parser("parse-index", help="Index行を JSON にデコードする")
    sp.add_argument("value")

    sp = sub.add_parser("build-index", help="JSON から Index行を組み立てる")
    sp.add_argument("json_values", help='例: \'{"index_name":"users_ix1","unique_flag":0,"columns":["user_name","birthday"]}\'')

    sp = sub.add_parser("validate", help=".a5er ファイルの参照整合性をチェックする")
    sp.add_argument("path")

    args = p.parse_args()

    if args.cmd == "escape":
        print(escape(args.text))
    elif args.cmd == "unescape":
        print(unescape(args.text))
    elif args.cmd == "parse":
        value = args.value
        if "=" in value and not value.strip().startswith('"'):
            # 'Field=...' のようにキー付きで渡された場合はキー部分を除去
            possible_key, _, rest = value.partition("=")
            if possible_key.strip() in (args.schema, "Field", "Position", "PageInfo", "DomainInfo", "CommonField"):
                value = rest
        print(json.dumps(parse_complex(value, args.schema), ensure_ascii=False, indent=2))
    elif args.cmd == "build":
        values = json.loads(args.json_values)
        print(build_complex(values, args.schema))
    elif args.cmd == "parse-index":
        value = args.value
        if value.strip().startswith("Index="):
            value = value.split("=", 1)[1]
        print(json.dumps(parse_index(value), ensure_ascii=False, indent=2))
    elif args.cmd == "build-index":
        values = json.loads(args.json_values)
        print(build_index(values.get("index_name", ""), values.get("unique_flag", 0), values.get("columns", [])))
    elif args.cmd == "validate":
        issues = validate_file(args.path)
        if not issues:
            print("OK: 参照整合性の問題は見つかりませんでした。")
        else:
            print(f"{len(issues)} 件の問題が見つかりました:")
            for i in issues:
                print(f" - {i}")
            sys.exit(1)


if __name__ == "__main__":
    main()
