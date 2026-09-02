import threading
import time

from PySide6.QtCore import Qt, QMimeData, QObject, QSize, QTimer, Signal
from PySide6.QtGui import QColor, QDrag
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import object_store
import project_config_store
import scenario_runner
import scenario_store
from device_panel import PROJECT_HANDLERS
from ui_common import (
    FolderHeaderRow,
    Navy,
    kfont,
    navy_button,
    navy_card,
    navy_card_header,
    navy_input_css,
    navy_list_css,
    navy_mono_font,
    navy_page_css,
    navy_page_header,
    navy_scrollbar_css,
)

# 동작 정의와 실제 실행 로직은 화면과 분리해 scenario_runner에 모아뒀습니다
# (프로젝트 창의 시나리오 목록에서도 같은 엔진으로 실행합니다).
ACTION_META = scenario_runner.ACTION_META

# 저장된 시나리오를 폴더 사이로 끌어다 옮길 때 쓰는 드래그 페이로드 형식
# (객체 관리 화면의 _OBJECT_MIME_TYPE과 같은 방식).
_SCENARIO_MIME_TYPE = "application/x-mcx-scenario-name"


class _RunSignals(QObject):
    log = Signal(str)


class _ScenarioRowWidget(QWidget):
    """'저장된 시나리오' 목록 한 줄. 평소엔 이름/스텝 수만 보이다가, 마우스를 올리면
    오른쪽에 순서 이동/수정/삭제 버튼이 나타납니다(객체 관리 화면의 폴더 행과 같은
    방식). 더블클릭해도 수정과 같이 편집기로 불러옵니다.

    누른 채로 끌면 다른 폴더 줄 위에 놓아서 그 폴더로 옮길 수 있습니다(드롭은
    _SavedScenarioList가 받습니다). 오른쪽 버튼들은 자기 마우스 이벤트를 직접
    받으므로 드래그에 걸리지 않습니다."""

    editRequested = Signal(str)
    deleteRequested = Signal(str)
    moveRequested = Signal(str, int)  # (이름, -1: 위로 / +1: 아래로)

    def __init__(self, name, label_text, can_move_up=True, can_move_down=True, parent=None):
        super().__init__(parent)
        self._name = name
        self._press_pos = None
        self._dragging = False
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 6, 3)
        layout.setSpacing(4)

        self._label = QLabel(label_text)
        self._label.setFont(kfont(10))
        self._label.setStyleSheet(f"color:{Navy.text};")
        layout.addWidget(self._label, 1)

        self._btn_up = navy_button("", kind="ghost", height=22, icon_name="fa5s.arrow-up", icon_size=10)
        self._btn_up.setFixedWidth(22)
        self._btn_up.setToolTip("위로 이동")
        self._btn_up.setEnabled(can_move_up)
        self._btn_up.clicked.connect(lambda: self.moveRequested.emit(self._name, -1))
        self._btn_up.setVisible(False)
        layout.addWidget(self._btn_up)

        self._btn_down = navy_button("", kind="ghost", height=22, icon_name="fa5s.arrow-down", icon_size=10)
        self._btn_down.setFixedWidth(22)
        self._btn_down.setToolTip("아래로 이동")
        self._btn_down.setEnabled(can_move_down)
        self._btn_down.clicked.connect(lambda: self.moveRequested.emit(self._name, 1))
        self._btn_down.setVisible(False)
        layout.addWidget(self._btn_down)

        self._btn_edit = navy_button("", kind="ghost", height=22, icon_name="fa5s.pen", icon_size=10)
        self._btn_edit.setFixedWidth(24)
        self._btn_edit.setToolTip("수정(편집기로 불러오기)")
        self._btn_edit.clicked.connect(lambda: self.editRequested.emit(self._name))
        self._btn_edit.setVisible(False)
        layout.addWidget(self._btn_edit)

        self._btn_delete = navy_button("", kind="danger", height=22, icon_name="fa5s.trash-alt", icon_size=10)
        self._btn_delete.setFixedWidth(24)
        self._btn_delete.setToolTip("삭제")
        self._btn_delete.clicked.connect(lambda: self.deleteRequested.emit(self._name))
        self._btn_delete.setVisible(False)
        layout.addWidget(self._btn_delete)

    def enterEvent(self, event):
        self._btn_up.setVisible(True)
        self._btn_down.setVisible(True)
        self._btn_edit.setVisible(True)
        self._btn_delete.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._btn_up.setVisible(False)
        self._btn_down.setVisible(False)
        self._btn_edit.setVisible(False)
        self._btn_delete.setVisible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.position().toPoint()
            self._dragging = False
            # 눌림을 여기서 accept하지 않으면 부모인 목록 뷰로 넘어가고, 이후의
            # 마우스 이동도 뷰가 가져가서 아래 mouseMoveEvent가 아예 안 불립니다
            # (객체 관리 화면의 _ObjectRowLabel에서 겪은 것과 같은 문제).
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
            mime.setData(_SCENARIO_MIME_TYPE, self._name.encode("utf-8"))
            drag = QDrag(self)
            drag.setMimeData(mime)
            drag.exec(Qt.MoveAction)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._press_pos is not None:
            self._press_pos = None
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            event.accept()
            self.editRequested.emit(self._name)
            return
        super().mouseDoubleClickEvent(event)


class _SavedScenarioList(QListWidget):
    """저장된 시나리오 목록. 행이 setItemWidget으로 덮여 있어 Qt 기본 드래그는 못
    먹으므로(드래그 시작은 _ScenarioRowWidget이 직접 함), 드롭만 여기서 받아서
    놓인 위치의 폴더로 옮깁니다(객체 관리 화면의 _SavedObjectList와 같은 방식)."""

    scenarioDroppedOnFolder = Signal(str, str)  # (시나리오 이름, 옮길 폴더)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(_SCENARIO_MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(_SCENARIO_MIME_TYPE):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime = event.mimeData()
        if not mime.hasFormat(_SCENARIO_MIME_TYPE):
            event.ignore()
            return
        target_item = self.itemAt(event.position().toPoint())
        if target_item is None and self.count():
            # 목록 아래 빈 공간에 놓으면 맨 마지막 폴더로 보냅니다(아무 일도 안
            # 일어나면 옮겨졌는지 실패했는지 알 수 없어서).
            target_item = self.item(self.count() - 1)
        folder = target_item.data(Qt.UserRole + 1) if target_item else None
        if not folder:
            event.ignore()
            return
        name = bytes(mime.data(_SCENARIO_MIME_TYPE)).decode("utf-8")
        event.acceptProposedAction()
        self.scenarioDroppedOnFolder.emit(name, folder)


class ScenarioBuilderPage(QWidget):
    """객체 관리에서 이름 붙여 저장해둔 객체들을 골라 클릭/입력/대기 같은 동작을
    순서대로 쌓아서 코드 한 줄 없이 시나리오를 만드는 화면.

    [저장된 객체 + 동작 선택] : [저장된 시나리오 + 작성 중인 스텝] 두 칸을 4:6으로
    쓰고, 프로젝트 선택과 기기 연결은 맨 위 제목 줄에 둡니다(예전에는 프로젝트
    목록이 왼쪽 세 번째 칸을 차지했습니다).
    실행은 연결된 단말(A/B)에 그대로 실제 동작을 보냅니다."""

    def __init__(self, panel_a, panel_b, parent=None):
        super().__init__(parent)
        self.setObjectName("scenarioBuilderInterface")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # 자식까지 물들이지 않도록 이 위젯 하나만 가리키는 id 선택자로 바닥색을 칠합니다.
        self.setStyleSheet(navy_page_css("scenarioBuilderInterface"))
        self.panel_a = panel_a
        self.panel_b = panel_b
        self._current_project = None
        self._steps = []
        # 목록에서 접어둔 폴더 이름들 (객체 관리 화면과 같은 방식)
        self._collapsed_object_folders = set()
        self._collapsed_scenario_folders = set()

        self._run_signals = _RunSignals()
        self._run_signals.log.connect(self._append_log)

        self.panel_a.signals.device_ready.connect(self._on_device_a_ready)
        self.panel_b.signals.device_ready.connect(self._on_device_b_ready)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        header, self._breadcrumb = navy_page_header(
            "시나리오 작성",
            "저장해둔 객체를 골라 동작을 쌓아 올리면 코드 없이 시나리오가 됩니다.",
            actions=self._build_header_actions(),
        )
        outer.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        outer.addLayout(body, 1)

        # 프로젝트를 고르면 _refresh_object_list()/_refresh_step_list()/
        # _refresh_saved_scenarios()가 두 패널 안의 위젯(_object_list, _step_list,
        # _saved_list 등)을 바로 건드리므로, 패널을 먼저 다 만든 뒤에 드롭다운을
        # 채웁니다(채우면서 첫 프로젝트가 자동 선택됩니다).
        body.addWidget(self._build_add_step_panel(), 4)
        body.addWidget(self._build_step_panel(), 6)

        self._refresh_project_combo()

    def showEvent(self, event):
        super().showEvent(event)
        # "프로젝트 관리" 화면에서 새 프로젝트를 추가하고 돌아왔을 때도 목록이
        # 최신 상태로 보이도록 이 화면이 다시 보일 때마다 새로고침합니다.
        self._refresh_project_combo()

    # ---------- 제목 줄: 프로젝트 선택 + 기기 연결 ----------
    def _build_header_actions(self):
        """제목 "시나리오 작성" 바로 옆에 붙는 [프로젝트 드롭다운] [기기 연결] [연결 상태].

        예전에는 왼쪽에 프로젝트 목록 카드가 한 칸을 차지했지만, 본문을 저장된 객체와
        저장된 시나리오 두 칸(4:6)에 다 내주려고 제목 줄로 옮겼습니다."""
        self._project_combo = QComboBox()
        self._project_combo.setFixedHeight(32)
        self._project_combo.setMinimumWidth(200)
        self._project_combo.setFont(kfont(10))
        self._project_combo.setStyleSheet(navy_input_css())
        self._project_combo.currentIndexChanged.connect(self._on_project_combo_changed)

        self._btn_connect_device = navy_button(
            "기기 연결", kind="primary", height=32, icon_name="fa5s.plug"
        )
        self._btn_connect_device.clicked.connect(self._on_connect_device_clicked)

        self._device_status_lbl = QLabel("연결된 단말 없음")
        self._device_status_lbl.setFont(kfont(9))
        self._device_status_lbl.setStyleSheet(f"color:{Navy.text_muted};")

        return [self._project_combo, self._btn_connect_device, self._device_status_lbl]

    def _refresh_project_combo(self):
        """등록된 프로젝트로 드롭다운을 다시 채웁니다. 국내/해외가 섞여 있으면 항목
        앞에 지역을 붙여 구분합니다(드롭다운에는 구분선을 넣을 자리가 없습니다).
        고르고 있던 프로젝트는 유지하고, 없으면 첫 번째를 자동으로 고릅니다."""
        self._project_combo.blockSignals(True)
        self._project_combo.clear()
        groups = project_config_store.group_projects_by_region(list(PROJECT_HANDLERS.keys()))
        for group_label, proj_names in groups:
            for proj_name in proj_names:
                label = f"[{group_label}] {proj_name}" if group_label else proj_name
                self._project_combo.addItem(label, proj_name)
        idx = self._project_combo.findData(self._current_project)
        self._project_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._project_combo.blockSignals(False)

        selected = self._project_combo.currentData()
        if selected and selected != self._current_project:
            self._on_project_selected(selected)

    def _on_project_combo_changed(self, _index):
        proj_name = self._project_combo.currentData()
        if proj_name:
            self._on_project_selected(proj_name)

    def _on_connect_device_clicked(self):
        # 실제 기기 탐색/연결 로직은 panel_a에 이미 연결돼 있는 버튼(App.check_devices)을
        # 그대로 눌러 재사용합니다. 이 화면에서 새로 구현하지 않습니다.
        self.panel_a.btn_connect.click()

    def _on_device_a_ready(self, info):
        if info:
            self._device_status_lbl.setText(f"● A 단말 연결됨: {info.get('model', '')}")
            self._device_status_lbl.setStyleSheet(f"color:{Navy.accent};")
        else:
            self._device_status_lbl.setText("연결된 단말 없음")
            self._device_status_lbl.setStyleSheet(f"color:{Navy.text_muted};")

    def _on_device_b_ready(self, info):
        if info:
            self._device_status_lbl.setText(f"● B 단말 연결됨: {info.get('model', '')}")
            self._device_status_lbl.setStyleSheet(f"color:{Navy.accent};")

    def _on_project_selected(self, proj_name):
        self._current_project = proj_name
        self._breadcrumb.setText(proj_name)
        self._collapsed_object_folders = set()
        self._collapsed_scenario_folders = set()
        self._steps = []
        self._refresh_step_list()
        self._refresh_object_list()
        self._refresh_saved_scenarios()

    # ---------- 2단: 저장된 객체 + 동작 선택 ----------
    def _build_add_step_panel(self):
        card = navy_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        btn_refresh = navy_button(
            "", kind="ghost", height=26, icon_name="fa5s.sync-alt", icon_size=12
        )
        btn_refresh.setFixedWidth(30)
        btn_refresh.setToolTip("객체 관리에서 저장한 최신 목록으로 새로고침")
        btn_refresh.clicked.connect(self._refresh_object_list)
        obj_header, self._object_count = navy_card_header(
            "① 저장된 객체", badge=0, actions=[btn_refresh]
        )
        layout.addWidget(obj_header)

        self._object_list = QListWidget()
        self._object_list.setFont(kfont(10))
        self._object_list.setStyleSheet(navy_list_css())
        self._object_list.itemClicked.connect(self._on_object_list_item_clicked)
        layout.addWidget(self._object_list, 1)

        layout.addSpacing(4)
        action_header, _ = navy_card_header("② 동작")
        layout.addWidget(action_header)

        self._action_combo = QComboBox()
        self._action_combo.setFixedHeight(30)
        self._action_combo.setFont(kfont(10))
        self._action_combo.setStyleSheet(navy_input_css())
        for key, (label, *_rest) in ACTION_META.items():
            self._action_combo.addItem(label, key)
        self._action_combo.currentIndexChanged.connect(self._on_action_changed)
        layout.addWidget(self._action_combo)

        # 재난망 문자처럼 실제 개행/탭이 섞인 긴 텍스트를 그대로 넣을 수 있어야 해서
        # 한 줄짜리 QLineEdit 대신 여러 줄 입력이 되는 QPlainTextEdit을 씁니다.
        self._value_edit = QPlainTextEdit()
        self._value_edit.setFixedHeight(70)
        self._value_edit.setFont(kfont(10))
        self._value_edit.setStyleSheet(navy_input_css())
        layout.addWidget(self._value_edit)

        # '토글 상태 맞추기'만 쓰는, 켜짐/꺼짐 중 하나를 고르는 콤보(오타 위험이 있는
        # 자유 입력 대신). 값 입력칸과 자리를 같이 쓰고 동작에 따라 하나만 보입니다.
        self._toggle_state_combo = QComboBox()
        self._toggle_state_combo.setFixedHeight(30)
        self._toggle_state_combo.setFont(kfont(10))
        self._toggle_state_combo.setStyleSheet(navy_input_css())
        self._toggle_state_combo.addItem("켜짐(on)으로 맞추기", "on")
        self._toggle_state_combo.addItem("꺼짐(off)으로 맞추기", "off")
        layout.addWidget(self._toggle_state_combo)

        # '두 객체 값 같은지 확인' / '조건부 클릭'처럼 두 번째 객체가 필요한
        # 동작에서만 쓰는 콤보. 왼쪽 ①목록에서 고른 객체가 첫 번째, 여기서 고른
        # 객체가 두 번째입니다(라벨 문구는 동작에 따라 바뀝니다).
        self._object2_label = QLabel()
        self._object2_label.setFont(kfont(9, True))
        self._object2_label.setStyleSheet(f"color:{Navy.text_muted};")
        layout.addWidget(self._object2_label)

        self._object2_combo = QComboBox()
        self._object2_combo.setFixedHeight(30)
        self._object2_combo.setFont(kfont(10))
        self._object2_combo.setStyleSheet(navy_input_css())
        layout.addWidget(self._object2_combo)

        self._on_action_changed(0)

        btn_add = navy_button("스텝 추가", kind="primary", height=32, icon_name="fa5s.plus")
        btn_add.clicked.connect(self._add_step)
        layout.addWidget(btn_add)

        return card

    def _on_action_changed(self, _index):
        key = self._action_combo.currentData()
        _label, needs_object, needs_value, placeholder, needs_object2 = ACTION_META[key]
        self._object_list.setEnabled(needs_object)
        self._object_list.setStyleSheet(
            navy_list_css() if needs_object
            else navy_list_css() + f"QListWidget {{ background-color:{Navy.surface_sunken}; }}"
        )

        is_toggle = key == "toggle_state"
        self._value_edit.setVisible(needs_value and not is_toggle)
        self._value_edit.setEnabled(needs_value and not is_toggle)
        self._value_edit.setPlaceholderText(placeholder)
        if not needs_value or is_toggle:
            self._value_edit.clear()
        self._toggle_state_combo.setVisible(is_toggle)

        self._object2_label.setVisible(needs_object2)
        self._object2_combo.setVisible(needs_object2)
        if needs_object2:
            self._object2_label.setText(
                "클릭할 객체(위 ① 확인 객체가 화면에 없을 때)"
                if key == "click_if_missing" else "비교 대상(두 번째 객체)"
            )

    def _refresh_object_list(self):
        self._object_list.clear()
        if not self._current_project:
            self._object_count.setText("0")
            self._refresh_object2_combo({})
            return
        saved = object_store.list_objects(self._current_project)
        self._object_count.setText(str(len(saved)))

        by_folder = {folder: [] for folder in object_store.list_folders(self._current_project)}
        for name, node in saved.items():
            by_folder.setdefault(object_store.object_folder(node, self._current_project), []).append((name, node))

        for folder, items in by_folder.items():
            collapsed = folder in self._collapsed_object_folders
            arrow = "▶" if collapsed else "▼"
            header = QListWidgetItem(f"{arrow}  {folder}  ({len(items)})")
            # 접기/펼치기 클릭은 받아야 하니 Enabled는 켜두고, 선택 표시만 안 뜨게
            # Selectable은 뺍니다(객체 관리 화면과 같은 방식).
            header.setFlags(Qt.ItemIsEnabled)
            # 폴더 이름은 옅은 회색이면 잘 안 보여서 본문 색(진한 네이비)으로 씁니다.
            header.setFont(kfont(11, True))
            header.setForeground(QColor(Navy.text))
            header.setData(Qt.UserRole + 1, folder)
            self._object_list.addItem(header)

            if collapsed:
                continue

            for name, node in items:
                hint = node.get("resource_id") or node.get("text") or node.get("class_name") or ""
                # 긴 resourceId가 행 폭을 밀어버리지 않도록 앞쪽을 줄입니다
                # (뒤쪽의 .../id/xxx 부분이 식별에 쓸모 있으므로 꼬리를 남깁니다).
                if len(hint) > 34:
                    hint = "…" + hint[-33:]

                item = QListWidgetItem()
                item.setData(Qt.UserRole, name)
                item.setData(Qt.UserRole + 1, folder)
                self._object_list.addItem(item)

                # 이름은 진하게, resourceId/text 힌트는 흐리게 두 톤으로 보여줍니다.
                # 행 위젯이 목록의 클릭(=스텝에 쓸 객체 선택)을 가로채지 않도록
                # 위젯과 라벨 모두 마우스 이벤트를 통과시킵니다.
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(12, 3, 8, 3)
                row_layout.setSpacing(8)
                name_lbl = QLabel(name)
                name_lbl.setFont(kfont(10, True))
                name_lbl.setStyleSheet(f"color:{Navy.text}; background:transparent;")
                hint_lbl = QLabel(hint)
                hint_lbl.setFont(kfont(9))
                hint_lbl.setStyleSheet(f"color:{Navy.text_muted}; background:transparent;")
                row_layout.addWidget(name_lbl)
                row_layout.addWidget(hint_lbl, 1)
                for w in (row, name_lbl, hint_lbl):
                    w.setAttribute(Qt.WA_TransparentForMouseEvents, True)

                item.setSizeHint(QSize(0, row.sizeHint().height() + 6))
                self._object_list.setItemWidget(item, row)

        self._refresh_object2_combo(saved)

    def _refresh_object2_combo(self, saved):
        """'두 객체 값 같은지 확인'에서 두 번째 객체를 고르는 콤보. 폴더 구분 없이
        이름만 쭉 나열합니다(비교 대상 하나 고르는 용도라 굳이 폴더까지는 필요 없음)."""
        self._object2_combo.blockSignals(True)
        current = self._object2_combo.currentData()
        self._object2_combo.clear()
        for name in saved:
            self._object2_combo.addItem(name, name)
        idx = self._object2_combo.findData(current)
        self._object2_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._object2_combo.blockSignals(False)

    def _on_object_list_item_clicked(self, item):
        """폴더 헤더를 누르면 그 폴더를 접거나 폅니다(객체 행 클릭은 그냥 선택)."""
        folder = item.data(Qt.UserRole + 1)
        if not folder or item.data(Qt.UserRole) is not None:
            return
        if folder in self._collapsed_object_folders:
            self._collapsed_object_folders.discard(folder)
        else:
            self._collapsed_object_folders.add(folder)
        self._refresh_object_list()

    def _add_step(self):
        if not self._current_project:
            QMessageBox.warning(self, "프로젝트 미선택", "먼저 왼쪽에서 프로젝트를 선택해주세요.")
            return

        key = self._action_combo.currentData()
        _label, needs_object, needs_value, _placeholder, needs_object2 = ACTION_META[key]

        obj_name = None
        if needs_object:
            item = self._object_list.currentItem()
            # 폴더 헤더에는 UserRole이 없습니다. 헤더만 눌린 상태로 스텝을 추가하면
            # 객체 없는 스텝이 만들어지므로 같이 걸러냅니다.
            if not item or item.data(Qt.UserRole) is None:
                QMessageBox.warning(self, "객체 미선택", "왼쪽 목록에서 이 동작에 쓸 객체를 먼저 선택해주세요.")
                return
            obj_name = item.data(Qt.UserRole)

        obj2_name = None
        if needs_object2:
            obj2_name = self._object2_combo.currentData()
            if not obj2_name:
                QMessageBox.warning(self, "비교 대상 미선택", "두 번째 객체를 골라주세요.")
                return
            # check_same은 자기 자신과 비교하면 항상 같다고만 나와 의미가 없고,
            # click_if_missing도 '이 객체가 없으면 이 객체를 눌러라'는 애초에
            # 불가능한 조합이라 둘 다 같은 객체 선택을 막습니다.
            if obj2_name == obj_name:
                QMessageBox.warning(self, "같은 객체", "서로 다른 두 객체를 골라주세요.")
                return

        if key == "toggle_state":
            value = self._toggle_state_combo.currentData() or "on"
        else:
            # set_text는 재난망 문자처럼 앞뒤 개행/공백까지 실제로 보내는 값의
            # 일부일 수 있어 그대로 두고, timeout/대기 시간처럼 숫자를 쓰는
            # 값들만 정리해줍니다.
            raw_value = self._value_edit.toPlainText() if needs_value else ""
            value = raw_value if key == "set_text" else raw_value.strip()
        if key == "set_text" and not value:
            QMessageBox.warning(self, "값 필요", "입력할 텍스트를 적어주세요.")
            return

        step = {"action": key, "object": obj_name, "value": value}
        if needs_object2:
            step["object2"] = obj2_name
        self._steps.append(step)
        self._refresh_step_list()

    # ---------- 3단: 작성 중인 스텝 + 저장/불러오기/실행 ----------
    def _build_step_panel(self):
        card = navy_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        btn_add_folder = navy_button(
            "", kind="ghost", height=24, icon_name="fa5s.folder-plus", icon_size=11
        )
        btn_add_folder.setFixedWidth(26)
        btn_add_folder.setToolTip("새 폴더 추가")
        btn_add_folder.clicked.connect(self._on_add_folder_clicked)
        saved_header, self._saved_count = navy_card_header(
            "저장된 시나리오", badge=0, actions=[btn_add_folder]
        )
        layout.addWidget(saved_header)

        saved_hint = QLabel(
            "시나리오를 폴더 줄로 끌어다 놓으면 옮겨집니다. 폴더 줄을 누르면 접히고, "
            "행에 마우스를 올리면 수정/삭제 버튼이 나옵니다(더블클릭도 수정)."
        )
        saved_hint.setFont(kfont(9))
        saved_hint.setWordWrap(True)
        saved_hint.setStyleSheet(f"color:{Navy.text_muted};")
        layout.addWidget(saved_hint)

        self._saved_list = _SavedScenarioList()
        self._saved_list.setFont(kfont(10))
        self._saved_list.setStyleSheet(navy_list_css())
        self._saved_list.scenarioDroppedOnFolder.connect(self._on_scenario_dropped_on_folder)
        layout.addWidget(self._saved_list, 1)

        layout.addSpacing(6)

        btn_add_step_hdr = navy_button(
            "", kind="ghost", height=24, icon_name="fa5s.plus", icon_size=11
        )
        btn_add_step_hdr.setFixedWidth(26)
        btn_add_step_hdr.setToolTip("위 ①②에서 고른 객체+동작으로 스텝 추가")
        btn_add_step_hdr.clicked.connect(self._add_step)

        step_header, self._step_count = navy_card_header(
            "작성 중인 시나리오", badge=0, actions=[btn_add_step_hdr]
        )
        layout.addWidget(step_header)

        # 저장할 때 어느 폴더에 넣을지. 위 "저장된 시나리오" 목록이 이 폴더 기준으로
        # 묶여서 보입니다(수정으로 불러오면 그 시나리오의 폴더로 맞춰집니다).
        folder_row = QHBoxLayout()
        folder_row.setSpacing(6)
        folder_lbl = QLabel("폴더")
        folder_lbl.setFont(kfont(9, True))
        folder_lbl.setFixedWidth(30)
        folder_lbl.setStyleSheet(f"color:{Navy.text_muted};")
        folder_row.addWidget(folder_lbl)
        self._folder_combo = QComboBox()
        self._folder_combo.setFixedHeight(30)
        self._folder_combo.setFont(kfont(10))
        self._folder_combo.setStyleSheet(navy_input_css())
        folder_row.addWidget(self._folder_combo, 1)
        btn_add_folder_2 = navy_button(
            "", kind="ghost", height=30, icon_name="fa5s.folder-plus", icon_size=13
        )
        btn_add_folder_2.setFixedWidth(34)
        btn_add_folder_2.setToolTip("새 폴더 추가")
        btn_add_folder_2.clicked.connect(self._on_add_folder_clicked)
        folder_row.addWidget(btn_add_folder_2)
        layout.addLayout(folder_row)

        name_save_row = QHBoxLayout()
        name_save_row.setSpacing(6)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("이 시나리오의 이름")
        self._name_edit.setFixedHeight(32)
        self._name_edit.setFont(kfont(10))
        self._name_edit.setStyleSheet(navy_input_css())
        name_save_row.addWidget(self._name_edit, 1)
        btn_save = navy_button("저장", kind="primary", height=32, icon_name="fa5s.save")
        btn_save.clicked.connect(self._save_scenario)
        name_save_row.addWidget(btn_save)
        layout.addLayout(name_save_row)

        self._step_list = QListWidget()
        self._step_list.setFont(kfont(10))
        self._step_list.setStyleSheet(navy_list_css())
        layout.addWidget(self._step_list, 1)

        step_btn_row = QHBoxLayout()
        step_btn_row.setSpacing(6)
        btn_up = navy_button("", kind="ghost", height=28, icon_name="fa5s.arrow-up", icon_size=12)
        btn_up.setFixedWidth(34)
        btn_up.setToolTip("선택한 스텝을 위로")
        btn_up.clicked.connect(lambda: self._move_step(-1))
        btn_down = navy_button("", kind="ghost", height=28, icon_name="fa5s.arrow-down", icon_size=12)
        btn_down.setFixedWidth(34)
        btn_down.setToolTip("선택한 스텝을 아래로")
        btn_down.clicked.connect(lambda: self._move_step(1))
        btn_del = navy_button("스텝 삭제", kind="danger", height=28, icon_name="fa5s.trash-alt")
        btn_del.clicked.connect(self._delete_step)
        step_btn_row.addWidget(btn_up)
        step_btn_row.addWidget(btn_down)
        step_btn_row.addWidget(btn_del, 1)
        layout.addLayout(step_btn_row)

        layout.addSpacing(6)

        # 실행은 저장과 성격이 달라(단말에 실제 동작을 보냄) 파란 액센트로 구분하고,
        # 위로 옮긴 이름+저장과 떨어뜨려 둡니다.
        btn_run = navy_button("실행", kind="accent", height=32, icon_name="fa5s.play")
        btn_run.clicked.connect(self._run_scenario)
        layout.addWidget(btn_run)

        # 실행 로그는 터미널처럼 읽히도록 딥네이비 바탕 + 고정폭 글꼴.
        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setFixedHeight(110)
        self._log_edit.setFont(navy_mono_font(9))
        self._log_edit.setStyleSheet(
            f"QTextEdit {{ background-color:{Navy.navy_pressed}; color:#D8E2F2; "
            f"border:none; border-radius:{Navy.radius_sm}px; padding:8px; }}"
            + navy_scrollbar_css()
        )
        layout.addWidget(self._log_edit)

        return card

    _step_label = staticmethod(scenario_runner.step_label)

    def _refresh_step_list(self):
        self._step_list.clear()
        self._step_count.setText(str(len(self._steps)))
        for i, step in enumerate(self._steps, start=1):
            self._step_list.addItem(QListWidgetItem(f"{i}.  {self._step_label(step)}"))

    def _move_step(self, direction):
        row = self._step_list.currentRow()
        new_row = row + direction
        if row < 0 or not (0 <= new_row < len(self._steps)):
            return
        self._steps[row], self._steps[new_row] = self._steps[new_row], self._steps[row]
        self._refresh_step_list()
        self._step_list.setCurrentRow(new_row)

    def _delete_step(self):
        row = self._step_list.currentRow()
        if row < 0:
            return
        del self._steps[row]
        self._refresh_step_list()

    # ---------- 저장 / 불러오기 ----------
    def _save_scenario(self):
        if not self._current_project:
            QMessageBox.warning(self, "프로젝트 미선택", "먼저 왼쪽에서 프로젝트를 선택해주세요.")
            return
        if not self._steps:
            QMessageBox.warning(self, "스텝 없음", "먼저 스텝을 하나 이상 추가해주세요.")
            return
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "이름 필요", "저장할 시나리오 이름을 입력해주세요.")
            return

        folder = self._folder_combo.currentText() or scenario_store.default_folder_name(
            self._current_project
        )
        scenario_store.save_scenario(self._current_project, name, self._steps, folder=folder)
        self._refresh_saved_scenarios()

    # ---------- 저장된 시나리오 폴더 ----------
    def _refresh_folder_combo(self):
        self._folder_combo.blockSignals(True)
        current = self._folder_combo.currentText()
        self._folder_combo.clear()
        if self._current_project:
            self._folder_combo.addItems(scenario_store.list_folders(self._current_project))
        idx = self._folder_combo.findText(current)
        self._folder_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._folder_combo.blockSignals(False)

    def _on_add_folder_clicked(self):
        if not self._current_project:
            QMessageBox.warning(self, "프로젝트 미선택", "먼저 위에서 프로젝트를 선택해주세요.")
            return
        name, ok = QInputDialog.getText(
            self, "폴더 추가", "새 폴더 이름 (기능/화면별로 시나리오를 묶어둘 이름):"
        )
        if not ok or not name.strip():
            return
        scenario_store.add_folder(self._current_project, name.strip())
        self._refresh_saved_scenarios()
        idx = self._folder_combo.findText(name.strip())
        if idx >= 0:
            self._folder_combo.setCurrentIndex(idx)

    def _on_folder_toggled(self, folder):
        if folder in self._collapsed_scenario_folders:
            self._collapsed_scenario_folders.discard(folder)
        else:
            self._collapsed_scenario_folders.add(folder)
        # 이 시그널은 폴더 헤더 위젯 자신의 mousePressEvent 처리 도중에 옵니다.
        # 여기서 바로 목록을 다시 그리면 이벤트를 처리 중인 위젯이 삭제되므로 미룹니다.
        QTimer.singleShot(0, self._refresh_saved_scenarios)

    def _on_folder_edit_requested(self, folder):
        if not self._current_project:
            return
        new_name, ok = QInputDialog.getText(self, "폴더 이름 수정", "새 폴더 이름:", text=folder)
        new_name = (new_name or "").strip()
        if not ok or not new_name or new_name == folder:
            return
        if not scenario_store.rename_folder(self._current_project, folder, new_name):
            QMessageBox.warning(self, "수정 실패", "폴더 이름을 바꾸지 못했습니다.")
            return
        if folder in self._collapsed_scenario_folders:
            self._collapsed_scenario_folders.discard(folder)
            self._collapsed_scenario_folders.add(new_name)
        # 수정 버튼도 다시 그리려는 헤더 위젯 안에 있는 자식이라 위와 같은 이유로 미룹니다.
        QTimer.singleShot(0, self._refresh_saved_scenarios)

    def _on_folder_delete_requested(self, folder):
        if not self._current_project:
            return
        count = sum(
            1
            for name in scenario_store.list_scenarios(self._current_project)
            if scenario_store.scenario_folder(self._current_project, name) == folder
        )
        msg = (
            f"{folder!r} 폴더와 그 안의 시나리오 {count}개를 모두 삭제할까요?"
            if count
            else f"{folder!r} 폴더를 삭제할까요?"
        )
        ret = QMessageBox.question(self, "폴더 삭제", msg, QMessageBox.Yes | QMessageBox.No)
        if ret != QMessageBox.Yes:
            return
        scenario_store.delete_folder(self._current_project, folder)
        self._collapsed_scenario_folders.discard(folder)
        QTimer.singleShot(0, self._refresh_saved_scenarios)

    def _on_scenario_dropped_on_folder(self, name, folder):
        if not self._current_project:
            return
        if scenario_store.scenario_folder(self._current_project, name) == folder:
            return
        scenario_store.set_scenario_folder(self._current_project, name, folder)
        # 이 시그널은 끌던 행 위젯의 드래그 처리 도중에 옵니다. 여기서 바로 목록을
        # 다시 그리면 그 위젯이 통째로 삭제되므로 미룹니다.
        QTimer.singleShot(0, self._refresh_saved_scenarios)

    def _refresh_saved_scenarios(self):
        self._saved_list.clear()
        self._refresh_folder_combo()
        if not self._current_project:
            self._saved_count.setText("0")
            return
        saved = scenario_store.list_scenarios(self._current_project)
        self._saved_count.setText(str(len(saved)))

        default_name = scenario_store.default_folder_name(self._current_project)
        by_folder = {folder: [] for folder in scenario_store.list_folders(self._current_project)}
        for name, steps in saved.items():
            folder = scenario_store.scenario_folder(self._current_project, name)
            by_folder.setdefault(folder, []).append((name, steps))

        for folder, items in by_folder.items():
            collapsed = folder in self._collapsed_scenario_folders
            arrow = "▶" if collapsed else "▼"
            header = QListWidgetItem()
            # 접기/펼치기 클릭은 받아야 하니 Enabled는 켜두고, 파란 선택 표시만 안 뜨게
            # Selectable은 뺍니다. 실제 내용/상호작용은 FolderHeaderRow가 담당합니다.
            header.setFlags(Qt.ItemIsEnabled)
            header.setData(Qt.UserRole + 1, folder)
            self._saved_list.addItem(header)

            header_row = FolderHeaderRow(
                folder, f"{arrow}  {folder}  ({len(items)})",
                can_edit=True, can_delete=folder != default_name,
                delete_tooltip="폴더 삭제 (하위 시나리오 포함)",
            )
            header_row.toggled.connect(lambda f=folder: self._on_folder_toggled(f))
            header_row.editRequested.connect(self._on_folder_edit_requested)
            header_row.deleteRequested.connect(self._on_folder_delete_requested)
            header.setSizeHint(QSize(0, header_row.sizeHint().height() + 10))
            self._saved_list.setItemWidget(header, header_row)

            if collapsed:
                continue

            for i, (name, steps) in enumerate(items):
                item = QListWidgetItem()
                item.setData(Qt.UserRole, name)
                item.setData(Qt.UserRole + 1, folder)
                self._saved_list.addItem(item)

                # 순서 이동은 같은 폴더 안에서만 이뤄지므로(scenario_store.move_scenario),
                # 위/아래 버튼도 폴더 안에서의 자리를 기준으로 켜고 끕니다.
                row = _ScenarioRowWidget(
                    name, f"{name}   {len(steps)}스텝",
                    can_move_up=i > 0, can_move_down=i < len(items) - 1,
                )
                row.editRequested.connect(self._edit_scenario_by_name)
                row.deleteRequested.connect(self._delete_scenario_by_name)
                row.moveRequested.connect(self._move_scenario_by_name)
                # 목록 QSS의 item padding까지 감안해 여유를 안 주면 글자가 위아래로
                # 잘립니다(객체 관리 화면 폴더 행에서 겪은 것과 같은 문제).
                item.setSizeHint(QSize(0, row.sizeHint().height() + 10))
                self._saved_list.setItemWidget(item, row)

    def _edit_scenario_by_name(self, name):
        if not self._current_project:
            return
        self._load_scenario_into_editor(name)

    def _delete_scenario_by_name(self, name):
        if not self._current_project:
            return
        ret = QMessageBox.question(
            self, "삭제 확인", f"'{name}' 시나리오를 삭제할까요?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        scenario_store.delete_scenario(self._current_project, name)
        # 삭제 버튼이 지금 지우려는 행 위젯 자신의 자식이라, 여기서 바로 목록을
        # 다시 그리면(clear()) 그 이벤트를 처리 중인 위젯이 통째로 삭제됩니다
        # (객체 관리 화면의 폴더 행과 같은 이유). 지금 처리 중인 이벤트가 끝난
        # 뒤로 미룹니다.
        QTimer.singleShot(0, self._refresh_saved_scenarios)

    def _move_scenario_by_name(self, name, direction):
        if not self._current_project:
            return
        scenario_store.move_scenario(self._current_project, name, direction)
        # 이동 버튼도 지금 다시 그리려는 행 위젯 안에 있는 자식이라 삭제와 같은
        # 이유로 미룹니다.
        QTimer.singleShot(0, self._refresh_saved_scenarios)

    def _load_scenario_into_editor(self, name):
        saved = scenario_store.list_scenarios(self._current_project)
        steps = saved.get(name)
        if steps is None:
            return
        self._steps = [dict(step) for step in steps]
        self._name_edit.setText(name)
        folder = scenario_store.scenario_folder(self._current_project, name)
        idx = self._folder_combo.findText(folder)
        self._folder_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._refresh_step_list()

    def select_project(self, project_name):
        """런처 메뉴처럼 바깥에서 특정 프로젝트를 골라 이 화면을 열 때 씁니다.
        제목 줄 드롭다운을 그 프로젝트로 맞추고 목록들을 새로 채웁니다.

        이미 그 프로젝트가 골라져 있으면 setCurrentIndex는 시그널을 안 보내므로,
        어느 쪽이든 목록이 새로 채워지도록 _on_project_selected를 직접 부릅니다."""
        idx = self._project_combo.findData(project_name)
        if idx < 0:
            return False
        self._project_combo.blockSignals(True)
        self._project_combo.setCurrentIndex(idx)
        self._project_combo.blockSignals(False)
        self._on_project_selected(project_name)
        return True

    def load_scenario_for_edit(self, project_name, scenario_name):
        """'시나리오' 목록 화면 등 다른 화면에서 특정 프로젝트의 저장된 시나리오를
        바로 편집할 수 있도록, 해당 프로젝트를 선택하고 스텝 편집기에 불러옵니다."""
        if not self.select_project(project_name):
            # 드롭다운에 없는 프로젝트라도(핸들러 미등록 등) 목록만은 그 프로젝트
            # 기준으로 맞춰줍니다.
            self._on_project_selected(project_name)
        self._load_scenario_into_editor(scenario_name)

    # ---------- 실행 ----------
    def _append_log(self, text):
        self._log_edit.append(text)

    def _run_scenario(self):
        if not self._current_project:
            QMessageBox.warning(self, "프로젝트 미선택", "먼저 왼쪽에서 프로젝트를 선택해주세요.")
            return
        if not self._steps:
            QMessageBox.warning(self, "스텝 없음", "실행할 스텝이 없습니다.")
            return

        panel = self.panel_a
        if not panel.current_uuid:
            QMessageBox.warning(self, "단말 미연결", "먼저 기기를 연결해주세요.")
            return

        self._log_edit.clear()
        steps_snapshot = [dict(step) for step in self._steps]
        channel_roles = dict(panel.channel_roles)
        threading.Thread(
            target=self._run_worker,
            args=(panel.current_uuid, self._current_project, steps_snapshot, channel_roles),
            daemon=True,
        ).start()

    def _run_worker(self, uuid, project, steps, channel_roles):
        scenario_runner.run_scenario(
            uuid, project, steps, on_log=self._run_signals.log.emit, channel_roles=channel_roles
        )
