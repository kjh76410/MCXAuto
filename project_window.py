"""프로젝트 창.

런처(데스크톱 아이콘)의 프로젝트 박스를 누르면 뜨는 창입니다. 사이드바가 있는
'관리 창'(ui_logic.App: 프로젝트 관리/객체 관리/시나리오 작성/시나리오)과 달리,
여기는 실제로 테스트를 돌릴 때 보는 화면만 모아둡니다.

단말 A 대시보드(미러링/리스트/로그) 하나로 이루어져 있고, 그 안의 Network &
System Logs 카드(tab_view)에 "시나리오" 탭을 맨 앞에 끼워 넣어 이 프로젝트의
저장된 시나리오 목록(+ 주채널/부채널 지정)을 보여줍니다("반복시나리오" 탭엔
원래 있던 Group/User List + 반복 발신이 그대로 있습니다).

대시보드 위젯은 DevicePanel이 만들어 둔 조각(left_column_widget / right_column_widget,
그 안의 tab_view)을 그대로 가져와 배치합니다(기기 연결/관리 버튼은 이제
left_column_widget 맨 위, 미러링 카드 바로 위에 붙어 있습니다). DevicePanel
인스턴스는 관리 창과 공유하는 하나뿐이라, 이 창이 살아있는 동안 대시보드는
여기에만 보입니다(관리 창에는 더 이상 대시보드 탭이 없습니다).

시나리오 목록에서 항목을 누르면 그 자리에서 바로 실행되고, 진행 로그는 대시보드의
로그창에 그대로 찍힙니다.
"""

import threading

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

import scenario_runner
import scenario_store

# 공통통화그룹은 재난망 프로젝트에만 있는 개념이라, 채널 지정 드롭다운에도
# 이 두 프로젝트일 때만 보여줍니다.
COMMON_CALL_GROUP_PROJECTS = ("재난망", "재난망_LM75")
from ui_common import (
    Navy,
    clear_layout,
    kfont,
    navy_button,
    navy_card,
    navy_card_header,
    navy_input_css,
    navy_page_css,
    styled,
)


class _RunSignals(QObject):
    log = Signal(str)
    result = Signal(str, bool)


class ProjectWindow(QWidget):
    """프로젝트 하나를 기준으로 '대시보드 + 시나리오 목록'을 함께 보여주는 창.
    창은 하나만 만들어 두고 set_project()로 프로젝트만 갈아끼우며 재사용합니다."""

    def __init__(self, panel, project_name=None, parent=None):
        super().__init__(parent)
        self.panel = panel
        self._project = None
        self._run_signals = _RunSignals()
        self._run_signals.log.connect(self._on_run_log)
        self._run_signals.result.connect(self._on_run_result)
        self._running = False
        self._scenario_result_labels = {}

        self.setWindowTitle("MCX QA")
        self.setObjectName("projectWindow")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # 배경은 이 창 자체만 칠하고(자식까지 물들면 카드 안 빈 컨테이너에 회색이 덧칠됩니다),
        # 글자색만 QWidget 전체에 기본값으로 깔아둡니다.
        self.setStyleSheet(
            navy_page_css("projectWindow") + f"QWidget {{ color:{Navy.text}; }}"
        )

        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(12)
        outer.addWidget(self._build_dashboard(), 1)

        # 예전엔 시나리오 목록을 대시보드 오른쪽에 별도 폭 고정 패널로 붙였지만,
        # 이제 Network & System Logs 카드의 tab_view 맨 앞에 "시나리오" 탭으로
        # 넣습니다("반복시나리오" 탭엔 원래 있던 Group/User List + 반복 발신이
        # 그대로 남아 있습니다). ProjectWindow는 앱 시작 시 딱 한 번만 만들어지므로
        # (main.py) 이 insertTab도 한 번만 실행됩니다.
        self.panel.tab_view.insertTab(0, self._build_scenario_panel(), "시나리오")
        self.panel.tab_view.setCurrentIndex(0)

        self.panel.signals.groups_ready.connect(self._refresh_channel_combos)
        self._refresh_channel_combos(self.panel.all_groups)

        if project_name:
            self.set_project(project_name)

    # ---------- 왼쪽: 단말 A 대시보드 ----------
    def _build_dashboard(self):
        # 기기 연결/관리 버튼은 이제 left_column_widget 맨 위(미러링 카드 바로 위)에
        # 붙어 있어서, 두 컬럼을 나란히 놓기만 하면 됩니다.
        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        row.addWidget(self.panel.left_column_widget)
        row.addWidget(self.panel.right_column_widget, 1)
        return holder

    # ---------- Network & System Logs의 "시나리오" 탭 콘텐츠 ----------
    def _build_scenario_panel(self):
        card = navy_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        btn_refresh = navy_button("", kind="ghost", height=24, icon_name="fa5s.sync-alt", icon_size=11)
        btn_refresh.setFixedWidth(26)
        btn_refresh.setToolTip("시나리오 목록 새로고침")
        btn_refresh.clicked.connect(self.refresh_scenarios)
        header, self._scenario_count = navy_card_header("시나리오", badge=0, actions=[btn_refresh])
        layout.addWidget(header)

        self._project_label = QLabel("-")
        self._project_label.setFont(kfont(16, True))
        self._project_label.setStyleSheet(f"color:{Navy.navy};")
        layout.addWidget(self._project_label)

        hint = QLabel("항목을 누르면 연결된 단말에서 바로 실행됩니다.")
        hint.setFont(kfont(9))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{Navy.text_muted}; padding-bottom:4px;")
        layout.addWidget(hint)

        layout.addWidget(self._build_channel_section())

        self._scenario_layout = layout
        layout.addStretch(1)
        return card

    # ---------- 주채널/부채널(+ 재난망 전용 공통통화그룹) 지정 ----------
    def _build_channel_section(self):
        """시나리오에서 채널 역할(주채널/부채널/공통통화그룹)로 저장된 객체가,
        캡처 당시 채널명이 아니라 지금 여기서 고른 실제 채널명으로 동작하게 하는
        드롭다운. 채널 목록은 단말 연결 시 그룹 목록을 읽어야 알 수 있어서(단말
        연결 전엔 비어 있음), 패널의 groups_ready 시그널로 매번 다시 채웁니다.
        공통통화그룹은 재난망/재난망_LM75에만 있는 개념이라, 그 두 프로젝트일
        때만 행을 보여줍니다(set_project에서 _update_channel_row_visibility로
        토글)."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)

        title = QLabel("채널 지정")
        title.setFont(kfont(9, True))
        title.setStyleSheet(f"color:{Navy.text_muted};")
        layout.addWidget(title)

        self._channel_combos = {}
        self._channel_rows = {}
        for role in ("주채널", "부채널", "공통통화그룹"):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            lbl = QLabel(role)
            lbl.setFont(kfont(9))
            lbl.setFixedWidth(60)
            lbl.setStyleSheet(f"color:{Navy.text};")
            row_layout.addWidget(lbl)
            combo = self._make_channel_combo()
            row_layout.addWidget(combo, 1)
            layout.addWidget(row)
            self._channel_combos[role] = combo
            self._channel_rows[role] = row

        return section

    def _make_channel_combo(self):
        combo = QComboBox()
        combo.setFixedHeight(26)
        combo.setFont(kfont(9))
        combo.setStyleSheet(navy_input_css())
        combo.currentTextChanged.connect(self._on_channel_combo_changed)
        return combo

    def _refresh_channel_combos(self, groups=None):
        if groups is None:
            groups = self.panel.all_groups
        names = [g.get("name", "") for g in groups if g.get("name")]

        for role, combo in self._channel_combos.items():
            current = self.panel.channel_roles.get(role) or combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("(미지정)")
            combo.addItems(names)
            idx = combo.findText(current) if current else -1
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)
        # 위에서 blockSignals로 막아둔 채로 채웠으니, 복원된 선택값을 패널에도 반영합니다.
        self._on_channel_combo_changed()

    @staticmethod
    def _combo_channel_value(combo):
        text = combo.currentText()
        return text if text and text != "(미지정)" else None

    def _on_channel_combo_changed(self, _text=None):
        for role, combo in self._channel_combos.items():
            self.panel.channel_roles[role] = self._combo_channel_value(combo)

    def _update_channel_row_visibility(self):
        show_common_group = self._project in COMMON_CALL_GROUP_PROJECTS
        self._channel_rows["공통통화그룹"].setVisible(show_common_group)
        if not show_common_group:
            self.panel.channel_roles["공통통화그룹"] = None

    # ---------- 프로젝트 전환 ----------
    def set_project(self, project_name):
        self._project = project_name
        self.setWindowTitle(f"{project_name} — MCX QA")
        self._project_label.setText(project_name)
        self._update_channel_row_visibility()
        self.refresh_scenarios()

    def refresh_scenarios(self):
        # keep=4: 타이틀 / 프로젝트 이름 / 안내문구 / 주채널·부채널 지정
        clear_layout(self._scenario_layout, keep=4)
        self._scenario_result_labels = {}

        saved = scenario_store.list_scenarios(self._project) if self._project else {}
        self._scenario_count.setText(str(len(saved)))
        if not saved:
            empty = QLabel("저장된 시나리오가 없습니다.\n'시나리오 작성'에서 만들어 주세요.")
            empty.setFont(kfont(10))
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignCenter)
            styled(
                empty,
                f"background-color:{Navy.surface_alt}; color:{Navy.text_muted}; "
                f"border:1px dashed {Navy.border_strong}; border-radius:{Navy.radius_sm}px; "
                f"padding:16px 10px;",
            )
            self._scenario_layout.addWidget(empty)
        else:
            for name, steps in saved.items():
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(6)

                btn = navy_button(
                    f"{name}   {len(steps)}스텝", kind="ghost", height=34, icon_name="fa5s.play"
                )
                # 실행 목록이라 항목이 여러 개 쌓입니다. 가운데 정렬보다 왼쪽 정렬이 읽기 좋습니다.
                btn.setStyleSheet(
                    btn.styleSheet() + "QPushButton { text-align:left; padding-left:12px; }"
                )
                btn.clicked.connect(lambda checked=False, n=name: self._run_scenario(n))
                row_layout.addWidget(btn, 1)

                result_lbl = QLabel("")
                result_lbl.setFont(kfont(10, True))
                result_lbl.setFixedWidth(40)
                result_lbl.setAlignment(Qt.AlignCenter)
                row_layout.addWidget(result_lbl)
                self._scenario_result_labels[name] = result_lbl

                self._scenario_layout.addWidget(row)

        self._scenario_layout.addStretch(1)

    def showEvent(self, event):
        super().showEvent(event)
        # 다른 창에서 시나리오를 추가/삭제하고 돌아왔을 때도 목록이 최신이도록.
        self.refresh_scenarios()

    # ---------- 실행 ----------
    def _run_scenario(self, name):
        if self._running:
            QMessageBox.information(self, "실행 중", "이미 실행 중인 시나리오가 있습니다.")
            return
        if not self.panel.current_uuid:
            QMessageBox.warning(self, "단말 미연결", "먼저 왼쪽 대시보드에서 단말을 연결해주세요.")
            return

        steps = scenario_store.list_scenarios(self._project).get(name)
        if not steps:
            QMessageBox.warning(self, "스텝 없음", f"'{name}'에 실행할 스텝이 없습니다.")
            return

        result_lbl = self._scenario_result_labels.get(name)
        if result_lbl:
            result_lbl.setText("...")
            result_lbl.setStyleSheet(f"color:{Navy.text_muted};")

        self._running = True
        channel_roles = dict(self.panel.channel_roles)
        threading.Thread(
            target=self._run_worker,
            args=(self.panel.current_uuid, self._project, [dict(s) for s in steps], name, channel_roles),
            daemon=True,
        ).start()

    def _run_worker(self, uuid, project, steps, name, channel_roles):
        try:
            success = scenario_runner.run_scenario(
                uuid, project, steps, on_log=self._run_signals.log.emit, title=name,
                channel_roles=channel_roles,
            )
            self._run_signals.result.emit(name, success)
        finally:
            self._running = False

    def _on_run_result(self, name, success):
        # 시나리오 목록이 그 사이에 새로고침됐으면(스텝 편집 등) 이 이름의 라벨이
        # 더 이상 없을 수 있어 조용히 무시합니다.
        result_lbl = self._scenario_result_labels.get(name)
        if result_lbl is None:
            return
        if success:
            result_lbl.setText("PASS")
            result_lbl.setStyleSheet(f"color:{Navy.accent};")
        else:
            result_lbl.setText("FAIL")
            result_lbl.setStyleSheet(f"color:{Navy.danger};")

    def _on_run_log(self, text):
        # 실행 로그는 왼쪽 대시보드의 로그창에 그대로 흘려보냅니다.
        self.panel.safe_log_insert(text, is_error="❌" in text or "⏹" in text)
