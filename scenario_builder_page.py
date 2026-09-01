import threading
import time

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import PrimaryPushButton, TogglePushButton
import qtawesome as qta

import object_store
import scenario_runner
import scenario_store
from device_panel import PROJECT_HANDLERS
from ui_common import Palette, add_shadow, card_css, clear_layout, kfont, make_button, styled

# 동작 정의와 실제 실행 로직은 화면과 분리해 scenario_runner에 모아뒀습니다
# (프로젝트 창의 시나리오 목록에서도 같은 엔진으로 실행합니다).
ACTION_META = scenario_runner.ACTION_META


class _RunSignals(QObject):
    log = Signal(str)


class ScenarioBuilderPage(QWidget):
    """객체 관리에서 이름 붙여 저장해둔 객체들을 골라 클릭/입력/대기 같은 동작을
    순서대로 쌓아서 코드 한 줄 없이 시나리오를 만드는 화면.
    [프로젝트 목록] - [저장된 객체 + 동작 선택] - [작성 중인 스텝 목록 + 저장/불러오기/실행]
    3단 구성입니다. 실행은 연결된 단말(A/B)에 그대로 실제 동작을 보냅니다."""

    def __init__(self, panel_a, panel_b, parent=None):
        super().__init__(parent)
        self.setObjectName("scenarioBuilderInterface")
        self.panel_a = panel_a
        self.panel_b = panel_b
        self._current_project = None
        self._steps = []
        self._project_buttons = {}

        self._run_signals = _RunSignals()
        self._run_signals.log.connect(self._append_log)

        self.panel_a.signals.device_ready.connect(self._on_device_a_ready)
        self.panel_b.signals.device_ready.connect(self._on_device_b_ready)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(16)

        # 프로젝트 목록을 마지막에 만드는 이유: 그 안에서 첫 프로젝트를 자동 선택하며
        # _refresh_object_list()/_refresh_step_list()/_refresh_saved_scenarios()가 다른
        # 패널의 위젯(_object_list, _step_list, _saved_list 등)을 바로 건드리는데, 그
        # 위젯들은 아래 두 패널을 먼저 만들어야 존재합니다. 화면상 배치는 addWidget 순서
        # (project -> add-step -> step)로 그대로 유지됩니다.
        add_step_panel = self._build_add_step_panel()
        step_panel = self._build_step_panel()
        project_list = self._build_project_list()

        outer.addWidget(project_list, 2)
        outer.addWidget(add_step_panel, 3)
        outer.addWidget(step_panel, 5)

    def showEvent(self, event):
        super().showEvent(event)
        # "프로젝트 관리" 화면에서 새 프로젝트를 추가하고 돌아왔을 때도 목록이
        # 최신 상태로 보이도록 이 화면이 다시 보일 때마다 새로고침합니다.
        self._refresh_project_buttons()

    # ---------- 1단: 프로젝트 목록 ----------
    def _build_project_list(self):
        self._project_list_card = styled(QFrame(), card_css())
        layout = QVBoxLayout(self._project_list_card)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(6)

        title = QLabel("프로젝트")
        title.setFont(kfont(12, True))
        title.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(title)

        # 프로젝트 버튼들은 _refresh_project_buttons()가 매번 통째로 지우고 다시 그리므로,
        # 아래 기기 연결 섹션까지 같이 지워지지 않도록 별도의 내부 레이아웃에 담습니다.
        self._project_list_layout = QVBoxLayout()
        self._project_list_layout.setSpacing(6)
        layout.addLayout(self._project_list_layout)
        self._refresh_project_buttons()

        layout.addSpacing(10)

        device_title = QLabel("기기")
        device_title.setFont(kfont(12, True))
        device_title.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(device_title)

        self._btn_connect_device = PrimaryPushButton(qta.icon("fa5s.plug", color="white"), "기기 연결")
        self._btn_connect_device.setFixedHeight(30)
        self._btn_connect_device.setFont(kfont(11, True))
        self._btn_connect_device.setCursor(Qt.PointingHandCursor)
        self._btn_connect_device.clicked.connect(self._on_connect_device_clicked)
        layout.addWidget(self._btn_connect_device)

        self._device_status_lbl = QLabel("연결된 단말 없음")
        self._device_status_lbl.setFont(kfont(10))
        self._device_status_lbl.setStyleSheet(f"color:{Palette.text_sub};")
        self._device_status_lbl.setWordWrap(True)
        layout.addWidget(self._device_status_lbl)

        return add_shadow(self._project_list_card)

    def _on_connect_device_clicked(self):
        # 실제 기기 탐색/연결 로직은 panel_a에 이미 연결돼 있는 버튼(App.check_devices)을
        # 그대로 눌러 재사용합니다. 이 화면에서 새로 구현하지 않습니다.
        self.panel_a.btn_connect.click()

    def _on_device_a_ready(self, info):
        if info:
            self._device_status_lbl.setText(f"A 단말 연결됨: {info.get('model', '')}")
            self._device_status_lbl.setStyleSheet(f"color:{Palette.blue};")
        else:
            self._device_status_lbl.setText("연결된 단말 없음")
            self._device_status_lbl.setStyleSheet(f"color:{Palette.text_sub};")

    def _on_device_b_ready(self, info):
        if info:
            self._device_status_lbl.setText(f"B 단말 연결됨: {info.get('model', '')}")
            self._device_status_lbl.setStyleSheet(f"color:{Palette.blue};")

    def _refresh_project_buttons(self):
        clear_layout(self._project_list_layout, keep=0)
        self._project_buttons = {}
        group = QButtonGroup(self._project_list_card)
        group.setExclusive(True)
        for proj_name in PROJECT_HANDLERS:
            btn = TogglePushButton(proj_name)
            btn.setFont(kfont(11, True))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
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
        self._steps = []
        self._refresh_step_list()
        self._refresh_object_list()
        self._refresh_saved_scenarios()

    # ---------- 2단: 저장된 객체 + 동작 선택 ----------
    def _build_add_step_panel(self):
        card = styled(QFrame(), card_css())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(6)

        obj_header = QHBoxLayout()
        title = QLabel("① 저장된 객체")
        title.setFont(kfont(12, True))
        title.setStyleSheet(f"color:{Palette.text_sub};")
        obj_header.addWidget(title)
        obj_header.addStretch(1)
        btn_refresh = make_button(
            "", Palette.neutral_bg, Palette.text_main, Palette.neutral_hover,
            height=24, radius=6, icon_name="fa5s.sync-alt", icon_size=13,
        )
        btn_refresh.setToolTip("객체 관리에서 저장한 최신 목록으로 새로고침")
        btn_refresh.clicked.connect(self._refresh_object_list)
        obj_header.addWidget(btn_refresh)
        layout.addLayout(obj_header)

        self._object_list = QListWidget()
        layout.addWidget(self._object_list, 1)

        action_title = QLabel("② 동작")
        action_title.setFont(kfont(12, True))
        action_title.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(action_title)

        self._action_combo = QComboBox()
        for key, (label, *_rest) in ACTION_META.items():
            self._action_combo.addItem(label, key)
        self._action_combo.currentIndexChanged.connect(self._on_action_changed)
        layout.addWidget(self._action_combo)

        self._value_edit = QLineEdit()
        self._value_edit.setStyleSheet(
            f"QLineEdit {{ background-color:#FFFFFF; color:{Palette.text_main}; "
            f"border:1px solid {Palette.border}; border-radius:6px; padding:4px 8px; }}"
        )
        layout.addWidget(self._value_edit)
        self._on_action_changed(0)

        btn_add = PrimaryPushButton(qta.icon("fa5s.plus", color="white"), "스텝 추가")
        btn_add.setFixedHeight(30)
        btn_add.setFont(kfont(11, True))
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._add_step)
        layout.addWidget(btn_add)

        return add_shadow(card)

    def _on_action_changed(self, _index):
        key = self._action_combo.currentData()
        _label, needs_object, needs_value, placeholder = ACTION_META[key]
        self._object_list.setEnabled(needs_object)
        self._value_edit.setEnabled(needs_value)
        self._value_edit.setPlaceholderText(placeholder)
        if not needs_value:
            self._value_edit.clear()

    def _refresh_object_list(self):
        self._object_list.clear()
        if not self._current_project:
            return
        saved = object_store.list_objects(self._current_project)

        by_folder = {folder: [] for folder in object_store.list_folders(self._current_project)}
        for name, node in saved.items():
            by_folder.setdefault(object_store.object_folder(node), []).append((name, node))

        for folder, items in by_folder.items():
            if not items:
                continue
            header = QListWidgetItem(f"📁 {folder}")
            header.setFlags(Qt.NoItemFlags)
            header.setFont(kfont(10, True))
            header.setForeground(QColor(Palette.text_sub))
            self._object_list.addItem(header)

            for name, node in items:
                hint = node.get("resource_id") or node.get("text") or node.get("class_name") or ""
                item = QListWidgetItem(f"  {name}  —  {hint}")
                item.setData(Qt.UserRole, name)
                self._object_list.addItem(item)

    def _add_step(self):
        if not self._current_project:
            QMessageBox.warning(self, "프로젝트 미선택", "먼저 왼쪽에서 프로젝트를 선택해주세요.")
            return

        key = self._action_combo.currentData()
        _label, needs_object, needs_value, _placeholder = ACTION_META[key]

        obj_name = None
        if needs_object:
            item = self._object_list.currentItem()
            if not item:
                QMessageBox.warning(self, "객체 미선택", "왼쪽 목록에서 이 동작에 쓸 객체를 먼저 선택해주세요.")
                return
            obj_name = item.data(Qt.UserRole)

        value = self._value_edit.text().strip() if needs_value else ""
        if key == "set_text" and not value:
            QMessageBox.warning(self, "값 필요", "입력할 텍스트를 적어주세요.")
            return

        self._steps.append({"action": key, "object": obj_name, "value": value})
        self._refresh_step_list()

    # ---------- 3단: 작성 중인 스텝 + 저장/불러오기/실행 ----------
    def _build_step_panel(self):
        card = styled(QFrame(), card_css())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(6)

        saved_title = QLabel("저장된 시나리오 (더블클릭: 불러오기)")
        saved_title.setFont(kfont(11, True))
        saved_title.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(saved_title)

        self._saved_list = QListWidget()
        self._saved_list.itemDoubleClicked.connect(self._load_selected_scenario)
        layout.addWidget(self._saved_list, 1)

        btn_delete_saved = make_button(
            "선택한 저장본 삭제", Palette.danger_bg, Palette.danger, Palette.danger_bg_hover,
            height=26, icon_name="fa5s.trash-alt",
        )
        btn_delete_saved.clicked.connect(self._delete_selected_scenario)
        layout.addWidget(btn_delete_saved)

        layout.addSpacing(10)

        title = QLabel("작성 중인 시나리오")
        title.setFont(kfont(12, True))
        title.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(title)

        self._step_list = QListWidget()
        layout.addWidget(self._step_list, 1)

        step_btn_row = QHBoxLayout()
        btn_up = make_button(
            "", Palette.neutral_bg, Palette.text_main, Palette.neutral_hover,
            height=26, radius=6, icon_name="fa5s.arrow-up", icon_size=13,
        )
        btn_up.clicked.connect(lambda: self._move_step(-1))
        btn_down = make_button(
            "", Palette.neutral_bg, Palette.text_main, Palette.neutral_hover,
            height=26, radius=6, icon_name="fa5s.arrow-down", icon_size=13,
        )
        btn_down.clicked.connect(lambda: self._move_step(1))
        btn_del = make_button(
            "스텝 삭제", Palette.danger_bg, Palette.danger, Palette.danger_bg_hover,
            height=26, icon_name="fa5s.trash-alt",
        )
        btn_del.clicked.connect(self._delete_step)
        step_btn_row.addWidget(btn_up)
        step_btn_row.addWidget(btn_down)
        step_btn_row.addWidget(btn_del, 1)
        layout.addLayout(step_btn_row)

        layout.addSpacing(8)

        save_row = QHBoxLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("이 시나리오의 이름")
        self._name_edit.setStyleSheet(
            f"QLineEdit {{ background-color:#FFFFFF; color:{Palette.text_main}; "
            f"border:1px solid {Palette.border}; border-radius:6px; padding:4px 8px; }}"
        )
        save_row.addWidget(self._name_edit, 1)
        btn_save = PrimaryPushButton(qta.icon("fa5s.save", color="white"), "저장")
        btn_save.setFixedHeight(30)
        btn_save.setFont(kfont(11, True))
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self._save_scenario)
        save_row.addWidget(btn_save)
        layout.addLayout(save_row)

        layout.addSpacing(8)
        run_row = QHBoxLayout()
        run_row.addStretch(1)
        btn_run = PrimaryPushButton(qta.icon("fa5s.play", color="white"), "실행")
        btn_run.setFixedHeight(28)
        btn_run.setFont(kfont(11, True))
        btn_run.setCursor(Qt.PointingHandCursor)
        btn_run.clicked.connect(self._run_scenario)
        run_row.addWidget(btn_run)
        layout.addLayout(run_row)

        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setFixedHeight(110)
        self._log_edit.setFont(kfont(10))
        self._log_edit.setStyleSheet(
            f"QTextEdit {{ background-color:{Palette.bg}; color:{Palette.text_main}; "
            f"border:1px solid {Palette.border}; border-radius:{Palette.radius}px; }}"
        )
        layout.addWidget(self._log_edit)

        return add_shadow(card)

    _step_label = staticmethod(scenario_runner.step_label)

    def _refresh_step_list(self):
        self._step_list.clear()
        for step in self._steps:
            self._step_list.addItem(QListWidgetItem(self._step_label(step)))

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

        scenario_store.save_scenario(self._current_project, name, self._steps)
        self._refresh_saved_scenarios()

    def _refresh_saved_scenarios(self):
        self._saved_list.clear()
        if not self._current_project:
            return
        for name, steps in scenario_store.list_scenarios(self._current_project).items():
            item = QListWidgetItem(f"{name}  ({len(steps)}개 스텝)")
            item.setData(Qt.UserRole, name)
            self._saved_list.addItem(item)

    def _load_selected_scenario(self, item):
        name = item.data(Qt.UserRole)
        self._load_scenario_into_editor(name)

    def _load_scenario_into_editor(self, name):
        saved = scenario_store.list_scenarios(self._current_project)
        steps = saved.get(name)
        if steps is None:
            return
        self._steps = [dict(step) for step in steps]
        self._name_edit.setText(name)
        self._refresh_step_list()

    def select_project(self, project_name):
        """런처 메뉴처럼 바깥에서 특정 프로젝트를 골라 이 화면을 열 때 씁니다.
        해당 프로젝트 버튼을 눌린 상태로 만들고 목록들을 그 프로젝트 기준으로 새로 채웁니다."""
        if project_name not in self._project_buttons:
            return False
        self._project_buttons[project_name].setChecked(True)
        self._on_project_selected(project_name)
        return True

    def load_scenario_for_edit(self, project_name, scenario_name):
        """'시나리오' 목록 화면 등 다른 화면에서 특정 프로젝트의 저장된 시나리오를
        바로 편집할 수 있도록, 해당 프로젝트를 선택하고 스텝 편집기에 불러옵니다."""
        if project_name in self._project_buttons:
            self._project_buttons[project_name].setChecked(True)
        self._on_project_selected(project_name)
        self._load_scenario_into_editor(scenario_name)

    def _delete_selected_scenario(self):
        item = self._saved_list.currentItem()
        if not item or not self._current_project:
            return
        name = item.data(Qt.UserRole)
        scenario_store.delete_scenario(self._current_project, name)
        self._refresh_saved_scenarios()

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
        threading.Thread(
            target=self._run_worker,
            args=(panel.current_uuid, self._current_project, steps_snapshot),
            daemon=True,
        ).start()

    def _run_worker(self, uuid, project, steps):
        scenario_runner.run_scenario(
            uuid, project, steps, on_log=self._run_signals.log.emit
        )
