#!/usr/bin/env python3
"""Генератор drawio-диаграмм документации Promelectron (единый тёмный стиль).

Эмитит `.drawio` (XML) для всех диаграмм из декларативных описаний:
Порядок чтения — по префиксам 01–08 (от общего к частному):
  - docs/architecture/01-c4-system-context.drawio — C4 Level 1 (System context)
  - docs/architecture/02-c4-containers.drawio     — C4 Level 2 (Containers)
  - docs/flows/03..07-<flow>.drawio               — sequence-флоу (5 шт.)
  - docs/08-ai-agent-pipeline.drawio              — flowchart пайплайна агентов

Рендер SVG (headless drawio, dbus-ошибки в stderr игнорируются):
  ~/tools/drawio -x -f svg -o <out.svg> <in.drawio>

Или всё сразу:
  python scripts/docs/gen_diagrams.py --render        # drawio из $DRAWIO или ~/tools/drawio

Стиль — тёмная тема (референсы: C4 system context / containers / sequence):
  - фон страницы #1e1f2b (атрибут background на mxGraphModel);
  - роли [Person] — светло-голубые боксы с тёмным текстом;
  - основная система — ярко-синий бокс, внешние системы — серые;
  - граница системы — пунктирный скруглённый фрейм;
  - стрелки ортогональные (edgeStyle=orthogonalEdgeStyle), светлые подписи;
  - sequence: тёмно-синие боксы участников с голубой рамкой, пунктирные
    лайфлайны, сплошные стрелки = вызовы, пунктирные = ответы,
    жёлтые sticky-notes, opt-фреймы с пунктирной рамкой и табом.

Компромисс ради детерминированного рендера: подписи sequence-сообщений —
отдельные text-ноды над стрелками (не edge labels), стрелки привязаны
к абсолютным точкам лайфлайнов (не магнитятся при перетаскивании в GUI).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Палитра (тёмная тема, по референсным скриншотам)
# ---------------------------------------------------------------------------
BG = "#1e1f2b"

PERSON_FILL = "#8fb8e0"
PERSON_FONT = "#10121a"
SYSTEM_FILL = "#3d85c6"
SYSTEM_FONT = "#ffffff"
CONTAINER_FILL = "#2d6ca8"
CONTAINER_FONT = "#eaf2fb"
EXTERNAL_FILL = "#5a5d66"
EXTERNAL_FONT = "#e8eaf0"
BOUNDARY_STROKE = "#6ea8fe"
BOUNDARY_FONT = "#6ea8fe"
ARROW = "#9aa7bd"
EDGE_FONT = "#c9d1d9"
TITLE_FONT = "#e8eaf0"

SEQ_BOX_FILL = "#1f2a44"
SEQ_BOX_STROKE = "#5b9bd5"
SEQ_BOX_FONT = "#d7e3f4"
LIFELINE = "#55617a"
CALL = "#8ab4f8"
MSG_FONT = "#c9d1d9"
NOTE_FILL = "#fff9c4"
NOTE_STROKE = "#d6c656"
NOTE_FONT = "#3a3800"
FRAME_STROKE = "#8ab4f8"
FRAME_FONT = "#8ab4f8"

OK_FONT = "#7bd88f"
ERR_FONT = "#ef6a6a"


def esc(s: str) -> str:
    """XML-escape для value-атрибутов (HTML-разметка хранится escaped)."""
    return escape(s, {'"': "&quot;"})


def br(s: str) -> str:
    """Переводы строк в HTML-разметку drawio."""
    return s.replace("\n", "<br>")


# ---------------------------------------------------------------------------
# Базовый построитель диаграммы
# ---------------------------------------------------------------------------
class Diagram:
    def __init__(self, name: str, page_w: int, page_h: int):
        self.name = name
        self.page_w = page_w
        self.page_h = page_h
        self._cells: list[str] = []
        self._n = 0

    def _id(self, prefix: str) -> str:
        self._n += 1
        return f"{prefix}{self._n}"

    def vertex(self, x: float, y: float, w: float, h: float, value: str,
               style: str, vid: str | None = None) -> str:
        vid = vid or self._id("v")
        self._cells.append(
            f'<mxCell id="{vid}" value="{esc(br(value))}" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
        )
        return vid

    def text(self, x: float, y: float, w: float, h: float, value: str,
             style_extra: str = "", size: int = 12, color: str = MSG_FONT,
             align: str = "left", valign: str = "bottom", bold: bool = False) -> str:
        b = "fontStyle=1;" if bold else ""
        style = (f"text;html=1;strokeColor=none;fillColor=none;fontColor={color};"
                 f"fontSize={size};align={align};verticalAlign={valign};whiteSpace=wrap;{b}{style_extra}")
        return self.vertex(x, y, w, h, value, style)

    def edge(self, value: str, style: str, source: str | None = None,
             target: str | None = None,
             src_pt: tuple[float, float] | None = None,
             dst_pt: tuple[float, float] | None = None,
             points: list[tuple[float, float]] | None = None,
             eid: str | None = None) -> str:
        eid = eid or self._id("e")
        attrs = f'id="{eid}" value="{esc(br(value))}" style="{style}" edge="1" parent="1"'
        if source:
            attrs += f' source="{source}"'
        if target:
            attrs += f' target="{target}"'
        geo = '<mxGeometry relative="1" as="geometry">'
        if src_pt:
            geo += f'<mxPoint x="{src_pt[0]}" y="{src_pt[1]}" as="sourcePoint"/>'
        if dst_pt:
            geo += f'<mxPoint x="{dst_pt[0]}" y="{dst_pt[1]}" as="targetPoint"/>'
        if points:
            geo += "<Array as='points'>".replace("'", '"')
            for px, py in points:
                geo += f'<mxPoint x="{px}" y="{py}"/>'
            geo += "</Array>"
        geo += "</mxGeometry>"
        self._cells.append(f"<mxCell {attrs}>{geo}</mxCell>")
        return eid

    def routed(self, src: str, dst: str, exit_: tuple[float, float],
               entry: tuple[float, float],
               points: list[tuple[float, float]] | None = None,
               dashed: bool = False) -> str:
        """Ортогональная связь с явными точками выхода/входа и waypoints —
        детерминированный маршрут без сюрпризов авто-роутера."""
        d = "dashed=1;dashPattern=4 4;" if dashed else ""
        style = (f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor={ARROW};"
                 f"fontColor={EDGE_FONT};fontSize=12;endArrow=block;endFill=1;"
                 f"labelBackgroundColor=none;jettySize=auto;"
                 f"exitX={exit_[0]};exitY={exit_[1]};exitDx=0;exitDy=0;"
                 f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;{d}")
        return self.edge("", style, src, dst, points=points)

    def xml(self) -> str:
        body = "\n        ".join(self._cells)
        return (
            '<mxfile host="app.diagrams.net" agent="gen_diagrams.py" version="24.7.5" type="device">\n'
            f'  <diagram name="{esc(self.name)}" id="{esc(self.name)}">\n'
            f'    <mxGraphModel dx="1000" dy="700" grid="0" gridSize="10" guides="1" tooltips="1" '
            f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{self.page_w}" '
            f'pageHeight="{self.page_h}" math="0" shadow="0" background="{BG}">\n'
            "      <root>\n"
            '        <mxCell id="0"/>\n'
            '        <mxCell id="1" parent="0"/>\n'
            f"        {body}\n"
            "      </root>\n"
            "    </mxGraphModel>\n"
            "  </diagram>\n"
            "</mxfile>\n"
        )


# ---------------------------------------------------------------------------
# Стили C4
# ---------------------------------------------------------------------------
def person_style() -> str:
    return (f"rounded=1;arcSize=12;whiteSpace=wrap;html=1;fillColor={PERSON_FILL};"
            f"strokeColor=none;fontColor={PERSON_FONT};fontSize=13;align=center;"
            f"verticalAlign=middle;spacing=6;")


def system_style() -> str:
    return (f"rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor={SYSTEM_FILL};"
            f"strokeColor=none;fontColor={SYSTEM_FONT};fontSize=13;align=center;"
            f"verticalAlign=middle;spacing=8;")


def container_style() -> str:
    return (f"rounded=1;arcSize=8;whiteSpace=wrap;html=1;fillColor={CONTAINER_FILL};"
            f"strokeColor=#5b9bd5;fontColor={CONTAINER_FONT};fontSize=13;align=center;"
            f"verticalAlign=middle;spacing=6;")


def external_style() -> str:
    return (f"rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor={EXTERNAL_FILL};"
            f"strokeColor=none;fontColor={EXTERNAL_FONT};fontSize=13;align=center;"
            f"verticalAlign=middle;spacing=6;")


def boundary_style(color: str = BOUNDARY_STROKE, font: str = BOUNDARY_FONT) -> str:
    return (f"rounded=1;arcSize=2;fillColor=none;strokeColor={color};dashed=1;"
            f"dashPattern=4 4;fontColor={font};fontSize=13;align=left;"
            f"verticalAlign=top;spacingLeft=10;spacingTop=6;html=1;fontStyle=1;")


def cylinder_style(dashed: bool = False) -> str:
    d = "dashed=1;dashPattern=4 4;" if dashed else ""
    return (f"shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;"
            f"size=14;fillColor={CONTAINER_FILL};strokeColor=#5b9bd5;fontColor={CONTAINER_FONT};"
            f"fontSize=13;align=center;{d}")


def c4_edge_style(dashed: bool = False) -> str:
    d = "dashed=1;dashPattern=4 4;" if dashed else ""
    return (f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor={ARROW};"
            f"fontColor={EDGE_FONT};fontSize=12;endArrow=block;endFill=1;"
            f"labelBackgroundColor=none;jettySize=auto;{d}")


def title(d: Diagram, text: str, sub: str | None = None, w: int | None = None):
    w = w or d.page_w - 80
    d.text(40, 24, w, 30, f"<b>{text}</b>", size=18, color=TITLE_FONT, valign="middle")
    if sub:
        d.text(40, 58, w, 20, sub, size=12, color="#8b93a8", valign="middle")


def person_value(name: str, desc: str) -> str:
    return f"<b>{name}</b><br>[Person]<br>{desc}"


# ---------------------------------------------------------------------------
# C4 Level 1 — System context
# ---------------------------------------------------------------------------
def gen_c4_l1() -> Diagram:
    d = Diagram("01 · C4 Level 1 — System context", 1360, 780)
    title(d, "01 · C4 Level 1 — System context",
          "Promelectron — интернет-магазин электроники: роли, система и внешние интеграции")

    # Роли слева
    buyer = d.vertex(60, 140, 230, 110, person_value("Покупатель", "каталог, корзина, заказы, оплата"), person_style())
    admin = d.vertex(60, 330, 230, 110, person_value("Администратор", "товары, категории, заказы, фичатоглы"), person_style())
    supplier = d.vertex(60, 520, 230, 110, person_value("Поставщик", "свои товары, CDEK-настройки"), person_style())

    # Граница системы + система
    d.vertex(440, 160, 460, 450, "Promelectron [System boundary]", boundary_style())
    system = d.vertex(520, 290, 300, 190,
                      "<b>Promelectron</b><br>[FastAPI backend + Vue SPA]<br><br>"
                      "каталог · корзина · заказы<br>платежи ЮKassa · доставка CDEK<br>"
                      "уведомления · синхронизация 1С",
                      system_style())

    # Внешние системы справа
    yk = d.vertex(1100, 140, 240, 110,
                  "<b>ЮKassa</b><br>[External]<br>платежи, возвраты", external_style())
    cdek = d.vertex(1100, 330, 240, 110,
                    "<b>CDEK</b><br>[External]<br>тарифы, заказы на доставку", external_style())
    onec = d.vertex(1100, 520, 240, 110,
                    "<b>1С (ERP)</b><br>[External]<br>мастер-данные каталога", external_style())

    # Связи ролей → система (явные маршруты, подписи над горизонтальными сегментами)
    d.routed(buyer, system, (1, 0.5), (0, 0.2), points=[(465, 195), (465, 328)])
    d.text(295, 140, 165, 50, "каталог · корзина ·\nзаказы · оплата\nHTTPS · JWT", color=EDGE_FONT, valign="top")

    d.routed(admin, system, (1, 0.5), (0, 0.5))
    d.text(295, 322, 150, 50, "админ-панель\nтовары · заказы\nHTTPS · JWT", color=EDGE_FONT, valign="top")

    d.routed(supplier, system, (1, 0.5), (0, 0.8), points=[(465, 575), (465, 442)])
    d.text(295, 512, 165, 50, "свои товары ·\nCDEK-настройки\nHTTPS · JWT", color=EDGE_FONT, valign="top")

    # Связи система ↔ внешние системы
    d.routed(system, yk, (1, 0.2), (0, 0.5), points=[(960, 328), (960, 195)])
    d.text(970, 232, 125, 55, "create/cancel/refund\nwebhook\npayment.succeeded", color=EDGE_FONT, valign="top")

    d.routed(system, cdek, (1, 0.5), (0, 0.5))
    d.text(912, 332, 180, 40, "тарифы · создание заказа\nwebhook статусов · polling", color=EDGE_FONT, valign="top")

    d.routed(onec, system, (0, 0.5), (1, 0.85), points=[(960, 575), (960, 451)])
    d.text(968, 466, 125, 70, "JSON-батчи изменений\nPOST /onec/webhook/\nX-1C-Api-Key", color=EDGE_FONT, valign="top")
    return d


# ---------------------------------------------------------------------------
# C4 Level 2 — Containers
# ---------------------------------------------------------------------------
def gen_c4_l2() -> Diagram:
    d = Diagram("02 · C4 Level 2 — Containers", 1600, 1000)
    title(d, "02 · C4 Level 2 — Containers",
          "Каждый бокс — сервис docker-compose / k8s. Пунктирный сабграф — опциональный профиль.")

    # Person сверху
    person = d.vertex(630, 70, 340, 80,
                      "<b>Покупатель / Администратор / Поставщик</b><br>[Person]", person_style())

    # Граница системы
    d.vertex(110, 200, 1090, 760, "Promelectron — docker compose up · k8s (helm)", boundary_style())

    # Контейнеры
    frontend = d.vertex(650, 240, 300, 90,
                        "<b>frontend</b> — Vue 3 SPA + nginx<br>[Container]<br>веб-UI · localStorage гостевой корзины",
                        container_style())
    api = d.vertex(650, 400, 300, 90,
                   "<b>api</b> — FastAPI<br>[Container]<br>REST /api/v1 · WebSocket /ws/notifications",
                   container_style())
    jw = d.vertex(150, 580, 250, 90,
                  "<b>job-worker</b><br>[Container]<br>jobs: CDEK_CREATE_ORDER ·<br>CDEK_SYNC_ORDER_STATUS · ONEC_APPLY_CHANGES",
                  container_style())
    pg = d.vertex(450, 580, 200, 90,
                  "<b>postgres</b><br>[Container: PostgreSQL 16]<br>OLTP · jobs · cdek_status_history",
                  cylinder_style())
    redis = d.vertex(700, 580, 170, 90,
                     "<b>redis</b><br>[Container]<br>кэш · rate limit ·<br>feature flags",
                     cylinder_style())
    minio = d.vertex(920, 580, 170, 90,
                     "<b>minio</b><br>[Container]<br>uploads ·<br>onec-intake (S3)",
                     cylinder_style())

    # Опциональный профиль: поиск
    d.vertex(150, 740, 420, 110, "опционально: поиск (feature flag catalog_search_meilisearch)",
             boundary_style(color="#7bd88f", font="#7bd88f"))
    meili = d.vertex(250, 772, 220, 62,
                     "<b>meilisearch</b><br>[Container]<br>поиск и фасеты каталога",
                     cylinder_style(dashed=True))

    # Внешние системы справа
    yk = d.vertex(1290, 230, 240, 90,
                  "<b>ЮKassa</b><br>[External]<br>платежи · возвраты", external_style())
    cdek = d.vertex(1290, 410, 240, 90,
                    "<b>CDEK API</b><br>[External]<br>заказы · статусы", external_style())
    onec = d.vertex(1290, 590, 240, 90,
                    "<b>1С (ERP)</b><br>[External]<br>выгрузки каталога", external_style())

    # Связи: пользовательская цепочка
    d.routed(person, frontend, (0.5, 1), (0.5, 0))
    d.text(812, 185, 90, 20, "HTTPS", color=EDGE_FONT)
    d.routed(frontend, api, (0.5, 1), (0.5, 0))
    d.text(812, 348, 160, 20, "JSON · HTTPS · JWT", color=EDGE_FONT)

    # api → хранилища (горизонтали разведены по y, чтобы не сливались)
    d.routed(api, jw, (0.15, 1), (0.5, 0), points=[(695, 530), (275, 530)])
    d.text(420, 500, 280, 20, "ставит jobs · poll · SELECT FOR UPDATE", color=EDGE_FONT)
    d.routed(api, pg, (0.45, 1), (0.5, 0), points=[(785, 552), (550, 552)])
    d.text(800, 520, 130, 20, "SQLAlchemy async", color=EDGE_FONT)
    d.routed(api, redis, (0.62, 1), (0.5, 0), points=[(836, 572), (785, 572)])
    d.text(848, 540, 110, 20, "кэш · rate limit", color=EDGE_FONT)
    d.routed(api, minio, (0.85, 1), (0.5, 0), points=[(905, 558), (1005, 558)])
    d.text(915, 516, 100, 20, "S3 · uploads", color=EDGE_FONT)
    d.routed(api, meili, (0, 0.5), (0, 0.5), points=[(125, 445), (125, 803)], dashed=True)
    d.text(200, 406, 170, 36, "поиск · переиндексация\n(feature flag)", color=EDGE_FONT, valign="top")

    # api/job-worker ↔ внешние системы
    d.routed(api, yk, (1, 0.25), (0, 0.5), points=[(1130, 422), (1130, 275)])
    d.text(1140, 330, 145, 40, "create/cancel/refund\nwebhook payment.succeeded", color=EDGE_FONT, valign="top")
    d.routed(api, cdek, (1, 0.55), (0, 0.5), points=[(1210, 449)])
    d.text(960, 462, 240, 20, "заказы · webhook + polling статусов", color=EDGE_FONT)
    d.routed(jw, cdek, (0.5, 1), (0, 0.7), points=[(275, 710), (1245, 710), (1245, 483)])
    d.text(700, 718, 300, 20, "CDEK_CREATE_ORDER · CDEK_SYNC_ORDER_STATUS", color=EDGE_FONT, valign="top")
    d.routed(onec, api, (0, 0.5), (1, 0.85), points=[(1150, 635), (1150, 476)])
    d.text(965, 486, 250, 36, "JSON-батчи · X-1C-Api-Key\nZIP intake → MinIO", color=EDGE_FONT, valign="top")
    return d


# ---------------------------------------------------------------------------
# Sequence builder
# ---------------------------------------------------------------------------
class SeqDiagram(Diagram):
    """Sequence-диаграмма: участники по X, сообщения по Y.

    Инвариант: ``_y`` — верх следующего ряда. Подпись сообщения рисуется
    внутри его ряда (в [_y, _y + label_h]), линия — под подписью; так label
    никогда не залезает на предыдущий ряд (note / opt-фрейм / боксы).
    """

    BOX_W = 170
    BOX_H = 44
    GAP = 60
    MARGIN = 60
    TOP_Y = 110
    LINE_H = 17          # высота строки подписи
    AFTER_LINE = 22      # зазор после линии сообщения
    LOOP_W = 46
    LOOP_H = 26

    def __init__(self, name: str, participants: list[tuple[str, str]],
                 subtitle: str | None = None):
        self.participants = participants
        n = len(participants)
        pw = max(1100, 2 * self.MARGIN + n * self.BOX_W + (n - 1) * self.GAP)
        # высота вычисляется в finalize
        super().__init__(name, pw, 100)
        self.subtitle = subtitle
        self._xs: dict[str, float] = {}
        for i, (key, _label) in enumerate(participants):
            self._xs[key] = self.MARGIN + i * (self.BOX_W + self.GAP) + self.BOX_W / 2
        self._msg_rows: list[tuple] = []   # (kind, payload, y)
        self._y = self.TOP_Y + self.BOX_H + 20
        self._opt_stack: list[tuple[str, str, float, float, float]] = []

    @staticmethod
    def _label_h(label: str) -> int:
        return (label.count("\n") + 1) * SeqDiagram.LINE_H

    def message(self, a: str, b: str, label: str, dashed: bool = False):
        lh = self._label_h(label)
        self._msg_rows.append(("msg", (a, b, label, dashed, lh), self._y))
        self._y += lh + 3 + self.AFTER_LINE

    def self_message(self, a: str, label: str):
        self._msg_rows.append(("self", (a, label), self._y))
        self._y += self.LOOP_H + 14

    def note(self, a: str, b: str, text: str):
        """Sticky-note, растянутый между lifelines a..b (включительно)."""
        xa = self._xs[a] - self.BOX_W / 2
        xb = self._xs[b] + self.BOX_W / 2
        w = max(260, xb - xa)
        chars_per_line = int(w / 7.0)
        lines = max(1, -(-len(text) // chars_per_line)) + text.count("\n")
        h = 16 + lines * 17 + 10
        self._msg_rows.append(("note", (xa, w, h, text), self._y))
        self._y += h + 20

    def begin_opt(self, tab: str, condition: str, a: str, b: str):
        xa = self._xs[a] - self.BOX_W / 2 - 25
        xb = self._xs[b] + self.BOX_W / 2 + 25
        self._opt_stack.append((tab, condition, self._y, xa, xb))
        self._y += 30   # таб + условие фрейма

    def end_opt(self):
        tab, condition, y0, xa, xb = self._opt_stack.pop()
        self._msg_rows.append(("opt", (tab, condition, y0, self._y + 6, xa, xb), y0))
        self._y += 30

    def finalize(self):
        # Заголовок
        title(self, self.name, self.subtitle, w=self.page_w - 80)

        # Боксы участников (верх/низ) + лайфлайны
        bottom_y = self._y + 40
        for key, label in self.participants:
            cx = self._xs[key]
            style = (f"rounded=0;whiteSpace=wrap;html=1;fillColor={SEQ_BOX_FILL};"
                     f"strokeColor={SEQ_BOX_STROKE};fontColor={SEQ_BOX_FONT};fontSize=13;")
            top = self.vertex(cx - self.BOX_W / 2, self.TOP_Y, self.BOX_W, self.BOX_H,
                              label, style)
            bot = self.vertex(cx - self.BOX_W / 2, bottom_y, self.BOX_W, self.BOX_H,
                              label, style)
            self.edge("", (f"html=1;strokeColor={LIFELINE};dashed=1;dashPattern=4 4;"
                           f"endArrow=none;strokeWidth=1;"),
                      source=top, target=bot,
                      eid=self._id("ll"))

        # Сообщения / заметки / фреймы
        for kind, payload, y in self._msg_rows:
            if kind == "msg":
                a, b, label, dashed, lh = payload
                xa, xb = self._xs[a], self._xs[b]
                line_y = y + lh + 3
                d = "dashed=1;dashPattern=6 4;" if dashed else ""
                self.edge("", (f"html=1;strokeColor={CALL};strokeWidth=1.5;endArrow=block;"
                               f"endFill=1;{d}"),
                          src_pt=(xa, line_y), dst_pt=(xb, line_y))
                lx = min(xa, xb) + 10
                lw = abs(xb - xa) - 20
                self.text(lx, y, lw, lh, label,
                          size=12, color=MSG_FONT, valign="bottom")
            elif kind == "self":
                a, label = payload
                xa = self._xs[a]
                self.edge("", (f"html=1;strokeColor={CALL};strokeWidth=1.5;endArrow=block;"
                               f"endFill=1;"),
                          src_pt=(xa, y), dst_pt=(xa, y + self.LOOP_H),
                          points=[(xa + self.LOOP_W, y), (xa + self.LOOP_W, y + self.LOOP_H)])
                lines = label.count("\n") + 1
                self.text(xa + self.LOOP_W + 10, y + self.LOOP_H / 2 - lines * 8.5 - 2,
                          340, lines * 17, label, size=12, color=MSG_FONT, valign="top")
            elif kind == "note":
                xa, w, h, text = payload
                self.vertex(xa, y, w, h, text,
                            (f"shape=note;whiteSpace=wrap;html=1;fillColor={NOTE_FILL};"
                             f"strokeColor={NOTE_STROKE};fontColor={NOTE_FONT};fontSize=12;"
                             f"align=center;verticalAlign=middle;size=14;spacing=6;"))
            elif kind == "opt":
                tab, condition, y0, y1, xa, xb = payload
                self.vertex(xa, y0, xb - xa, y1 - y0, "",
                            (f"rounded=0;fillColor=none;strokeColor={FRAME_STROKE};"
                             f"dashed=1;dashPattern=4 4;html=1;"))
                self.vertex(xa, y0, 46, 22, tab,
                            (f"rounded=0;fillColor={SEQ_BOX_FILL};strokeColor={FRAME_STROKE};"
                             f"fontColor={FRAME_FONT};fontSize=12;html=1;fontStyle=1;"))
                self.text(xa + 56, y0 + 2, xb - xa - 66, 18, condition,
                          size=12, color=FRAME_FONT, valign="middle")

        self.page_h = int(bottom_y + self.BOX_H + 50)
        return self


# ---------------------------------------------------------------------------
# Sequence-флоу
# ---------------------------------------------------------------------------
def gen_order_checkout() -> SeqDiagram:
    s = SeqDiagram(
        "03 · Оформление заказа и оплата (order-checkout)",
        [("buyer", "Покупатель"), ("fe", "Frontend (Vue)"), ("api", "Backend API (FastAPI)"),
         ("pg", "PostgreSQL"), ("yk", "ЮKassa"), ("jw", "job_worker")],
        "POST /api/v1/orders/create/ → платёж ЮKassa → webhook payment.succeeded → job CDEK_CREATE_ORDER")
    s.message("buyer", "fe", "оформить заказ (корзина → чекаут)")
    s.message("fe", "api", "POST /api/v1/orders/create/")
    s.message("api", "pg", "BEGIN · SELECT … FOR UPDATE\n(блокировка строк stock)")
    s.message("api", "pg", "списание stock · INSERT order\nCOMMIT")
    s.message("api", "fe", "201 · order_id", dashed=True)
    s.message("fe", "api", "POST /api/v1/payments/{order_id}/")
    s.message("api", "yk", "создать платёж\n(amount, return_url)")
    s.message("yk", "api", "payment id + confirmation_url", dashed=True)
    s.message("api", "fe", "redirect URL", dashed=True)
    s.message("buyer", "yk", "оплата на странице ЮKassa")
    s.note("api", "pg", "SELECT FOR UPDATE держит блокировку строк stock до COMMIT — "
                        "параллельные чекауты не уйдут в минус")
    s.message("yk", "api", "webhook POST /api/v1/payments/yookassa/webhook/\n(payment.succeeded)")
    s.message("api", "pg", "идемпотентно: заказ → paid")
    s.message("api", "pg", "INSERT job CDEK_CREATE_ORDER")
    s.note("api", "yk", "Webhook идемпотентен: повторный payment.succeeded "
                        "не меняет состояние заказа")
    s.message("yk", "buyer", "redirect обратно в магазин\n(PaymentSuccess)", dashed=True)
    s.message("jw", "pg", "забрать job CDEK_CREATE_ORDER\n(см. 04 · cdek-delivery)", dashed=True)
    return s.finalize()


def gen_cdek_delivery() -> SeqDiagram:
    s = SeqDiagram(
        "04 · Доставка CDEK после оплаты (cdek-delivery)",
        [("jw", "job_worker"), ("pg", "PostgreSQL"), ("cdek", "CDEK API"),
         ("api", "Backend API (FastAPI)"), ("ntf", "NotificationService\n+ WebSocket"), ("buyer", "Покупатель")],
        "job CDEK_CREATE_ORDER → трек-номер → webhook-статусы + polling → уведомление")
    s.message("jw", "pg", "забрать job\nCDEK_CREATE_ORDER")
    s.message("jw", "cdek", "создать заказ на доставку")
    s.message("cdek", "jw", "uuid + трек-номер", dashed=True)
    s.message("jw", "pg", "INSERT CdekOrder\n(track, статус)")
    s.message("jw", "pg", "INSERT job\nCDEK_SYNC_ORDER_STATUS")
    s.message("cdek", "api", "webhook POST /api/v1/cdek/webhooks/cdek/\n(новый статус)")
    s.message("api", "pg", "apply_cdek_status · SELECT FOR UPDATE\n+ cdek_status_history")
    s.message("api", "ntf", "NotificationService.create")
    s.message("ntf", "buyer", "push WebSocket\n/ws/notifications", dashed=True)
    s.note("cdek", "api", "Webhook + polling — два канала одного состояния; "
                          "apply_cdek_status идемпотентен, дубли безопасны")
    s.begin_opt("opt", "[polling fallback: webhook не пришёл]", "jw", "cdek")
    s.message("jw", "pg", "забрать job\nCDEK_SYNC_ORDER_STATUS")
    s.message("jw", "cdek", "GET текущий статус заказа")
    s.message("cdek", "jw", "статус", dashed=True)
    s.message("jw", "pg", "обновить статус\n(тот же apply_cdek_status)")
    s.end_opt()
    return s.finalize()


def gen_order_cancel_refund() -> SeqDiagram:
    s = SeqDiagram(
        "05 · Отмена заказа и возврат (order-cancel-refund)",
        [("admin", "Администратор"), ("api", "Backend API (FastAPI)"),
         ("pg", "PostgreSQL"), ("yk", "ЮKassa"), ("cdek", "CDEK API")],
        "POST /api/v1/admin/orders/{order_id}/cancel/ — строгий refund → возврат stock → best-effort CDEK")
    s.message("admin", "api", "POST /api/v1/admin/orders/{order_id}/cancel/")
    s.message("api", "pg", "SELECT … FOR UPDATE\n(заказ + платёж)")
    s.begin_opt("opt", "[заказ paid: строгий refund до отмены]", "api", "yk")
    s.message("api", "yk", "POST /refunds\n(сумма платежа)")
    s.message("yk", "api", "refund succeeded", dashed=True)
    s.end_opt()
    s.note("api", "yk", "Строгий refund: при сбое возврата API отвечает 502 — "
                        "заказ НЕ отменяется, stock не трогаем, деньги не зависают")
    s.message("api", "pg", "возврат stock · статус canceled\nCOMMIT")
    s.message("api", "cdek", "отмена заказа в CDEK\n(best-effort)")
    s.message("cdek", "api", "ok / ошибка (только лог)", dashed=True)
    s.note("api", "cdek", "CDEK-отмена best-effort: сбой не блокирует отмену заказа, "
                          "ошибка видна в логах и cdek_status_history")
    s.message("api", "admin", "200 · заказ отменён", dashed=True)
    return s.finalize()


def gen_guest_cart_merge() -> SeqDiagram:
    s = SeqDiagram(
        "06 · Гостевая корзина и merge (guest-cart-merge)",
        [("guest", "Гость / Покупатель"), ("fe", "Frontend (Vue)\n+ localStorage"),
         ("api", "Backend API (FastAPI)"), ("pg", "PostgreSQL")],
        "Гостевая корзина на клиенте → POST /api/v1/cart/merge после входа")
    s.message("guest", "fe", "добавляет товары\nбез входа")
    s.self_message("fe", "гостевая корзина\nв localStorage")
    s.message("guest", "fe", "вход / регистрация")
    s.message("fe", "api", "POST /api/v1/login/")
    s.message("api", "fe", "JWT", dashed=True)
    s.message("fe", "api", "POST /api/v1/cart/merge\n(items из localStorage)")
    s.message("api", "pg", "проверка stock\nкаждой позиции")
    s.message("api", "pg", "upsert: суммирование\nс серверной корзиной")
    s.message("api", "fe", "итоговая серверная корзина", dashed=True)
    s.self_message("fe", "очистить гостевую\nкорзину в localStorage")
    s.note("fe", "api", "Merge — upsert: количества суммируются; позиция сверх stock "
                        "отклоняется с ошибкой валидации (409)")
    return s.finalize()


def gen_catalog_1c_sync() -> SeqDiagram:
    s = SeqDiagram(
        "07 · Синхронизация каталога с 1С (catalog-1c-sync)",
        [("onec", "1С (ERP)"), ("api", "Backend API (FastAPI)"), ("pg", "PostgreSQL"),
         ("jw", "job_worker"), ("minio", "MinIO")],
        "Реализован webhook-вариант: JSON-батчи на POST /api/v1/onec/webhook/; файловый intake — частично")
    s.message("onec", "api", "POST /api/v1/onec/webhook/\n(JSON-батч, X-1C-Api-Key)")
    s.self_message("api", "проверка X-1C-Api-Key")
    s.message("api", "pg", "дедуп по batch_id\n(повтор батча)")
    s.message("api", "pg", "дедуп по checksum\n(тот же payload)")
    s.message("api", "pg", "INSERT OnecChangeLog\n(status pending)")
    s.message("api", "pg", "INSERT job\nONEC_APPLY_CHANGES")
    s.message("api", "onec", "200 · batch_id принят\n(dedup-статус)", dashed=True)
    s.note("onec", "api", "Дедуп дважды: по batch_id и по checksum тела — "
                          "повторная отправка батча безопасна")
    s.message("jw", "pg", "забрать job\nONEC_APPLY_CHANGES")
    s.message("jw", "pg", "upsert товары / категории /\nцены (product_prices) / остатки")
    s.message("jw", "pg", "OnecChangeLog → done")
    s.begin_opt("opt", "[файловый intake: raw-приём реализован, разбор — план]", "onec", "minio")
    s.message("onec", "api", "POST /api/v1/onec/intake/\n(ZIP CommerceML, X-1C-Api-Key)")
    s.message("api", "minio", "raw-файл → бакет\nonec-intake")
    s.message("api", "pg", "INSERT onec_intake_log\n(status pending)")
    s.message("api", "onec", "202 Accepted · intake_id", dashed=True)
    s.end_opt()
    return s.finalize()


# ---------------------------------------------------------------------------
# Flowchart: ai-agent-pipeline
# ---------------------------------------------------------------------------
def fc_node_style(fill: str = SEQ_BOX_FILL, stroke: str = SEQ_BOX_STROKE,
                  font: str = SEQ_BOX_FONT, dashed: bool = False) -> str:
    d = "dashed=1;dashPattern=4 4;" if dashed else ""
    return (f"rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor={fill};"
            f"strokeColor={stroke};fontColor={font};fontSize=12;align=center;"
            f"verticalAlign=middle;spacing=6;{d}")


def fc_rhombus_style() -> str:
    return ("rhombus;whiteSpace=wrap;html=1;fillColor=#3a2f16;strokeColor=#d6a94f;"
            "fontColor=#f0d9a0;fontSize=12;align=center;verticalAlign=middle;")


def fc_edge_style(dashed: bool = False) -> str:
    d = "dashed=1;dashPattern=4 4;" if dashed else ""
    return (f"edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor={ARROW};"
            f"fontColor={EDGE_FONT};fontSize=12;endArrow=block;endFill=1;"
            f"labelBackgroundColor=none;{d}")


def gen_agent_pipeline() -> Diagram:
    d = Diagram("08 · AI-agent pipeline", 1460, 1120)
    title(d, "08 · AI-agent pipeline — Promelectron",
          "/skill:implement · architect → dev → review → QA → PR · цикл review до 3 итераций")

    def v(x, y, w, h, val, style=None):
        return d.vertex(x, y, w, h, val, style or fc_node_style())

    # Главная цепочка (центральная колонна x≈560-720)
    entry = v(560, 80, 200, 44, "/skill:*", fc_node_style(fill="#2a2c3f", stroke="#6b7089"))
    tracker = v(560, 160, 200, 44, "Tracker")
    worktree = v(560, 240, 200, 52, "git worktree\n.worktrees/{id}", fc_node_style(dashed=True))
    arch = v(560, 400, 200, 60, "<b>Architect</b>\n⚠ plan mode required",
             fc_node_style(fill="#3b2d4f", stroke="#9a6fc9", font="#d9c2f0"))
    plan = v(560, 520, 200, 44, "PLAN.md / spec.md")
    approve = v(560, 610, 200, 76, "auto / human\napprove?", fc_rhombus_style())
    dev = v(560, 740, 200, 52, "<b>Developer</b>\nbackend / frontend / devops",
            fc_node_style(fill="#1f3a2a", stroke="#4f9a6a", font="#bfe8cc"))
    selfrev = v(560, 830, 200, 52, "Self-review\nadversarial audit diff")
    contract = v(560, 920, 200, 76, "API contract\nbackend ↔ frontend", fc_rhombus_style())
    reviewer = v(560, 1030, 200, 52, "<b>Reviewer</b>\n1-й проход, адаптивно к диффу",
                 fc_node_style(fill="#402e18", stroke="#c98a3f", font="#f0d3a8"))

    # Правая колонка
    secrev = v(900, 1030, 220, 52, "security-reviewer\n(security-sensitive diff)",
               fc_node_style(fill="#402e18", stroke="#c98a3f", font="#f0d3a8", dashed=True))
    approved = v(900, 1160, 200, 76, "APPROVED?", fc_rhombus_style())
    qa = v(560, 1180, 200, 52, "QA Gate\nопционально · --qa", fc_node_style(dashed=True))
    mr = v(560, 1270, 200, 44, "PR → GitHub", fc_node_style(fill="#40202a", stroke="#c9566a", font="#f0b8c0"))
    kc = v(560, 1350, 200, 52, "Knowledge Capture\nуроки → rules / skills / docs",
           fc_node_style(fill="#40202a", stroke="#c9566a", font="#f0b8c0"))
    done = v(560, 1440, 200, 44, "Done", fc_node_style(fill="#2a2c3f", stroke="#6b7089"))

    # Левая колонка: ресурсы и внешние системы
    libs = v(400, 330, 120, 36, "libs", fc_node_style(dashed=True))
    best = v(560, 330, 120, 36, "best-pract", fc_node_style(dashed=True))
    code = v(720, 330, 120, 36, "codebase", fc_node_style(dashed=True))
    jira = v(160, 460, 200, 44, "Jira / Confluence\nspec context", fc_node_style(dashed=True))
    figma = v(180, 740, 200, 44, "Figma\ndesign tokens", fc_node_style(dashed=True))
    human = v(900, 440, 200, 60, "Human", fc_node_style(fill="#3b2d4f", stroke="#9a6fc9", font="#d9c2f0"))

    # Цепочка
    d.edge("", fc_edge_style(), entry, tracker)
    d.edge("", fc_edge_style(), tracker, worktree)
    d.routed(worktree, libs, (0.25, 1), (0.5, 0), points=[(610, 311), (460, 311)], dashed=True)
    d.routed(worktree, best, (0.5, 1), (0.5, 0), dashed=True)
    d.routed(worktree, code, (0.75, 1), (0.5, 0), points=[(710, 311), (780, 311)], dashed=True)
    d.routed(libs, arch, (0.5, 1), (0.15, 0), points=[(460, 410), (590, 410)])
    d.routed(best, arch, (0.5, 1), (0.45, 0))
    d.routed(code, arch, (0.5, 1), (0.8, 0), points=[(780, 410), (720, 410)])
    # Architect ↔ Human — двунаправленная связь
    d.edge("", fc_edge_style(dashed=True) + "startArrow=block;startFill=1;", arch, human)
    d.text(772, 424, 116, 36, "прорабатывают\nархитектуру", color=EDGE_FONT, valign="top", align="center")
    d.edge("spec context", fc_edge_style(dashed=True), jira, arch)
    d.edge("", fc_edge_style(), arch, plan)
    d.edge("", fc_edge_style(), plan, approve)
    d.edge("revise", fc_edge_style(dashed=True) + f"fontColor={ERR_FONT};", approve, plan,
           points=[(780, 540)])
    d.edge("approved", fc_edge_style() + f"fontColor={OK_FONT};", approve, dev)
    d.edge("design tokens", fc_edge_style(dashed=True), figma, dev)
    d.edge("", fc_edge_style(), dev, selfrev)
    d.edge("", fc_edge_style(), selfrev, contract)
    d.edge("расхождение", fc_edge_style(dashed=True) + f"fontColor={ERR_FONT};", contract, dev,
           points=[(790, 950)])
    d.edge("ok", fc_edge_style() + f"fontColor={OK_FONT};", contract, reviewer)
    d.edge("", fc_edge_style(dashed=True), reviewer, secrev)
    d.edge("", fc_edge_style(), reviewer, approved)
    d.edge("", fc_edge_style(), secrev, approved)
    d.edge("нет", fc_edge_style(dashed=True) + f"fontColor={ERR_FONT};", approved, dev,
           points=[(1240, 1200), (1240, 766)])
    d.edge("да", fc_edge_style() + f"fontColor={OK_FONT};", approved, qa)
    d.edge("", fc_edge_style(), qa, mr)
    d.edge("", fc_edge_style(), mr, kc)
    d.edge("", fc_edge_style(), kc, done)

    # Заметки
    d.vertex(900, 1280, 340, 44, "re-review — один агент (шард при LARGE)\n· цикл до 3 итераций",
             f"shape=note;whiteSpace=wrap;html=1;fillColor={NOTE_FILL};strokeColor={NOTE_STROKE};"
             f"fontColor={NOTE_FONT};fontSize=12;align=center;verticalAlign=middle;size=12;")
    d.vertex(900, 1350, 340, 44, "agent_state.py — trace.jsonl на границах фаз\n· correlation ID",
             f"shape=note;whiteSpace=wrap;html=1;fillColor={NOTE_FILL};strokeColor={NOTE_STROKE};"
             f"fontColor={NOTE_FONT};fontSize=12;align=center;verticalAlign=middle;size=12;")

    d.page_h = 1560
    return d


# ---------------------------------------------------------------------------
# Реестр и main
# ---------------------------------------------------------------------------
TARGETS: dict[str, tuple[str, callable]] = {
    "docs/architecture/01-c4-system-context.drawio": ("01-c4-system-context", gen_c4_l1),
    "docs/architecture/02-c4-containers.drawio": ("02-c4-containers", gen_c4_l2),
    "docs/flows/03-order-checkout.drawio": ("03-order-checkout", gen_order_checkout),
    "docs/flows/04-cdek-delivery.drawio": ("04-cdek-delivery", gen_cdek_delivery),
    "docs/flows/05-order-cancel-refund.drawio": ("05-order-cancel-refund", gen_order_cancel_refund),
    "docs/flows/06-guest-cart-merge.drawio": ("06-guest-cart-merge", gen_guest_cart_merge),
    "docs/flows/07-catalog-1c-sync.drawio": ("07-catalog-1c-sync", gen_catalog_1c_sync),
    "docs/08-ai-agent-pipeline.drawio": ("08-ai-agent-pipeline", gen_agent_pipeline),
}


def render_svg(drawio_path: Path, drawio_bin: str) -> bool:
    svg = drawio_path.with_suffix(".svg")
    proc = subprocess.run(
        [drawio_bin, "-x", "-f", "svg", "-o", str(svg), str(drawio_path)],
        capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        print(f"  ✗ render failed: {drawio_path}\n{proc.stdout}\n{proc.stderr}", file=sys.stderr)
        return False
    print(f"  ✓ {svg.relative_to(ROOT)}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Генерация drawio-диаграмм документации Promelectron")
    ap.add_argument("--render", action="store_true",
                    help="сразу отрендерить SVG (drawio из $DRAWIO или ~/tools/drawio)")
    ap.add_argument("--only", nargs="*", default=None,
                    help="генерировать только перечисленные цели (подстрока пути)")
    args = ap.parse_args()

    drawio_bin = os.environ.get("DRAWIO", os.path.expanduser("~/tools/drawio"))
    ok = True
    for rel, (name, gen) in TARGETS.items():
        if args.only and not any(o in rel for o in args.only):
            continue
        out = ROOT / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(gen().xml(), encoding="utf-8")
        print(f"✓ {rel}")
        if args.render:
            ok = render_svg(out, drawio_bin) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
