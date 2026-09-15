# -*- coding: utf-8 -*-
"""
openpyxlで読み込み→保存すると、シート上の図形(テキストボックス等、DrawingML形式のもの)が
失われる問題を補うスクリプト。

【背景】
Nablarch標準テンプレートの「表紙」シートには、「関係者外秘」「[プロジェクト名]」等を表示する
テキストボックスが図形として配置されている。これはセルの値ではなく独立した描画オブジェクトのため、
openpyxlで一度読み込んで保存すると（apply_mapping.py / duplicate_sheet.py / extend_table_rows.py
はいずれもこの読み込み→保存を行う）、跡形もなく消える。実機検証で確認済み。

セルのコメント(vmlDrawing)は openpyxl 自身が再生成するため影響を受けない。
影響を受けるのは xl/drawings/drawingN.xml で表現される図形（テキストボックス等）のみ。

【方針】
「元のxlsxファイル(図形あり)」と「加工後のxlsxファイル(図形なし)」をシート名で対応付け、
元ファイルの該当シートに図形があれば、そのXMLパーツをそのまま加工後ファイルへ移植する。
セルの値・書式には一切触れない。

使い方:
    python restore_shapes.py <元xlsxパス(図形あり)> <加工後xlsxパス(図形なし)> <出力xlsxパス> [置換JSON]

置換JSON(省略可): 表紙のテキストボックス内プレースホルダーを実値に置き換える場合に指定する。
    例: '{"プロジェクト名": "サンプルプロジェクト", "サブシステム名": "顧客管理システム"}'

例(通常はapply_mapping.py等がsave_with_shapes()経由で自動的に呼び出すため、
   単独で実行するのは復元に失敗した疑いがあるときの手動リカバリ時のみ):
    python restore_shapes.py テーブル一覧.xlsx 加工後.xlsx 出力.xlsx
"""

import sys
import re
import shutil
import zipfile
import posixpath
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent))
from xlsx_common import ensure_utf8_stdio

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"

ET.register_namespace("", NS_MAIN)


def _sheet_name_to_target(zf):
    """workbook.xml + workbook.xml.rels から {シート名: 'xl/worksheets/sheetN.xml'} を作る"""
    wb_root = ET.fromstring(zf.read("xl/workbook.xml"))
    rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))

    rid_to_target = {}
    for rel in rels_root.findall(f"{{{NS_RELS}}}Relationship"):
        rid_to_target[rel.get("Id")] = rel.get("Target")

    name_to_target = {}
    sheets_el = wb_root.find(f"{{{NS_MAIN}}}sheets")
    for sheet_el in sheets_el.findall(f"{{{NS_MAIN}}}sheet"):
        name = sheet_el.get("name")
        rid = sheet_el.get(f"{{{NS_R}}}id")
        target = rid_to_target.get(rid)
        if target is None:
            continue
        target = target.lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        name_to_target[name] = target
    return name_to_target


def _find_drawing_for_sheet(zf, sheet_target):
    """指定シートXMLに<drawing r:id=.../>があれば、その参照先パス(xl/drawings/drawingN.xml)を返す"""
    try:
        sheet_xml = zf.read(sheet_target).decode("utf-8")
    except KeyError:
        return None
    m = re.search(r'<drawing r:id="([^"]+)"\s*/>', sheet_xml)
    if not m:
        return None
    rid = m.group(1)

    sheet_dir = "/".join(sheet_target.split("/")[:-1])
    sheet_name_only = sheet_target.split("/")[-1]
    rels_path = f"{sheet_dir}/_rels/{sheet_name_only}.rels"
    try:
        rels_xml = zf.read(rels_path).decode("utf-8")
    except KeyError:
        return None

    rels_root = ET.fromstring(rels_xml)
    for rel in rels_root.findall(f"{{{NS_RELS}}}Relationship"):
        if rel.get("Id") == rid:
            target = rel.get("Target")
            # target は通常 "../drawings/drawing1.xml" のような相対パス
            resolved = (Path(sheet_dir) / target).as_posix()
            resolved = re.sub(r"/[^/]+/\.\./", "/", resolved)
            while "/../" in resolved:
                resolved = re.sub(r"[^/]+/\.\./", "", resolved, count=1)
            return resolved.replace("\\", "/")
    return None


def sheets_with_drawings(xlsx_path):
    """そのxlsxファイルで、図形(<drawing r:id=.../>)を持つシート名の集合を返す(検証用)"""
    result = set()
    with zipfile.ZipFile(xlsx_path) as zf:
        sheet_map = _sheet_name_to_target(zf)
        for name, target in sheet_map.items():
            if _find_drawing_for_sheet(zf, target) is not None:
                result.add(name)
    return result


def shape_anchor_counts(xlsx_path):
    """
    そのxlsxファイルで、シートごとに図形の個数(<xdr:twoCellAnchor>/<xdr:oneCellAnchor>の数)を返す(検証用)。

    sheets_with_drawings()は図形の「有無」しか見ないため、例えば元々1個だった図形が
    (誤って別のファイルから図形を復元したことで)2個に増えたケースを検知できない。
    このケースは実際に発生した事故で、表紙のセルベースのタイトルに、古い図形ベースの
    タイトル(サンプル/実例ファイルのもの)が重なって二重表示される原因になった。
    """
    result = {}
    with zipfile.ZipFile(xlsx_path) as zf:
        names = zf.namelist()
        sheet_map = _sheet_name_to_target(zf)
        for name, target in sheet_map.items():
            drawing_path = _find_drawing_for_sheet(zf, target)
            if drawing_path is None or drawing_path not in names:
                continue
            content = zf.read(drawing_path).decode("utf-8", errors="replace")
            count = len(re.findall(r"<xdr:twoCellAnchor", content)) + len(
                re.findall(r"<xdr:oneCellAnchor", content)
            )
            result[name] = count
    return result


def restore_shapes(original_path, processed_path, output_path, text_replacements=None):
    """
    text_replacements: {"プロジェクト名": "サンプルプロジェクト", "サブシステム名": "顧客管理システム"} のように、
    図形内のテキストランを置き換えたい場合に指定する(表紙のテキストボックスの
    `[プロジェクト名]`のようなプレースホルダーを実値に更新するため)。
    角括弧`[` `]`の扱いはテンプレートのXML構造により異なる。
    `<a:t>[プロジェクト名]</a:t>`のように角括弧と中身が同じテキストランに
    入っている場合は、角括弧ごと値に置き換わる(角括弧は残らない)。
    `<a:t>[</a:t><a:t>プロジェクト名</a:t><a:t>]</a:t>`のように角括弧が
    別のテキストランに分かれている場合は、中身のランだけが置き換わり角括弧は残る。
    """
    report = {"restored_sheets": [], "skipped_sheets": []}

    with zipfile.ZipFile(original_path) as zorig, zipfile.ZipFile(
        processed_path
    ) as zproc:
        orig_names = zorig.namelist()
        proc_names = zproc.namelist()

        orig_sheet_map = _sheet_name_to_target(zorig)
        proc_sheet_map = _sheet_name_to_target(zproc)

        # 加工後ファイル内で既に使われているdrawingファイル名の最大番号を調べ、衝突を避ける
        existing_drawing_nums = [
            int(m.group(1))
            for n in proc_names
            for m in [re.match(r"xl/drawings/restoredDrawing(\d+)\.xml$", n)]
            if m
        ]
        next_num = max(existing_drawing_nums, default=0) + 1

        proc_content_types = zproc.read("[Content_Types].xml").decode("utf-8")

        # 変更が必要なファイルをメモリ上に保持
        updated_files = {}  # path -> bytes
        new_files = {}  # path -> bytes
        removed_paths = set()  # openpyxlが自前生成したdrawingパーツ等、不要になったパス

        for sheet_name, orig_target in orig_sheet_map.items():
            if sheet_name not in proc_sheet_map:
                continue  # 加工後に存在しないシート(名前が変わった等)は対象外
            proc_target = proc_sheet_map[sheet_name]

            drawing_path = _find_drawing_for_sheet(zorig, orig_target)
            if drawing_path is None or drawing_path not in orig_names:
                report["skipped_sheets"].append(
                    {"sheet": sheet_name, "reason": "元シートに図形なし"}
                )
                continue

            # 1. 図形XMLをコピー(新しい名前を割り当てて衝突回避)
            new_drawing_name = f"xl/drawings/restoredDrawing{next_num}.xml"
            next_num += 1
            drawing_bytes = zorig.read(drawing_path)
            if text_replacements:
                drawing_text = drawing_bytes.decode("utf-8")
                for key, value in text_replacements.items():
                    if value is None:
                        continue
                    # テンプレートによって、角括弧が同じテキストランに含まれる場合
                    # (<a:t>[プロジェクト名]</a:t>) と、別ランに分かれている場合
                    # (<a:t>[</a:t><a:t>プロジェクト名</a:t><a:t>]</a:t>) の両方がある。
                    # 前者は角括弧ごと値に置き換え、後者は中身のランだけを置き換える(角括弧は残る)。
                    drawing_text = drawing_text.replace(
                        f"<a:t>[{key}]</a:t>", f"<a:t>{value}</a:t>"
                    )
                    drawing_text = drawing_text.replace(
                        f"<a:t>{key}</a:t>", f"<a:t>{value}</a:t>"
                    )
                drawing_bytes = drawing_text.encode("utf-8")
            new_files[new_drawing_name] = drawing_bytes

            # 1.5. drawing自身の.rels(画像等メディアへの参照)があれば、新しい名前で複製する。
            # ⚠️drawingが実際の画像(<xdr:pic>。insert_flow_diagram.py等で埋め込んだもの)を
            # 含む場合、その画像の関係(rId→xl/media/xxx.png)はdrawing自身の.relsに書かれている。
            # これをコピーし忘れると、drawing XMLは複製されても画像への参照が解決できず、
            # 次にopenpyxlで読み込んだ際にfind_images()が壊れる(実機で確認済み。
            # 純粋な図形/テキストボックスだけの場合はこの.relsが無いため、従来は不要だった)。
            drawing_dir_orig = "/".join(drawing_path.split("/")[:-1])
            drawing_file_orig = drawing_path.split("/")[-1]
            orig_drawing_rels_path = (
                f"{drawing_dir_orig}/_rels/{drawing_file_orig}.rels"
            )
            if orig_drawing_rels_path in orig_names:
                drawing_rels_bytes = zorig.read(orig_drawing_rels_path)
                new_drawing_dir = "/".join(new_drawing_name.split("/")[:-1])
                new_drawing_file = new_drawing_name.split("/")[-1]
                new_drawing_rels_path = (
                    f"{new_drawing_dir}/_rels/{new_drawing_file}.rels"
                )
                new_files[new_drawing_rels_path] = drawing_rels_bytes
                # このrelsが参照するメディア(画像等)が加工後ファイルに無ければ、元ファイルから
                # 実体をコピーする(openpyxlが同じパスでメディアを引き継いでいれば不要)。
                for media_target in re.findall(
                    r'Target="([^"]+)"', drawing_rels_bytes.decode("utf-8")
                ):
                    if media_target.startswith("/"):
                        media_path = media_target.lstrip("/")
                    else:
                        media_path = posixpath.normpath(
                            f"{drawing_dir_orig}/{media_target}"
                        )
                    if media_path in proc_names or media_path in new_files:
                        continue
                    if media_path in orig_names:
                        new_files[media_path] = zorig.read(media_path)
                        ext = media_path.rsplit(".", 1)[-1].lower()
                        default_decl = f'Extension="{ext}"'
                        if default_decl not in proc_content_types:
                            orig_ct = zorig.read("[Content_Types].xml").decode("utf-8")
                            m = re.search(
                                rf'<Default Extension="{ext}"[^>]*/>', orig_ct
                            )
                            if m:
                                proc_content_types = proc_content_types.replace(
                                    "</Types>", m.group(0) + "</Types>"
                                )

            # 2. Content_Types.xmlにOverrideを追加
            override = (
                f'<Override PartName="/{new_drawing_name}" '
                f'ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>'
            )
            if override not in proc_content_types:
                proc_content_types = proc_content_types.replace(
                    "</Types>", override + "</Types>"
                )

            # 3. 加工後シートの.rels を読み込み(無ければ新規作成)し、リレーションシップを追加
            sheet_dir = "/".join(proc_target.split("/")[:-1])
            sheet_file_only = proc_target.split("/")[-1]
            rels_path = f"{sheet_dir}/_rels/{sheet_file_only}.rels"

            if rels_path in proc_names:
                rels_xml = zproc.read(rels_path).decode("utf-8")
            else:
                rels_xml = (
                    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    f'<Relationships xmlns="{NS_RELS}"></Relationships>'
                )

            # 加工後シートXMLを先に読む(次のdrawing要素の重複チェックに使うため)
            if proc_target in updated_files:
                sheet_xml = updated_files[proc_target].decode("utf-8")
            else:
                sheet_xml = zproc.read(proc_target).decode("utf-8")

            # ⚠️シートに実際の画像(<xdr:pic>。insert_flow_diagram.py等が埋め込んだもの)が
            # 含まれている場合、openpyxlは保存時にそれを自力で認識し、自前のdrawingN.xmlと
            # <drawing r:id="..."/>要素を再生成する(DrawingML図形/テキストボックスと違い、
            # 単純な画像はopenpyxl自身が一部サポートしているため)。この状態で気づかずに
            # 本関数が新しい<drawing>要素を追加すると、1シートに<drawing>要素が2つできてしまい
            # 不正なOOXMLになる(openpyxlで再読込した際にfind_imagesが例外を投げて壊れる。
            # 実機で確認済み)。既存の<drawing r:id="..."/>があれば、それを解除し、対応する
            # リレーションシップも削除してから、元ファイルの完全な図形(画像+テキストボックス等)で
            # 上書きする。元ファイルの図形には既にこの画像自体が含まれているため、情報は失われない。
            existing_drawing_match = re.search(
                r'<drawing\b[^>]*\br:id="(rId\d+)"[^>]*/>', sheet_xml
            )
            if existing_drawing_match:
                old_rid = existing_drawing_match.group(1)
                sheet_xml = sheet_xml.replace(existing_drawing_match.group(0), "")
                old_rel_match = re.search(
                    rf'<Relationship[^>]*Id="{old_rid}"[^>]*/>', rels_xml
                )
                if old_rel_match:
                    rels_xml = rels_xml.replace(old_rel_match.group(0), "")
                    # openpyxlが自前生成したdrawingパーツ本体・そのrels・Content_Typesの
                    # 登録も丸ごと削除する。中途半端に残すと、そのdrawingパーツ自身のrels
                    # (画像メディアへの参照)が"孤立した部品"として残り、次にopenpyxlで
                    # 読み込んだ際にfind_images()が壊れる(実機で確認済み)。
                    target_match = re.search(
                        r'Target="([^"]+)"', old_rel_match.group(0)
                    )
                    if target_match:
                        raw_target = target_match.group(1)
                        if raw_target.startswith("/"):
                            old_drawing_path = raw_target.lstrip("/")
                        else:
                            old_drawing_path = posixpath.normpath(
                                f"{sheet_dir}/{raw_target}"
                            )
                        old_drawing_dir = "/".join(old_drawing_path.split("/")[:-1])
                        old_drawing_file = old_drawing_path.split("/")[-1]
                        old_drawing_rels_path = (
                            f"{old_drawing_dir}/_rels/{old_drawing_file}.rels"
                        )
                        removed_paths.add(old_drawing_path)
                        removed_paths.add(old_drawing_rels_path)
                        old_override = re.search(
                            rf'<Override PartName="/{re.escape(old_drawing_path)}"[^>]*/>',
                            proc_content_types,
                        )
                        if old_override:
                            proc_content_types = proc_content_types.replace(
                                old_override.group(0), ""
                            )

            existing_rids = re.findall(r'Id="rId(\d+)"', rels_xml)
            new_rid_num = max([int(x) for x in existing_rids], default=0) + 1
            new_rid = f"rId{new_rid_num}"
            rel_target = f"../drawings/{new_drawing_name.split('/')[-1]}"
            new_rel = (
                f'<Relationship Id="{new_rid}" '
                f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" '
                f'Target="{rel_target}"/>'
            )
            rels_xml = rels_xml.replace(
                "</Relationships>", new_rel + "</Relationships>"
            )
            updated_files[rels_path] = rels_xml.encode("utf-8")

            # 4. 加工後シートXMLに<drawing r:id="..."/>を挿入(legacyDrawingの直前、無ければ</worksheet>の直前)
            # <drawing r:id="..."/> を使うには、ルート要素にr名前空間の宣言が必要
            # (openpyxlの出力は、他にr:属性を使う要素が無いシートではxmlns:rを省略するため)
            if "xmlns:r=" not in sheet_xml.split(">", 1)[0]:
                sheet_xml = sheet_xml.replace(
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"',
                    f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                    f'xmlns:r="{NS_R}"',
                    1,
                )

            drawing_el = f'<drawing r:id="{new_rid}"/>'
            if "<legacyDrawing" in sheet_xml:
                sheet_xml = sheet_xml.replace(
                    "<legacyDrawing", drawing_el + "<legacyDrawing", 1
                )
            elif "<extLst>" in sheet_xml:
                sheet_xml = sheet_xml.replace("<extLst>", drawing_el + "<extLst>", 1)
            else:
                sheet_xml = sheet_xml.replace(
                    "</worksheet>", drawing_el + "</worksheet>"
                )
            updated_files[proc_target] = sheet_xml.encode("utf-8")

            report["restored_sheets"].append(
                {"sheet": sheet_name, "drawing": new_drawing_name}
            )

        updated_files["[Content_Types].xml"] = proc_content_types.encode("utf-8")

        # 出力zipを組み立て: 加工後ファイルの全エントリを基準に、更新分は差し替え、新規分は追加
        # (updated_files には、加工後ファイルに元々存在しなかった新規.relsファイル等も
        #  含まれ得るため、zproc.infolist()のループだけでなく、new_files/updated_filesの
        #  両方について「まだ書き込んでいないパス」を漏れなく追加する)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            written = set()
            for item in zproc.infolist():
                if item.filename in removed_paths:
                    continue
                data = updated_files.get(item.filename, zproc.read(item.filename))
                zout.writestr(item, data)
                written.add(item.filename)
            for path, data in list(new_files.items()) + list(updated_files.items()):
                if path not in written and path not in removed_paths:
                    zout.writestr(path, data)
                    written.add(path)

    return report


def main():
    ensure_utf8_stdio()
    import json

    original_path = sys.argv[1]
    processed_path = sys.argv[2]
    output_path = sys.argv[3]
    text_replacements = json.loads(sys.argv[4]) if len(sys.argv) > 4 else None

    report = restore_shapes(
        original_path, processed_path, output_path, text_replacements
    )

    print(f"=== 図形復元結果: {output_path} ===")
    if report["restored_sheets"]:
        for r in report["restored_sheets"]:
            print(f"  復元: シート『{r['sheet']}』に {r['drawing']} を移植")
    else:
        print("  復元対象なし(元ファイルに図形が見つかりませんでした)")
    if report["skipped_sheets"]:
        for s in report["skipped_sheets"]:
            print(f"  スキップ: シート『{s['sheet']}』({s['reason']})")


if __name__ == "__main__":
    main()
