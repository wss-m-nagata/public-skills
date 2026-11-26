"""開発構想ブックに編集可能なExcel図形を追加する。"""

from bisect import bisect_right
from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


_DRAWING = "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing"
_GRAPHICS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_CONTENT = "http://schemas.openxmlformats.org/package/2006/content-types"
_SHEET = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_FONT = "ＭＳ 明朝"
_LINE = "2D6586"
_BORDER = "A6A6A6"

ET.register_namespace("xdr", _DRAWING)
ET.register_namespace("a", _GRAPHICS)
ET.register_namespace("r", _OFFICE_REL)


def _element(parent, namespace, tag, **attributes):
    """名前空間付きのOpen XML要素を追加する。"""
    return ET.SubElement(parent, f"{{{namespace}}}{tag}", attributes)


class Diagram:
    """同じワークシートに置く図形をDrawingMLにまとめる。"""

    def __init__(self):
        """空の図形パーツと座標原点を初期化する。"""
        self.root = ET.Element(f"{{{_DRAWING}}}wsDr")
        self.x = 0
        self.y = 0

    def _anchor(self, x, y, width, height):
        """ポイント単位の座標からExcelの図形アンカーを作る。"""
        anchor = _element(self.root, _DRAWING, "absoluteAnchor")
        _element(anchor, _DRAWING, "pos", x=str(round((x + self.x) * 12700)),
                 y=str(round((y + self.y) * 12700)))
        _element(anchor, _DRAWING, "ext", cx=str(round(width * 12700)),
                 cy=str(round(height * 12700)))
        return anchor

    def align_to_cells(self, column_points, row_heights):
        """セルに結び付けて、画面表示やページ分割にも図形を追従させる。"""
        column_emu = round(column_points * 12700)
        row_boundaries = [0]
        for height in row_heights:
            row_boundaries.append(row_boundaries[-1] + round(height * 12700))
        for anchor in self.root:
            position, extent = anchor[:2]
            x, y = (int(position.attrib[key]) for key in ("x", "y"))
            width, height = (int(extent.attrib[key]) for key in ("cx", "cy"))
            anchor.tag = f"{{{_DRAWING}}}twoCellAnchor"
            del anchor[:2]
            for index, (tag, px, py) in enumerate((("from", x, y), ("to", x + width, y + height))):
                marker = ET.Element(f"{{{_DRAWING}}}{tag}")
                col, offset_x = divmod(px, column_emu)
                row = bisect_right(row_boundaries, py) - 1
                for name, value in (("col", col), ("colOff", offset_x), ("row", row),
                                    ("rowOff", py - row_boundaries[row])):
                    _element(marker, _DRAWING, name).text = str(value)
                anchor.insert(index, marker)

    def box(self, x, y, width, height, value="", *, fill=None, border=None,
            bold=False, size=10, color="202020", align="ctr", geometry="roundRect"):
        """図形の中に編集可能なテキストを配置する。"""
        anchor = self._anchor(x, y, width, height)
        shape = _element(anchor, _DRAWING, "sp")
        nonvisual = _element(shape, _DRAWING, "nvSpPr")
        _element(nonvisual, _DRAWING, "cNvPr", id=str(len(self.root)),
                 name=f"図形 {len(self.root)}")
        _element(nonvisual, _DRAWING, "cNvSpPr")
        props = _element(shape, _DRAWING, "spPr")
        geometry_element = _element(props, _GRAPHICS, "prstGeom", prst=geometry)
        adjustments = _element(geometry_element, _GRAPHICS, "avLst")
        if geometry == "roundRect":
            _element(adjustments, _GRAPHICS, "gd", name="adj", fmla="val 8000")
        self._color(props, fill)
        self._color(_element(props, _GRAPHICS, "ln", w="12700"), border)
        if value:
            body = _element(shape, _DRAWING, "txBody")
            _element(body, _GRAPHICS, "bodyPr", anchor="ctr", wrap="none",
                     lIns="50800", rIns="50800", tIns="0", bIns="0")
            _element(body, _GRAPHICS, "lstStyle")
            for text in value.split("\n"):
                paragraph = _element(body, _GRAPHICS, "p")
                _element(paragraph, _GRAPHICS, "pPr", algn=align)
                run = _element(paragraph, _GRAPHICS, "r")
                font = _element(run, _GRAPHICS, "rPr", lang="ja-JP", sz=str(size * 100),
                                b=str(int(bold)))
                self._color(font, color)
                _element(font, _GRAPHICS, "latin", typeface=_FONT)
                _element(font, _GRAPHICS, "ea", typeface=_FONT)
                _element(run, _GRAPHICS, "t").text = text
        _element(anchor, _DRAWING, "clientData")

    def _color(self, parent, color):
        """背景色または塗りつぶしなしを設定する。"""
        if color:
            _element(_element(parent, _GRAPHICS, "solidFill"), _GRAPHICS, "srgbClr", val=color)
        else:
            _element(parent, _GRAPHICS, "noFill")

    def arrow(self, points, *, color=_LINE, end=True, dashed=False):
        """折れ線をExcelのコネクタにし、終点だけに矢印を付ける。"""
        segments = [(first, second) for first, second in zip(points, points[1:]) if first != second]
        for index, ((x1, y1), (x2, y2)) in enumerate(segments):
            anchor = self._anchor(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            connector = _element(anchor, _DRAWING, "cxnSp")
            nonvisual = _element(connector, _DRAWING, "nvCxnSpPr")
            _element(nonvisual, _DRAWING, "cNvPr", id=str(len(self.root)),
                     name=f"矢印 {len(self.root)}")
            _element(nonvisual, _DRAWING, "cNvCxnSpPr")
            props = _element(connector, _DRAWING, "spPr")
            transform = _element(props, _GRAPHICS, "xfrm",
                                 flipH=str(int(x2 < x1)), flipV=str(int(y2 < y1)))
            _element(transform, _GRAPHICS, "off", x="0", y="0")
            _element(transform, _GRAPHICS, "ext", cx=str(round(abs(x2 - x1) * 12700)),
                     cy=str(round(abs(y2 - y1) * 12700)))
            geometry = _element(props, _GRAPHICS, "prstGeom", prst="line")
            _element(geometry, _GRAPHICS, "avLst")
            line = _element(props, _GRAPHICS, "ln", w="12700")
            self._color(line, color)
            if dashed:
                _element(line, _GRAPHICS, "prstDash", val="dash")
            if end and index == len(segments) - 1:
                _element(line, _GRAPHICS, "tailEnd", type="triangle")
            _element(anchor, _DRAWING, "clientData")


def flow(diagram, block, width):
    """工程・判断・受け渡しをスイムレーンに配置し、使用した高さを返す。"""
    lanes = block["lanes"]
    nodes = block.get("nodes")
    if nodes:
        edges = block["edges"]
    else:
        nodes = []
        for index, (lane, task, *issue) in enumerate(block["steps"]):
            text = f"{index + 1}. {task}"
            if issue and issue[0]:
                text += f"\n課題：{issue[0]}"
            nodes.append((index, lane, index, text))
        edges = [(index, index + 1) for index in range(len(nodes) - 1)]

    pitch = max(49, max(12 * len(node[3].split("\n")) + 34 for node in nodes))
    height = 31 + (1 + max(node[2] for node in nodes)) * pitch
    lane_width = (width - 30) / len(lanes)
    for index, lane in enumerate(lanes):
        x = 15 + lane_width * index
        diagram.box(x, 0, lane_width, height - 3, fill="FFFFFF", border=_BORDER, geometry="rect")
        diagram.box(x, 0, lane_width, 18, lane, fill="F2F2F2", border=_BORDER,
                    bold=True, geometry="rect")

    boxes = {}
    for identity, lane, row, label, *role in nodes:
        decision = role == ["decision"]
        box_height = max(28 if decision else 24, 12 * len(label.split("\n")) + 8)
        x = 27 + lanes.index(lane) * lane_width
        y = 24 + row * pitch + (pitch - 18 - box_height) / 2
        boxes[identity] = (x, y, lane_width - 24, box_height, label, decision)

    # 矢印を先に置き、その上に工程の図形を描く。
    for source, target, *options in edges:
        label = options[0] if options else ""
        route = options[1] if len(options) > 1 else ""
        x1, y1, w1, h1, *_ = boxes[source]
        x2, y2, w2, h2, *_ = boxes[target]
        center1, center2 = x1 + w1 / 2, x2 + w2 / 2
        mid1, mid2 = y1 + h1 / 2, y2 + h2 / 2
        if route in ("left", "right"):
            gutter = 5 if route == "left" else width - 5
            side1, side2 = (x1, x2) if route == "left" else (x1 + w1, x2 + w2)
            points = [(side1, mid1), (gutter, mid1), (gutter, mid2), (side2, mid2)]
            label_xy = (0 if route == "left" else width - 48, mid1 + 16)
        elif abs(mid1 - mid2) < 0.1:
            side1, side2 = (x1 + w1, x2) if x1 < x2 else (x1, x2 + w2)
            points = [(side1, mid1), (side2, mid2)]
            label_xy = ((side1 + side2) / 2 - 24, mid1 - 12)
        else:
            middle = (y1 + h1 + y2) / 2
            points = [(center1, y1 + h1), (center1, middle), (center2, middle), (center2, y2)]
            label_x = center1 + 4 if center1 == center2 else (center1 + center2) / 2 - 24
            label_xy = (label_x, middle - 12)
        diagram.arrow(points, dashed=mid2 < mid1)
        if label:
            diagram.box(*label_xy, 48, 12, label, color=_LINE, size=8,
                        align="l" if not route and center1 == center2 else "ctr")

    for x, y, w, h, label, decision in boxes.values():
        diagram.box(x, y, w, h, label, fill="FFEEDF" if decision else "E7F3F9",
                    border=_LINE, geometry="diamond" if decision else "roundRect")
    return height


def information_transfer(diagram, block, width):
    """情報の種類・伝達経路と、任意の業務段階を左右・上下に配置する。"""
    workflow = block.get("workflow")
    card_width = (width - 8 * (len(block["paths"]) - 1)) / len(block["paths"])
    mid = width / 2
    background = {"fill": "FAFAFA", "border": "DDDDDD"}
    diagram.box(0, 3, width, 46, **background)
    diagram.box(0, 7, width, 19, block["source"], bold=True, size=12)
    diagram.box(0, 26, width, 17, block.get("sourceDetail", ""), color="606060")

    if workflow:
        height = 490
        card_top, handover_top, action_top = 56, 253, 403
        diagram.box(0, 151, width, 33, workflow["trigger"], **background)
        diagram.box(0, 206, width, 94, **background)
        diagram.box(6, 211, width - 12, 18, workflow["handover"], bold=True, align="l", size=12)
        diagram.box(6, 230, width - 12, 16, workflow["handoverDetail"], align="l", color="606060")
        diagram.box(0, 324, width, 109, **background)
        diagram.box(0, 329, width, 18, block["recipient"], bold=True, size=12)
        diagram.box(0, 349, width, 18, workflow["receipt"], size=11)
        diagram.box(6, 385, width - 12, 15, workflow["actionsHeading"], align="l", color="606060")
        diagram.box(0, 455, width, 33, workflow["resume"], **background)
        for first, last in ((134, 146), (188, 201), (304, 318), (369, 381), (437, 450)):
            diagram.arrow([(mid, first), (mid, last)], color="606060")
    else:
        height = 257
        card_top, handover_top, action_top = 75, 166, 232
        diagram.box(0, 211, width, 45, **background)
        diagram.box(0, 214, width, 18, block["recipient"], bold=True, size=12)
        diagram.arrow([(mid, 53), (mid, 60)], color="606060", end=False)
        diagram.arrow([(card_width / 2, 60), (width - card_width / 2, 60)],
                      color="606060", end=False)

    for index, path in enumerate(block["paths"]):
        color = ("387DB8", "BD8026", "BE5156")[index]
        x = (card_width + 8) * index
        center = x + card_width / 2
        diagram.box(x, card_top, card_width, 73, fill="FFFFFF", border=color)
        diagram.box(x + 4, card_top + 4, card_width - 8, 17, path["name"],
                    color=color, bold=True, size=11, align="l")
        for line, example in enumerate(path["examples"]):
            diagram.box(x + 4, card_top + 23 + 14 * line, card_width - 8, 14, example, align="l")
        align = "l" if workflow else "ctr"
        diagram.box(x + 4, handover_top, card_width - 8, 16, path["method"], bold=True, align=align)
        diagram.box(x + 4, handover_top + 19, card_width - 8, 15,
                    path.get("condition", ""), color="606060", align=align)
        diagram.box(x + 4, action_top, card_width - 8, 22, path["recipientAction"],
                    **(background if workflow else {}))
        if not workflow:
            diagram.arrow([(center, 60), (center, 70)], color="606060", end=False)
            diagram.arrow([(center, 152), (center, 162)], color=color)
            if path["interrupted"]:
                diagram.box(x, 197, card_width, 13, "×", color=color, bold=True)
            else:
                diagram.arrow([(center, 198), (center, 206)], color=color)
    return height


def attach_drawings(workbook, drawings):
    """openpyxlが書いたブックに図形パーツと各シートからの参照を加える。"""
    output = BytesIO()
    with ZipFile(workbook) as source, ZipFile(output, "w", ZIP_DEFLATED) as result:
        content = ET.fromstring(source.read("[Content_Types].xml"))
        rewritten = {}
        for sheet_number, diagram in drawings.items():
            sheet_name = f"xl/worksheets/sheet{sheet_number}.xml"
            drawing_name = f"xl/drawings/drawing{sheet_number}.xml"
            relation_name = f"xl/worksheets/_rels/sheet{sheet_number}.xml.rels"
            sheet = ET.fromstring(source.read(sheet_name))
            relationships = (
                ET.fromstring(source.read(relation_name)) if relation_name in source.namelist()
                else ET.Element(f"{{{_PACKAGE_REL}}}Relationships")
            )
            # 内部リンクなど既存の参照を保持し、図形には専用のIDを使う。
            relation_id = "rIdConceptDrawing"
            _element(relationships, _PACKAGE_REL, "Relationship", Id=relation_id,
                     Type=f"{_OFFICE_REL}/drawing", Target=f"/{drawing_name}")
            _element(sheet, _SHEET, "drawing", **{f"{{{_OFFICE_REL}}}id": relation_id})
            _element(content, _CONTENT, "Override", PartName=f"/{drawing_name}",
                     ContentType="application/vnd.openxmlformats-officedocument.drawing+xml")
            rewritten.update({sheet_name: sheet, relation_name: relationships, drawing_name: diagram.root})
        rewritten["[Content_Types].xml"] = content
        for name in source.namelist():
            if name not in rewritten:
                result.writestr(name, source.read(name))
        for name, element in rewritten.items():
            result.writestr(name, ET.tostring(element, encoding="utf-8", xml_declaration=True))
    return output.getvalue()
