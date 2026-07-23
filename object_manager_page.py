import re
import xml.etree.ElementTree as ET
from io import BytesIO

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import PrimaryPushButton, TogglePushButton
import qtawesome as qta

import object_store
from device_panel import PROJECT_HANDLERS
from ui_common import Palette, add_shadow, card_css, kfont, styled

BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


class ObjectManagerPage(QWidget):
    """weditor처럼 연결된 단말 화면에서 UI 요소를 찾아, 이름을 붙여 프로젝트별로
    저장해두는 화면. 여기서 저장한 이름 있는 객체들을 나중에 시나리오 작성 시
    resourceId를 다시 찾을 필요 없이 재사용하는 게 목표입니다.
    [프로젝트 목록] - [단말 화면/요소 찾기] - [선택한 요소 상세 + 이름 저장 + 저장된 객체 목록]
    3단 구성입니다."""

    def __init__(self, panel_a, panel_b, parent=None):
        super().__init__(parent)
        self.setObjectName("objectManagerInterface")
        self.panel_a = panel_a
        self.panel_b = panel_b
        self._target = "A"
        self._nodes = []
        self._pixmap_orig = None
        self._selected_node = None
        self._current_project = None
        self._project_buttons = {}

        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(16)

        outer.addWidget(self._build_project_list(), 2)
        outer.addWidget(self._build_inspector_panel(), 5)
        outer.addWidget(self._build_detail_and_saved_panel(), 3)

        if PROJECT_HANDLERS:
            first_project = next(iter(PROJECT_HANDLERS))
            self._project_buttons[first_project].setChecked(True)
            self._on_project_selected(first_project)

    # ---------- 1단: 프로젝트 목록 ----------
    def _build_project_list(self):
        card = styled(QFrame(), card_css())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(6)

        title = QLabel("프로젝트")
        title.setFont(kfont(12, True))
        title.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(title)

        group = QButtonGroup(card)
        group.setExclusive(True)
        for proj_name in PROJECT_HANDLERS:
            btn = TogglePushButton(proj_name)
            btn.setFont(kfont(11, True))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, p=proj_name: self._on_project_selected(p))
            group.addButton(btn)
            layout.addWidget(btn)
            self._project_buttons[proj_name] = btn
        layout.addStretch(1)

        return add_shadow(card)

    def _on_project_selected(self, proj_name):
        self._current_project = proj_name
        self._refresh_saved_list()

    # ---------- 2단: 단말 화면 + 요소 찾기 ----------
    def _build_inspector_panel(self):
        card = styled(QFrame(), card_css())
        outer = QVBoxLayout(card)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        toolbar = QHBoxLayout()
        lbl = QLabel("대상 단말:")
        lbl.setFont(kfont(11))
        lbl.setStyleSheet(f"color:{Palette.text_sub};")
        toolbar.addWidget(lbl)

        group = QButtonGroup(card)
        group.setExclusive(True)
        for key in ("A", "B"):
            btn = TogglePushButton(f"{key} 단말")
            btn.setFixedHeight(28)
            btn.setFont(kfont(11, True))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setChecked(key == "A")
            btn.clicked.connect(lambda checked=False, k=key: setattr(self, "_target", k))
            group.addButton(btn)
            toolbar.addWidget(btn)
        toolbar.addStretch(1)

        btn_refresh = PrimaryPushButton(qta.icon("fa5s.sync-alt", color="white"), "새로고침")
        btn_refresh.setFixedHeight(28)
        btn_refresh.setFont(kfont(11, True))
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self._refresh_device)
        toolbar.addWidget(btn_refresh)
        outer.addLayout(toolbar)

        body = QHBoxLayout()
        body.setSpacing(10)
        outer.addLayout(body, 1)

        self._screen_lbl = QLabel("새로고침을 눌러 화면을 불러오세요.")
        self._screen_lbl.setAlignment(Qt.AlignCenter)
        self._screen_lbl.setStyleSheet(
            f"background-color:#1C1C1E; color:{Palette.text_sub}; border-radius:{Palette.radius}px;"
        )
        self._screen_lbl.setMinimumWidth(300)
        body.addWidget(self._screen_lbl, 5)

        list_col = QVBoxLayout()
        list_col.setSpacing(6)
        body.addLayout(list_col, 4)

        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("🔍 resourceId / text로 필터")
        self._filter_edit.textChanged.connect(self._apply_filter)
        list_col.addWidget(self._filter_edit)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_row_selected)
        list_col.addWidget(self._list, 1)

        return card

    # ---------- 3단: 선택 요소 상세 + 이름 저장 + 저장된 객체 목록 ----------
    def _build_detail_and_saved_panel(self):
        card = styled(QFrame(), card_css())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(6)

        title = QLabel("선택한 요소")
        title.setFont(kfont(12, True))
        title.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(title)

        self._detail_labels = {}
        for key, label_text in (
            ("resource_id", "resourceId"),
            ("text", "text"),
            ("class_name", "class"),
        ):
            row = QHBoxLayout()
            t = QLabel(f"{label_text}:")
            t.setFont(kfont(10, True))
            t.setFixedWidth(70)
            t.setStyleSheet(f"color:{Palette.text_sub};")
            v = QLabel("-")
            v.setFont(kfont(10))
            v.setWordWrap(True)
            v.setStyleSheet(f"color:{Palette.text_main};")
            row.addWidget(t)
            row.addWidget(v, 1)
            layout.addLayout(row)
            self._detail_labels[key] = v

        name_row = QHBoxLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("이 요소에 붙일 이름")
        name_row.addWidget(self._name_edit, 1)
        layout.addLayout(name_row)

        btn_save = PrimaryPushButton(qta.icon("fa5s.save", color="white"), "이름으로 저장")
        btn_save.setFixedHeight(30)
        btn_save.setFont(kfont(11, True))
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._save_named_object)
        layout.addWidget(btn_save)

        layout.addSpacing(10)
        saved_title = QLabel("저장된 객체")
        saved_title.setFont(kfont(12, True))
        saved_title.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(saved_title)

        self._saved_list = QListWidget()
        layout.addWidget(self._saved_list, 1)

        btn_delete = PrimaryPushButton(qta.icon("fa5s.trash-alt", color="white"), "선택 삭제")
        btn_delete.setFixedHeight(28)
        btn_delete.setFont(kfont(10, True))
        btn_delete.setCursor(Qt.PointingHandCursor)
        btn_delete.clicked.connect(self._delete_selected_saved_object)
        layout.addWidget(btn_delete)

        return add_shadow(card)

    # ---------- 단말에서 화면/계층 가져오기 ----------
    def _current_panel(self):
        return self.panel_a if self._target == "A" else self.panel_b

    def _refresh_device(self):
        panel = self._current_panel()
        if not panel.current_uuid:
            QMessageBox.warning(self, "단말 미연결", f"먼저 {self._target} 단말을 연결해주세요.")
            return

        try:
            import uiautomator2 as u2

            d = u2.connect(panel.current_uuid)
            xml_str = d.dump_hierarchy()
            img = d.screenshot()
            buf = BytesIO()
            img.save(buf, format="PNG")
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            self._pixmap_orig = pixmap
        except Exception as e:
            QMessageBox.warning(self, "불러오기 실패", str(e))
            return

        self._nodes = self._parse_hierarchy(xml_str)
        self._populate_list()
        self._render_screenshot(highlight=None)

    @staticmethod
    def _parse_hierarchy(xml_str):
        nodes = []
        try:
            root = ET.fromstring(xml_str)
        except ET.ParseError:
            return nodes
        for node in root.iter("node"):
            m = BOUNDS_RE.match(node.attrib.get("bounds", ""))
            if not m:
                continue
            x1, y1, x2, y2 = map(int, m.groups())
            if x2 <= x1 or y2 <= y1:
                continue
            nodes.append({
                "resource_id": node.attrib.get("resource-id", ""),
                "text": node.attrib.get("text", ""),
                "class_name": node.attrib.get("class", ""),
                "desc": node.attrib.get("content-desc", ""),
                "bounds": [x1, y1, x2, y2],
            })
        return nodes

    def _populate_list(self):
        self._list.clear()
        for node in self._nodes:
            label = node["resource_id"] or node["text"] or node["class_name"] or "(이름 없음)"
            self._list.addItem(QListWidgetItem(label))
        self._apply_filter(self._filter_edit.text())

    def _apply_filter(self, text):
        text = text.lower().strip()
        for i in range(self._list.count()):
            node = self._nodes[i]
            haystack = f"{node['resource_id']} {node['text']} {node['class_name']}".lower()
            self._list.item(i).setHidden(bool(text) and text not in haystack)

    def _on_row_selected(self, row):
        if row < 0 or row >= len(self._nodes):
            self._selected_node = None
            return
        node = self._nodes[row]
        self._selected_node = node
        self._detail_labels["resource_id"].setText(node["resource_id"] or "-")
        self._detail_labels["text"].setText(node["text"] or "-")
        self._detail_labels["class_name"].setText(node["class_name"] or "-")
        self._render_screenshot(highlight=node["bounds"])

    def _render_screenshot(self, highlight):
        if self._pixmap_orig is None:
            return
        pixmap = self._pixmap_orig.copy()
        if highlight:
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor(Palette.danger), 4))
            x1, y1, x2, y2 = highlight
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)
            painter.end()
        if pixmap.width() > 380:
            pixmap = pixmap.scaledToWidth(380, Qt.SmoothTransformation)
        self._screen_lbl.setPixmap(pixmap)

    # ---------- 이름 붙여 저장 / 저장된 목록 ----------
    def _save_named_object(self):
        if not self._current_project:
            QMessageBox.warning(self, "프로젝트 미선택", "먼저 왼쪽에서 프로젝트를 선택해주세요.")
            return
        if not self._selected_node:
            QMessageBox.warning(self, "요소 미선택", "가운데 목록에서 저장할 요소를 먼저 선택해주세요.")
            return
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "이름 필요", "저장할 이름을 입력해주세요.")
            return

        object_store.save_object(self._current_project, name, self._selected_node)
        self._name_edit.clear()
        self._refresh_saved_list()

    def _refresh_saved_list(self):
        self._saved_list.clear()
        if not self._current_project:
            return
        saved = object_store.list_objects(self._current_project)
        for name, node in saved.items():
            item = QListWidgetItem(f"{name}  —  {node.get('resource_id') or node.get('text') or node.get('class_name')}")
            item.setData(Qt.UserRole, name)
            self._saved_list.addItem(item)

    def _delete_selected_saved_object(self):
        item = self._saved_list.currentItem()
        if not item or not self._current_project:
            return
        name = item.data(Qt.UserRole)
        object_store.delete_object(self._current_project, name)
        self._refresh_saved_list()
