import html
import re
import xml.etree.ElementTree as ET
from io import BytesIO

from PySide6.QtCore import Qt, QMimeData, QSize, QTimer, Signal
from PySide6.QtGui import QColor, QDrag, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta

import object_store
from device_panel import PROJECT_HANDLERS
from ui_common import (
    NavListButton,
    Navy,
    clear_layout,
    kfont,
    navy_button,
    navy_card,
    navy_card_header,
    navy_input_css,
    navy_list_css,
    navy_mono_font,
    navy_page_css,
    navy_page_header,
    styled,
)

BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")
_OBJECT_MIME_TYPE = "application/x-mcx-object-name"


def _bool_label(value):
    # uiautomator2 .info/XML 속성 값과 그대로 맞춰서(둘 다 true/false) 보여줍니다.
    return "true" if value else "false"


class _ObjectRowLabel(QLabel):
    """저장된 객체 목록 한 줄의 라벨. 그냥 클릭하면 수정 모드로 불러오고,
    누른 채로 끌면 다른 폴더 위에 놓아서 옮길 수 있습니다(클릭/드래그는
    이동 거리로 구분: 살짝 움직인 정도는 클릭으로 칩니다)."""

    clicked = Signal()

    def __init__(self, text, object_name, parent=None):
        super().__init__(text, parent)
        self._object_name = object_name
        self._press_pos = None
        self._dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.position().toPoint()
            self._dragging = False
            # QLabel의 기본 구현은 마우스 눌림을 무시(ignore)합니다. 그러면 눌림이 부모인
            # 목록 뷰로 넘어가면서 이후의 마우스 이동/뗌 이벤트도 뷰가 가져가고, 아래
            # mouseMoveEvent가 아예 호출되지 않아 드래그가 시작되지 않았습니다.
            # 여기서 직접 accept해서 이 라벨이 제스처를 끝까지 받도록 합니다.
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._press_pos is not None
            and not self._dragging
            and event.buttons() & Qt.LeftButton
            and (event.position().toPoint() - self._press_pos).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            self._dragging = True
            mime = QMimeData()
            mime.setData(_OBJECT_MIME_TYPE, self._object_name.encode("utf-8"))
            drag = QDrag(self)
            drag.setMimeData(mime)
            drag.exec(Qt.MoveAction)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._press_pos is not None:
            was_click = not self._dragging
            self._press_pos = None
            self._dragging = False
            event.accept()
            if was_click:
                self.clicked.emit()
            return
        self._press_pos = None
        self._dragging = False
        super().mouseReleaseEvent(event)


class _FolderHeaderRow(QWidget):
    """저장된 객체 목록에서 폴더 한 줄. 평소엔 펼침/접힘 화살표와 이름만 보이다가,
    마우스를 올리면 오른쪽에 수정/삭제 버튼이 나타납니다. 기본 폴더는 이름은
    바꿀 수 있지만(계속 기본 폴더 역할은 유지) 삭제는 할 수 없어 삭제 버튼만
    빠집니다."""

    toggled = Signal()
    editRequested = Signal(str)
    deleteRequested = Signal(str)

    def __init__(self, folder, label_text, can_edit=True, can_delete=True, parent=None):
        super().__init__(parent)
        self._folder = folder
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(4)

        self._label = QLabel(label_text)
        self._label.setFont(kfont(9, True))
        self._label.setStyleSheet(f"color:{Navy.text_muted};")
        self._label.setToolTip(label_text)
        layout.addWidget(self._label, 1)

        self._can_edit = can_edit
        self._can_delete = can_delete

        self._btn_edit = navy_button("", kind="ghost", height=22, icon_name="fa5s.pen", icon_size=10)
        self._btn_edit.setFixedWidth(24)
        self._btn_edit.setToolTip("폴더 이름 수정")
        self._btn_edit.clicked.connect(lambda: self.editRequested.emit(self._folder))
        self._btn_edit.setVisible(False)
        layout.addWidget(self._btn_edit)

        self._btn_delete = navy_button("", kind="danger", height=22, icon_name="fa5s.trash-alt", icon_size=10)
        self._btn_delete.setFixedWidth(24)
        self._btn_delete.setToolTip("폴더 삭제 (하위 객체 포함)")
        self._btn_delete.clicked.connect(lambda: self.deleteRequested.emit(self._folder))
        self._btn_delete.setVisible(False)
        layout.addWidget(self._btn_delete)

    def enterEvent(self, event):
        if self._can_edit:
            self._btn_edit.setVisible(True)
        if self._can_delete:
            self._btn_delete.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._btn_edit.setVisible(False)
        self._btn_delete.setVisible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            event.accept()
            self.toggled.emit()
            return
        super().mousePressEvent(event)


class _SavedObjectList(QListWidget):
    """저장된 객체 목록. 행이 setItemWidget으로 덮여 있어 Qt 기본 드래그는 못 먹으므로
    (드래그 시작은 _ObjectRowLabel이 직접 함), 드롭만 여기서 받아서 놓인 위치의
    폴더로 옮깁니다."""

    objectDroppedOnFolder = Signal(str, str)  # (object_name, target_folder)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(_OBJECT_MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(_OBJECT_MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime = event.mimeData()
        if not mime.hasFormat(_OBJECT_MIME_TYPE):
            event.ignore()
            return
        target_item = self.itemAt(event.position().toPoint())
        if target_item is None and self.count():
            # 목록 아래 빈 공간에 놓으면 맨 마지막 폴더로 보냅니다(아무 일도 안 일어나면
            # 사용자는 옮겨졌는지 실패했는지 알 수 없어서).
            target_item = self.item(self.count() - 1)
        folder = target_item.data(Qt.UserRole + 1) if target_item else None
        if not folder:
            event.ignore()
            return
        name = bytes(mime.data(_OBJECT_MIME_TYPE)).decode("utf-8")
        event.acceptProposedAction()
        self.objectDroppedOnFolder.emit(name, folder)


class ScreenLabel(QLabel):
    """미러링된 단말 화면을 보여주는 라벨. 화면 위 클릭 좌표를
    원본 스크린샷(=계층 덤프) 좌표로 변환해 clicked 시그널로 알려준다."""

    clicked = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._orig_size = None

    def set_orig_size(self, width, height):
        self._orig_size = (width, height)

    def mousePressEvent(self, event):
        pixmap = self.pixmap()
        if event.button() == Qt.LeftButton and self._orig_size and pixmap and pixmap.width() > 0:
            disp_w, disp_h = pixmap.width(), pixmap.height()
            scale = self._orig_size[0] / disp_w
            offset_x = (self.width() - disp_w) / 2
            offset_y = (self.height() - disp_h) / 2
            pos = event.position().toPoint()
            x = (pos.x() - offset_x) * scale
            y = (pos.y() - offset_y) * scale
            if 0 <= x <= self._orig_size[0] and 0 <= y <= self._orig_size[1]:
                self.clicked.emit(int(x), int(y))
        super().mousePressEvent(event)


class ObjectManagerPage(QWidget):
    """weditor처럼 연결된 단말 화면에서 UI 요소를 찾아, 이름을 붙여 프로젝트별로
    저장해두는 화면. 여기서 저장한 이름 있는 객체들을 나중에 시나리오 작성 시
    resourceId를 다시 찾을 필요 없이 재사용하는 게 목표입니다.
    [프로젝트 목록] - [단말 화면/요소 찾기] - [선택한 요소 상세 + 이름 저장 + 저장된 객체 목록]
    3단 구성입니다."""

    def __init__(self, panel_a, panel_b, parent=None):
        super().__init__(parent)
        self.setObjectName("objectManagerInterface")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # 자식까지 물들이지 않도록 이 위젯 하나만 가리키는 id 선택자로 바닥색을 칠합니다.
        self.setStyleSheet(navy_page_css("objectManagerInterface"))
        self.panel_a = panel_a
        self.panel_b = panel_b
        self._nodes = []
        self._pixmap_orig = None
        self._current_package = ""
        self._current_activity = ""
        self._selected_node = None
        self._editing_name = None
        self._current_project = None
        self._project_buttons = {}
        self._saved_checkboxes = {}
        self._collapsed_folders = set()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        header, self._breadcrumb = navy_page_header(
            "객체 관리", "단말 화면에서 UI 요소를 찾아 이름을 붙여 프로젝트별로 저장합니다."
        )
        outer.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        outer.addLayout(body, 1)

        # 프로젝트 목록을 마지막에 만드는 이유: 그 안에서 첫 프로젝트를 자동 선택하며
        # _refresh_saved_list() 등이 다른 패널의 위젯(_saved_list 등)을 바로 건드리는데,
        # 그 위젯들은 아래 두 패널을 먼저 만들어야 존재합니다. 화면상 배치는 addWidget
        # 순서(project -> inspector -> detail)로 그대로 유지됩니다.
        inspector_panel = self._build_inspector_panel()
        detail_panel = self._build_detail_and_saved_panel()
        project_list = self._build_project_list()

        body.addWidget(project_list, 2)
        body.addWidget(inspector_panel, 5)
        body.addWidget(detail_panel, 3)

    def showEvent(self, event):
        super().showEvent(event)
        # "프로젝트 관리" 화면에서 새 프로젝트를 추가하고 돌아왔을 때도 목록이
        # 최신 상태로 보이도록 이 화면이 다시 보일 때마다 새로고침합니다.
        self._refresh_project_buttons()

    # ---------- 1단: 프로젝트 목록 ----------
    def _build_project_list(self):
        self._project_list_card = navy_card()
        layout = QVBoxLayout(self._project_list_card)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(4)

        header, self._project_count = navy_card_header("프로젝트", badge=0)
        layout.addWidget(header)

        # 프로젝트 버튼들은 _refresh_project_buttons()가 매번 통째로 지우고 다시 그리므로,
        # 아래 기기 연결 섹션까지 같이 지워지지 않도록 별도의 내부 레이아웃에 담습니다.
        # (그 안의 addStretch가 기기 섹션을 카드 아래쪽으로 밀어줍니다.)
        self._project_list_layout = QVBoxLayout()
        self._project_list_layout.setSpacing(2)
        layout.addLayout(self._project_list_layout, 1)
        self._refresh_project_buttons()

        layout.addSpacing(6)

        device_header, _ = navy_card_header("기기")
        layout.addWidget(device_header)

        self._btn_connect_device = navy_button(
            "기기 연결", kind="primary", height=32, icon_name="fa5s.plug"
        )
        self._btn_connect_device.clicked.connect(lambda: self.panel_a.btn_connect.click())
        layout.addWidget(self._btn_connect_device)

        self._device_status_lbl = QLabel("연결된 단말 없음")
        self._device_status_lbl.setFont(kfont(9))
        self._device_status_lbl.setStyleSheet(f"color:{Navy.text_muted}; padding-top:2px;")
        self._device_status_lbl.setWordWrap(True)
        layout.addWidget(self._device_status_lbl)
        self.panel_a.signals.device_ready.connect(self._on_device_ready)

        return self._project_list_card

    def _on_device_ready(self, info):
        if info:
            self._device_status_lbl.setText(f"● 단말 연결됨: {info.get('model', '')}")
            self._device_status_lbl.setStyleSheet(f"color:{Navy.accent}; padding-top:2px;")
        else:
            self._device_status_lbl.setText("연결된 단말 없음")
            self._device_status_lbl.setStyleSheet(f"color:{Navy.text_muted}; padding-top:2px;")

    def _refresh_project_buttons(self):
        clear_layout(self._project_list_layout, keep=0)
        self._project_buttons = {}
        self._project_count.setText(str(len(PROJECT_HANDLERS)))
        group = QButtonGroup(self._project_list_card)
        group.setExclusive(True)
        for proj_name in PROJECT_HANDLERS:
            btn = NavListButton(proj_name, height=34)
            btn.clicked.connect(lambda checked=False, p=proj_name: self._on_project_selected(p))
            group.addButton(btn)
            self._project_list_layout.addWidget(btn)
            self._project_buttons[proj_name] = btn
        self._project_list_layout.addStretch(1)

        if self._current_project in self._project_buttons:
            self._project_buttons[self._current_project].setChecked(True)
        elif PROJECT_HANDLERS:
            first_project = next(iter(PROJECT_HANDLERS))
            self._project_buttons[first_project].setChecked(True)
            self._on_project_selected(first_project)

    def _on_project_selected(self, proj_name):
        self._current_project = proj_name
        self._breadcrumb.setText(proj_name)
        self._reset_edit_form()
        self._collapsed_folders = set()
        self._refresh_folder_combo()
        self._refresh_saved_list()

    # ---------- 2단: 단말 화면 + 요소 찾기 ----------
    def _build_inspector_panel(self):
        card = navy_card()
        outer = QVBoxLayout(card)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        btn_refresh = navy_button("새로고침", kind="ghost", height=30, icon_name="fa5s.sync-alt")
        btn_refresh.clicked.connect(self._refresh_device)
        header, _ = navy_card_header("단말 화면", actions=[btn_refresh])
        outer.addWidget(header)

        # weditor처럼 현재 화면의 Activity와 선택한 요소의 resourceId를 화면
        # 미러링 위쪽에 항상 보이는 정보 바로 표시합니다. 복사해서 쓸 수 있게
        # 텍스트 선택도 가능하게 해둡니다.
        info_bar = styled(
            QFrame(),
            f"background-color:{Navy.navy}; border:none; border-radius:{Navy.radius_sm}px;",
        )
        info_layout = QVBoxLayout(info_bar)
        info_layout.setContentsMargins(12, 8, 12, 8)
        info_layout.setSpacing(3)

        self._activity_lbl = QLabel("Activity: -")
        self._activity_lbl.setFont(navy_mono_font(9))
        self._activity_lbl.setStyleSheet("color:#E6ECF7; background:transparent;")
        self._activity_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(self._activity_lbl)

        self._resource_id_lbl = QLabel("resourceId: -")
        self._resource_id_lbl.setFont(navy_mono_font(9))
        self._resource_id_lbl.setStyleSheet("color:#9FB0CC; background:transparent;")
        self._resource_id_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        info_layout.addWidget(self._resource_id_lbl)

        outer.addWidget(info_bar)

        body = QHBoxLayout()
        body.setSpacing(12)
        outer.addLayout(body, 1)

        self._screen_lbl = ScreenLabel("새로고침을 눌러 화면을 불러오세요.")
        self._screen_lbl.setAlignment(Qt.AlignCenter)
        self._screen_lbl.setStyleSheet(
            f"background-color:{Navy.navy_pressed}; color:#8598B8; "
            f"border-radius:{Navy.radius_sm}px;"
        )
        self._screen_lbl.setMinimumWidth(300)
        self._screen_lbl.setCursor(Qt.PointingHandCursor)
        self._screen_lbl.clicked.connect(self._on_screen_clicked)
        body.addWidget(self._screen_lbl, 5)

        list_col = QVBoxLayout()
        list_col.setSpacing(8)
        body.addLayout(list_col, 4)

        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("resourceId / text로 필터")
        self._filter_edit.setFixedHeight(30)
        self._filter_edit.setFont(kfont(10))
        self._filter_edit.setStyleSheet(navy_input_css())
        self._filter_edit.textChanged.connect(self._apply_filter)
        list_col.addWidget(self._filter_edit)

        self._list = QListWidget()
        self._list.setFont(navy_mono_font(9))
        self._list.setStyleSheet(navy_list_css())
        self._list.currentRowChanged.connect(self._on_row_selected)
        list_col.addWidget(self._list, 1)

        return card

    # ---------- 3단: 선택 요소 상세 + 이름 저장 + 저장된 객체 목록 ----------
    def _build_detail_and_saved_panel(self):
        card = navy_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header, _ = navy_card_header("선택한 요소")
        layout.addWidget(header)

        self._detail_labels = {}
        for key, label_text in (
            ("resource_id", "resourceId"),
            ("text", "text"),
            ("desc", "desc"),
            ("class_name", "class"),
            ("checkable", "checkable"),
            ("checked", "checked"),
        ):
            row = QHBoxLayout()
            row.setSpacing(6)
            t = QLabel(label_text)
            t.setFont(kfont(9, True))
            t.setFixedWidth(66)
            t.setAlignment(Qt.AlignRight | Qt.AlignTop)
            t.setStyleSheet(f"color:{Navy.text_muted};")
            # 값은 resourceId/클래스명처럼 그대로 복사해 쓰는 문자열이라 고정폭 글꼴로.
            v = QLabel("-")
            v.setFont(navy_mono_font(9))
            v.setWordWrap(True)
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            v.setStyleSheet(f"color:{Navy.text};")
            row.addWidget(t)
            row.addWidget(v, 1)
            layout.addLayout(row)
            self._detail_labels[key] = v

        folder_row = QHBoxLayout()
        folder_row.setSpacing(6)
        folder_lbl = QLabel("폴더")
        folder_lbl.setFont(kfont(9, True))
        folder_lbl.setFixedWidth(66)
        folder_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        folder_lbl.setStyleSheet(f"color:{Navy.text_muted};")
        folder_row.addWidget(folder_lbl)
        self._folder_combo = QComboBox()
        self._folder_combo.setFixedHeight(30)
        self._folder_combo.setFont(kfont(10))
        self._folder_combo.setStyleSheet(navy_input_css())
        folder_row.addWidget(self._folder_combo, 1)
        btn_add_folder = navy_button(
            "", kind="ghost", height=30, icon_name="fa5s.folder-plus", icon_size=13
        )
        btn_add_folder.setFixedWidth(34)
        btn_add_folder.setToolTip("새 폴더 추가")
        btn_add_folder.clicked.connect(self._on_add_folder_clicked)
        folder_row.addWidget(btn_add_folder)
        layout.addLayout(folder_row)

        role_row = QHBoxLayout()
        role_row.setSpacing(6)
        role_lbl = QLabel("채널역할")
        role_lbl.setFont(kfont(9, True))
        role_lbl.setFixedWidth(66)
        role_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        role_lbl.setStyleSheet(f"color:{Navy.text_muted};")
        role_row.addWidget(role_lbl)
        self._channel_role_combo = QComboBox()
        self._channel_role_combo.setFixedHeight(30)
        self._channel_role_combo.setFont(kfont(10))
        self._channel_role_combo.setStyleSheet(navy_input_css())
        self._channel_role_combo.addItems(["(없음)", "주채널", "부채널"])
        self._channel_role_combo.setToolTip(
            "이 요소가 채널마다 값이 달라지는 자리(예: 채널 이름)를 가리킬 때, "
            "저장 당시 텍스트 대신 프로젝트 창에서 지정한 주채널/부채널의 실제 "
            "채널명으로 실행 시점에 바꿔서 찾습니다."
        )
        role_row.addWidget(self._channel_role_combo, 1)
        layout.addLayout(role_row)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("이 요소에 붙일 이름")
        self._name_edit.setFixedHeight(30)
        self._name_edit.setFont(kfont(10))
        self._name_edit.setStyleSheet(navy_input_css())
        layout.addWidget(self._name_edit)

        self._editing_hint_lbl = QLabel("")
        self._editing_hint_lbl.setFont(kfont(9))
        self._editing_hint_lbl.setWordWrap(True)
        self._editing_hint_lbl.setStyleSheet(
            f"background-color:{Navy.accent_soft}; color:{Navy.accent}; border:none; "
            f"border-left:3px solid {Navy.accent}; border-radius:{Navy.radius_sm}px; padding:7px 9px;"
        )
        self._editing_hint_lbl.setVisible(False)
        layout.addWidget(self._editing_hint_lbl)

        save_btn_row = QHBoxLayout()
        save_btn_row.setSpacing(6)
        self._btn_save = navy_button(
            "이름으로 저장", kind="primary", height=32, icon_name="fa5s.save"
        )
        self._btn_save.clicked.connect(self._save_named_object)
        save_btn_row.addWidget(self._btn_save, 1)
        btn_new = navy_button("", kind="ghost", height=32, icon_name="fa5s.eraser", icon_size=13)
        btn_new.setFixedWidth(36)
        btn_new.setToolTip("수정 취소하고 새로 만들기")
        btn_new.clicked.connect(self._reset_edit_form)
        save_btn_row.addWidget(btn_new)
        layout.addLayout(save_btn_row)

        layout.addSpacing(6)
        btn_add_folder_2 = navy_button(
            "", kind="ghost", height=24, icon_name="fa5s.folder-plus", icon_size=11
        )
        btn_add_folder_2.setFixedWidth(26)
        btn_add_folder_2.setToolTip("새 폴더 추가")
        btn_add_folder_2.clicked.connect(self._on_add_folder_clicked)
        saved_header, self._saved_count = navy_card_header(
            "저장된 객체", badge=0, actions=[btn_add_folder_2]
        )
        layout.addWidget(saved_header)

        self._saved_list = _SavedObjectList()
        self._saved_list.setFont(kfont(10))
        self._saved_list.setStyleSheet(navy_list_css())
        self._saved_list.objectDroppedOnFolder.connect(self._on_object_dropped_on_folder)
        layout.addWidget(self._saved_list, 1)

        btn_delete = navy_button("선택 삭제", kind="danger", height=30, icon_name="fa5s.trash-alt")
        btn_delete.clicked.connect(self._delete_selected_saved_object)
        layout.addWidget(btn_delete)

        copy_move_row = QHBoxLayout()
        copy_move_row.setSpacing(6)
        btn_copy = navy_button(
            "다른 프로젝트로 복사", kind="ghost", height=30, icon_name="fa5s.copy"
        )
        btn_copy.clicked.connect(lambda: self._copy_or_move_selected_saved_object(move=False))
        btn_move = navy_button("이동", kind="ghost", height=30, icon_name="fa5s.share")
        btn_move.clicked.connect(lambda: self._copy_or_move_selected_saved_object(move=True))
        copy_move_row.addWidget(btn_copy, 2)
        copy_move_row.addWidget(btn_move, 1)
        layout.addLayout(copy_move_row)

        return card

    # ---------- 단말에서 화면/계층 가져오기 ----------
    def _current_panel(self):
        return self.panel_a

    def _refresh_device(self):
        panel = self._current_panel()
        if not panel.current_uuid:
            QMessageBox.warning(self, "단말 미연결", "먼저 기기를 연결해주세요.")
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
            current = d.app_current()
            self._current_package = current.get("package", "")
            self._current_activity = current.get("activity", "")
            self._activity_lbl.setText(f"Activity: {self._current_package}/{self._current_activity}")
        except Exception as e:
            QMessageBox.warning(self, "불러오기 실패", str(e))
            return

        self._resource_id_lbl.setText("resourceId: -")
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
                # 토글/체크박스/스위치류를 "지금 켜져 있나"로 판단하려면 이 두 값이
                # 필요합니다(checkable=이 요소가 토글 가능한 종류인지,
                # checked=지금 켜져 있는지). uiautomator2의 .info와 같은 키 이름을
                # 그대로 씁니다.
                "checkable": node.attrib.get("checkable", "false") == "true",
                "checked": node.attrib.get("checked", "false") == "true",
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
            self._resource_id_lbl.setText("resourceId: -")
            return
        node = self._nodes[row]
        self._selected_node = node
        if self._editing_name:
            # 화면에서 새 요소를 고르면 "수정" 모드는 종료하고 새로 만드는 흐름으로 돌아갑니다.
            self._editing_name = None
            self._name_edit.clear()
            self._channel_role_combo.setCurrentIndex(0)
            self._editing_hint_lbl.setText("")
            self._editing_hint_lbl.setVisible(False)
            self._btn_save.setText("이름으로 저장")
        self._detail_labels["resource_id"].setText(node["resource_id"] or "-")
        self._detail_labels["text"].setText(node["text"] or "-")
        self._detail_labels["desc"].setText(node.get("desc") or "-")
        self._detail_labels["class_name"].setText(node["class_name"] or "-")
        self._detail_labels["checkable"].setText(_bool_label(node.get("checkable")))
        self._detail_labels["checked"].setText(_bool_label(node.get("checked")))
        self._resource_id_lbl.setText(f"resourceId: {node['resource_id'] or '-'}")
        self._render_screenshot(highlight=node["bounds"])

    def _render_screenshot(self, highlight):
        if self._pixmap_orig is None:
            return
        pixmap = self._pixmap_orig.copy()
        if highlight:
            painter = QPainter(pixmap)
            painter.setPen(QPen(QColor(Navy.danger), 4))
            x1, y1, x2, y2 = highlight
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)
            painter.end()
        self._screen_lbl.set_orig_size(self._pixmap_orig.width(), self._pixmap_orig.height())
        if pixmap.width() > 380:
            pixmap = pixmap.scaledToWidth(380, Qt.SmoothTransformation)
        self._screen_lbl.setPixmap(pixmap)

    def _on_screen_clicked(self, x, y):
        candidates = [
            (i, node)
            for i, node in enumerate(self._nodes)
            if node["bounds"][0] <= x <= node["bounds"][2] and node["bounds"][1] <= y <= node["bounds"][3]
        ]
        if not candidates:
            return

        def area(node):
            x1, y1, x2, y2 = node["bounds"]
            return (x2 - x1) * (y2 - y1)

        row, _ = min(candidates, key=lambda pair: area(pair[1]))
        self._list.setCurrentRow(row)

    # ---------- 폴더 ----------
    def _refresh_folder_combo(self):
        self._folder_combo.blockSignals(True)
        current = self._folder_combo.currentText()
        self._folder_combo.clear()
        if self._current_project:
            self._folder_combo.addItems(object_store.list_folders(self._current_project))
        idx = self._folder_combo.findText(current)
        self._folder_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._folder_combo.blockSignals(False)

    def _on_add_folder_clicked(self):
        if not self._current_project:
            QMessageBox.warning(self, "프로젝트 미선택", "먼저 왼쪽에서 프로젝트를 선택해주세요.")
            return
        name, ok = QInputDialog.getText(self, "폴더 추가", "새 폴더 이름 (화면/기능별로 객체를 묶어둘 이름):")
        if not ok or not name.strip():
            return
        object_store.add_folder(self._current_project, name.strip())
        self._refresh_folder_combo()
        idx = self._folder_combo.findText(name.strip())
        if idx >= 0:
            self._folder_combo.setCurrentIndex(idx)
        self._refresh_saved_list()

    # ---------- 이름 붙여 저장 / 수정 / 저장된 목록 ----------
    def _reset_edit_form(self, checked=False):
        self._editing_name = None
        self._name_edit.clear()
        self._channel_role_combo.setCurrentIndex(0)
        self._editing_hint_lbl.setText("")
        self._editing_hint_lbl.setVisible(False)
        self._btn_save.setText("이름으로 저장")

    def _on_folder_toggled(self, folder):
        if folder in self._collapsed_folders:
            self._collapsed_folders.discard(folder)
        else:
            self._collapsed_folders.add(folder)
        # 이 시그널은 폴더 헤더 위젯 자신의 mousePressEvent 처리 도중에 옵니다.
        # 여기서 바로 목록을 다시 그리면(clear()) 그 이벤트를 처리 중인 위젯 자신이
        # 통째로 삭제되므로(-> _on_object_dropped_on_folder와 같은 문제), 지금 처리
        # 중인 이벤트가 끝난 뒤로 미룹니다.
        QTimer.singleShot(0, self._refresh_saved_list)

    def _on_folder_edit_requested(self, folder):
        if not self._current_project:
            return
        new_name, ok = QInputDialog.getText(self, "폴더 이름 수정", "새 폴더 이름:", text=folder)
        new_name = (new_name or "").strip()
        if not ok or not new_name or new_name == folder:
            return
        if not object_store.rename_folder(self._current_project, folder, new_name):
            QMessageBox.warning(self, "수정 실패", "폴더 이름을 바꾸지 못했습니다.")
            return
        if folder in self._collapsed_folders:
            self._collapsed_folders.discard(folder)
            self._collapsed_folders.add(new_name)
        self._refresh_folder_combo()
        # 수정 버튼도 지금 지우려는 헤더 위젯 안에 있는 자식이라 위와 같은 이유로 미룹니다.
        QTimer.singleShot(0, self._refresh_saved_list)

    def _on_folder_delete_requested(self, folder):
        if not self._current_project:
            return
        count = sum(
            1
            for node in object_store.list_objects(self._current_project).values()
            if object_store.object_folder(node, self._current_project) == folder
        )
        msg = (
            f"'{folder}' 폴더와 그 안의 객체 {count}개를 모두 삭제할까요?"
            if count
            else f"'{folder}' 폴더를 삭제할까요?"
        )
        ret = QMessageBox.question(
            self, "폴더 삭제", msg, QMessageBox.Yes | QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        was_editing_in_folder = self._editing_name is not None and object_store.object_folder(
            object_store.list_objects(self._current_project).get(self._editing_name, {"folder": None}),
            self._current_project,
        ) == folder
        object_store.delete_folder(self._current_project, folder)
        self._collapsed_folders.discard(folder)
        if was_editing_in_folder:
            self._reset_edit_form()
        self._refresh_folder_combo()
        # 삭제 버튼도 지금 지우려는 헤더 위젯 안에 있는 자식이라 위 수정 버튼과 같은
        # 이유로 미룹니다.
        QTimer.singleShot(0, self._refresh_saved_list)

    def _on_object_dropped_on_folder(self, name, folder):
        if not self._current_project:
            return
        node = object_store.list_objects(self._current_project).get(name)
        if node is None or object_store.object_folder(node, self._current_project) == folder:
            return
        node = dict(node)
        node["folder"] = folder
        object_store.save_object(self._current_project, name, node)
        if self._editing_name == name:
            idx = self._folder_combo.findText(folder)
            self._folder_combo.setCurrentIndex(idx if idx >= 0 else 0)
        # 이 핸들러는 드롭 처리 도중(=드래그를 시작한 행 라벨의 이벤트 처리 스택 안)에서
        # 불립니다. 여기서 바로 목록을 다시 그리면 그 라벨이 통째로 삭제되므로, 드래그가
        # 끝난 뒤로 미룹니다.
        QTimer.singleShot(0, self._refresh_saved_list)

    def _on_saved_item_clicked(self, name):
        if not name or not self._current_project:
            return
        node = object_store.list_objects(self._current_project).get(name)
        if node is None:
            return

        self._editing_name = name
        self._selected_node = None
        self._name_edit.setText(name)
        self._editing_hint_lbl.setText(
            f"'{name}' 수정 중 — 이름/폴더를 바꾸고 저장하면 반영됩니다. "
            f"가리키는 요소 자체를 바꾸려면 왼쪽 화면에서 다시 골라주세요."
        )
        self._editing_hint_lbl.setVisible(True)
        self._btn_save.setText("수정 저장")

        folder = object_store.object_folder(node, self._current_project)
        idx = self._folder_combo.findText(folder)
        self._folder_combo.setCurrentIndex(idx if idx >= 0 else 0)

        role_idx = self._channel_role_combo.findText(node.get("channel_role") or "(없음)")
        self._channel_role_combo.setCurrentIndex(role_idx if role_idx >= 0 else 0)

        self._detail_labels["resource_id"].setText(node.get("resource_id") or "-")
        self._detail_labels["text"].setText(node.get("text") or "-")
        self._detail_labels["desc"].setText(node.get("desc") or "-")
        self._detail_labels["class_name"].setText(node.get("class_name") or "-")
        self._detail_labels["checkable"].setText(_bool_label(node.get("checkable")))
        self._detail_labels["checked"].setText(_bool_label(node.get("checked")))

    def _save_named_object(self):
        if not self._current_project:
            QMessageBox.warning(self, "프로젝트 미선택", "먼저 왼쪽에서 프로젝트를 선택해주세요.")
            return
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "이름 필요", "저장할 이름을 입력해주세요.")
            return
        folder = self._folder_combo.currentText() or object_store.default_folder_name(self._current_project)
        role = self._channel_role_combo.currentText()
        channel_role = role if role in ("주채널", "부채널") else None

        if self._editing_name:
            existing = object_store.list_objects(self._current_project).get(self._editing_name)
            if existing is None:
                QMessageBox.warning(self, "객체 없음", "수정하려던 객체를 찾을 수 없습니다 (이미 삭제됐을 수 있음).")
                self._reset_edit_form()
                self._refresh_saved_list()
                return
            node = dict(existing)
            node["folder"] = folder
            if channel_role:
                node["channel_role"] = channel_role
            else:
                node.pop("channel_role", None)
            if self._editing_name != name:
                object_store.delete_object(self._current_project, self._editing_name)
            object_store.save_object(self._current_project, name, node)
        else:
            if not self._selected_node:
                QMessageBox.warning(self, "요소 미선택", "가운데 목록에서 저장할 요소를 먼저 선택해주세요.")
                return
            node = dict(self._selected_node)
            node["package"] = self._current_package
            node["activity"] = self._current_activity
            node["folder"] = folder
            if channel_role:
                node["channel_role"] = channel_role
            object_store.save_object(self._current_project, name, node)

        self._reset_edit_form()
        self._refresh_saved_list()

    def _refresh_saved_list(self):
        # QListWidgetItem의 기본 체크 표시가 이 앱의 Fluent 테마 아래에서는 그려지지
        # 않아서(사실상 안 보임), Group/User List에서 이미 검증된 방식대로 각 행에
        # 직접 스타일링한 토글 버튼을 체크박스로 붙입니다.
        self._saved_list.clear()
        self._saved_checkboxes = {}
        if not self._current_project:
            self._saved_count.setText("0")
            return
        saved = object_store.list_objects(self._current_project)

        default_name = object_store.default_folder_name(self._current_project)
        by_folder = {folder: [] for folder in object_store.list_folders(self._current_project)}
        for name, node in saved.items():
            by_folder.setdefault(object_store.object_folder(node, self._current_project), []).append((name, node))

        self._saved_count.setText(str(len(saved)))

        for folder, items in by_folder.items():
            collapsed = folder in self._collapsed_folders
            arrow = "▶" if collapsed else "▼"
            header = QListWidgetItem()
            # 클릭(펼치기/접기)은 받아야 하니 Enabled는 켜두고, 파란 선택 표시만 안 뜨게
            # Selectable은 뺍니다. 실제 내용/상호작용은 아래 _FolderHeaderRow 위젯이 담당합니다.
            header.setFlags(Qt.ItemIsEnabled)
            header.setData(Qt.UserRole + 1, folder)
            self._saved_list.addItem(header)

            header_row = _FolderHeaderRow(
                folder, f"{arrow}  {folder}  ({len(items)})",
                can_edit=True, can_delete=folder != default_name,
            )
            header_row.toggled.connect(lambda f=folder: self._on_folder_toggled(f))
            header_row.editRequested.connect(self._on_folder_edit_requested)
            header_row.deleteRequested.connect(self._on_folder_delete_requested)
            # 아래 객체 행과 같은 이유로(목록 QSS의 item padding 때문에) 여유를 더 안 주면
            # 글자가 위아래로 잘립니다.
            header.setSizeHint(QSize(0, header_row.sizeHint().height() + 10))
            self._saved_list.setItemWidget(header, header_row)

            if collapsed:
                continue

            for name, node in items:
                hint = node.get("resource_id") or node.get("text") or node.get("class_name") or ""
                # 긴 resourceId가 행 폭을 밀어버리지 않도록 앞쪽을 줄입니다
                # (뒤쪽의 .../id/xxx 부분이 식별에 쓸모 있으므로 꼬리를 남깁니다).
                if len(hint) > 40:
                    hint = "…" + hint[-39:]
                if node.get("channel_role"):
                    hint = f"[{node['channel_role']}] {hint}"

                item = QListWidgetItem()
                item.setData(Qt.UserRole, name)
                item.setData(Qt.UserRole + 1, folder)
                self._saved_list.addItem(item)

                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(6, 4, 6, 4)
                row_layout.setSpacing(8)

                checkbox = QPushButton()
                checkbox.setCheckable(True)
                checkbox.setFixedSize(20, 20)
                checkbox.setCursor(Qt.PointingHandCursor)
                checkbox.clicked.connect(lambda checked=False, cb=checkbox: self._style_saved_checkbox(cb))
                self._style_saved_checkbox(checkbox)
                row_layout.addWidget(checkbox)

                # 이름은 진하게, 뒤에 붙는 resourceId/text 힌트는 흐리게 두 톤으로 보여줍니다.
                label = _ObjectRowLabel(
                    f"<span style='color:{Navy.text};'>{html.escape(name)}</span>"
                    f"<span style='color:{Navy.text_muted};'>  {html.escape(hint)}</span>",
                    name,
                )
                label.setFont(kfont(10))
                label.setCursor(Qt.PointingHandCursor)
                label.clicked.connect(lambda n=name: self._on_saved_item_clicked(n))
                row_layout.addWidget(label, 1)

                # 목록 QSS의 item padding까지 감안해 높이에 여유를 주지 않으면 글자가 위아래로
                # 잘립니다. 폭은 0으로 두어 긴 힌트 때문에 가로 스크롤바가 생기지 않게 합니다.
                item.setSizeHint(QSize(0, row.sizeHint().height() + 10))
                self._saved_list.setItemWidget(item, row)
                self._saved_checkboxes[name] = checkbox

    @staticmethod
    def _style_saved_checkbox(checkbox):
        if checkbox.isChecked():
            checkbox.setIcon(qta.icon("fa5s.check", color="white"))
            checkbox.setIconSize(QSize(11, 11))
            checkbox.setStyleSheet(
                f"QPushButton {{ background-color:{Navy.navy}; border:2px solid {Navy.navy}; "
                f"border-radius:4px; }}"
            )
        else:
            checkbox.setIcon(QIcon())
            checkbox.setStyleSheet(
                f"QPushButton {{ background-color:{Navy.surface}; border:2px solid {Navy.border_strong}; "
                f"border-radius:4px; }}"
                f"QPushButton:hover {{ border-color:{Navy.accent}; }}"
            )

    def _checked_saved_object_names(self):
        return [name for name, cb in self._saved_checkboxes.items() if cb.isChecked()]

    def _delete_selected_saved_object(self):
        if not self._current_project:
            return
        names = self._checked_saved_object_names()
        if not names:
            QMessageBox.warning(self, "객체 미선택", "삭제할 객체를 체크박스로 선택해주세요.")
            return
        ret = QMessageBox.question(
            self, "삭제 확인", f"체크한 {len(names)}개 객체를 삭제할까요?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        for name in names:
            object_store.delete_object(self._current_project, name)
        if self._editing_name in names:
            self._reset_edit_form()
        self._refresh_saved_list()

    def _copy_or_move_selected_saved_object(self, move):
        if not self._current_project:
            return
        names = self._checked_saved_object_names()
        if not names:
            QMessageBox.warning(self, "객체 미선택", "복사/이동할 객체를 체크박스로 선택해주세요.")
            return

        targets = [p for p in PROJECT_HANDLERS if p != self._current_project]
        if not targets:
            QMessageBox.information(self, "대상 없음", "복사/이동할 다른 프로젝트가 없습니다.")
            return

        action_label = "이동" if move else "복사"
        target, ok = QInputDialog.getItem(
            self, "대상 프로젝트 선택",
            f"체크한 {len(names)}개 객체를 어느 프로젝트로 {action_label}할까요?",
            targets, 0, False,
        )
        if not ok or not target:
            return

        existing = object_store.list_objects(target)
        duplicates = [name for name in names if name in existing]
        if duplicates:
            ret = QMessageBox.question(
                self, "이름 중복",
                f"'{target}' 프로젝트에 이미 있는 객체 {len(duplicates)}개({', '.join(duplicates)})를 덮어쓸까요?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return

        for name in names:
            if move:
                object_store.move_object(self._current_project, target, name)
            else:
                object_store.copy_object(self._current_project, target, name)

        self._refresh_saved_list()
        QMessageBox.information(self, "완료", f"{len(names)}개 객체를 '{target}' 프로젝트로 {action_label}했습니다.")
