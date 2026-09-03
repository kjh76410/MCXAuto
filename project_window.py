"""프로젝트 창.

런처(데스크톱 아이콘)의 프로젝트 박스를 누르면 뜨는 창입니다. 사이드바가 있는
'관리 창'(ui_logic.App: 프로젝트 관리/객체 관리/시나리오 작성/시나리오)과 달리,
여기는 실제로 테스트를 돌릴 때 보는 화면만 모아둡니다.

단말 A 대시보드(미러링/리스트/로그) 하나로 이루어져 있고, 그 안의 Network &
System Logs 카드(tab_view)에 "시나리오" 탭을 맨 앞에 끼워 넣어 이 프로젝트의
저장된 시나리오 목록(시나리오 작성 화면에서 나눈 폴더별로 묶어서 + 주채널/부채널
지정)을 보여줍니다("반복시나리오" 탭엔
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

from PySide6.QtCore import Qt, QObject, QPointF, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import project_config_store
import scenario_runner
import scenario_store

# 공통통화그룹은 재난망 프로젝트에만 있는 개념이라, 채널 지정 드롭다운에도
# 이 두 프로젝트일 때만 보여줍니다.
COMMON_CALL_GROUP_PROJECTS = ("재난망", "재난망_LM75")

# 재난망/재난망_LM75에만 있는 채널 역할들(위 COMMON_CALL_GROUP_PROJECTS 프로젝트일
# 때만 채널 지정 드롭다운에 행을 보여줍니다).
DISASTER_ONLY_CHANNEL_ROLES = ("일반그룹", "일반그룹 SRTP", "공통통화그룹", "공통통화그룹 SRTP")

# 해외 프로젝트(project_config.json의 region == "해외")에만 있는 채널 역할들.
OVERSEAS_ONLY_CHANNEL_ROLES = ("Chat group", "PreArranged group", "Private")

# 항상 보이는 역할(주채널/부채널) + 조건부 역할 순서. scenario_runner.CHANNEL_ROLES와
# 같은 집합이어야 하며(안 그러면 시나리오의 "찾기" 동작이 지정할 곳 없는 역할을
# 참조하게 됩니다), 아래 assert로 어긋나면 바로 알 수 있게 해둡니다.
ALL_CHANNEL_ROLES = ("주채널", "부채널", *DISASTER_ONLY_CHANNEL_ROLES, *OVERSEAS_ONLY_CHANNEL_ROLES)
assert set(ALL_CHANNEL_ROLES) == set(scenario_runner.CHANNEL_ROLES)
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


class _TreeConnector(QWidget):
    """폴더 아래 딸린 시나리오 줄임을 보여주는 가는 세로선 하나(ㅣ)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(16)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(Navy.border_strong))
        pen.setWidthF(1.6)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        cx = self.width() / 2
        painter.drawLine(QPointF(cx, 2), QPointF(cx, self.height() - 2))


class _ScenarioCardRow(QFrame):
    """[이름 + 스텝 수] [PASS/FAIL] 시나리오 카드 한 줄. 폭 전체가 클릭 영역이라
    이름 글자뿐 아니라 카드 어디를 눌러도 실행됩니다."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("scenarioCardRow")
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            f"QFrame#scenarioCardRow {{ background-color:{Navy.surface}; "
            f"border:1px solid {Navy.border}; border-radius:{Navy.radius_sm}px; }}"
            f"QFrame#scenarioCardRow:hover {{ background-color:{Navy.accent_soft}; "
            f"border-color:{Navy.accent}; }}"
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            event.accept()
            self.clicked.emit()
            return
        super().mousePressEvent(event)


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
        # '전체 진행'으로 이어 실행할 시나리오 이름 대기열(폴더 전체 진행용).
        self._run_queue = []
        self._scenario_result_labels = {}
        # 시나리오 목록에서 접어둔 폴더 이름들(시나리오 작성 화면과 같은 방식).
        self._collapsed_scenario_folders = set()

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

        layout.addWidget(self._build_channel_section())

        # 시나리오가 많아지면 카드가 창 밖으로 계속 늘어나던 걸 막기 위해,
        # 목록만 스크롤 영역에 담습니다(위의 헤더/채널 지정은 스크롤과 무관하게
        # 항상 보입니다). 프로젝트 이름은 왼쪽 대시보드의 기기 연결 버튼 위에
        # 이미 표시되므로 여기서 다시 보여주지 않습니다.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        list_container = styled(QWidget(), "background: transparent;")
        self._scenario_layout = QVBoxLayout(list_container)
        self._scenario_layout.setContentsMargins(0, 0, 0, 0)
        self._scenario_layout.setSpacing(6)
        scroll.setWidget(list_container)
        layout.addWidget(scroll, 1)

        return card

    # ---------- 주채널/부채널(+ 재난망 전용 공통통화그룹/SRTP 채널들) 지정 ----------
    def _build_channel_section(self):
        """시나리오에서 채널 역할(주채널/부채널/공통통화그룹/일반그룹 SRTP/공통통화그룹
        SRTP)로 저장된 객체가, 캡처 당시 채널명이 아니라 지금 여기서 고른 실제
        채널명으로 동작하게 하는 드롭다운. 채널 목록은 단말 연결 시 그룹 목록을
        읽어야 알 수 있어서(단말 연결 전엔 비어 있음), 패널의 groups_ready
        시그널로 매번 다시 채웁니다. DISASTER_ONLY_CHANNEL_ROLES는 재난망/
        재난망_LM75에만 있는 개념이라, 그 두 프로젝트일 때만 행을 보여줍니다
        (set_project에서 _update_channel_row_visibility로 토글).

        제목 줄("채널 지정")을 누르면 드롭다운 묶음 전체를 접었다 펼 수 있습니다."""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)

        # 역할이 많은 프로젝트(재난망 6줄, 해외 5줄)에서는 이 영역만으로 카드가 꽉 차서
        # 정작 실행할 시나리오 목록이 밀립니다. 한 번 골라두면 계속 볼 일이 없는
        # 설정이라, 제목 줄을 눌러 접었다 펼 수 있게 했습니다.
        self._channel_toggle = navy_button("", kind="quiet", height=24)
        self._channel_toggle.setFont(kfont(9, True))
        self._channel_toggle.setStyleSheet(
            self._channel_toggle.styleSheet()
            + f"QPushButton {{ text-align:left; padding-left:2px; color:{Navy.text_muted}; }}"
        )
        self._channel_toggle.clicked.connect(self._toggle_channel_section)
        layout.addWidget(self._channel_toggle)

        rows_holder = QWidget()
        rows_layout = QVBoxLayout(rows_holder)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(4)
        self._channel_rows_holder = rows_holder
        layout.addWidget(rows_holder)

        self._channel_combos = {}
        self._channel_rows = {}
        for role in ALL_CHANNEL_ROLES:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            lbl = QLabel(role)
            lbl.setFont(kfont(9))
            # "공통통화그룹 SRTP"/"PreArranged group"처럼 길어진 역할 이름도 안 잘리도록
            # 넉넉히 잡습니다(원래 60px은 "주채널"/"부채널" 두 글자 기준이었습니다).
            lbl.setFixedWidth(118)
            lbl.setStyleSheet(f"color:{Navy.text};")
            row_layout.addWidget(lbl)
            combo = self._make_channel_combo()
            row_layout.addWidget(combo, 1)
            rows_layout.addWidget(row)
            self._channel_combos[role] = combo
            self._channel_rows[role] = row

        self._channel_section_open = True
        self._update_channel_toggle()
        return section

    def _toggle_channel_section(self):
        self._channel_section_open = not self._channel_section_open
        self._update_channel_toggle()

    def _update_channel_toggle(self):
        arrow = "▼" if self._channel_section_open else "▶"
        self._channel_toggle.setText(f"{arrow}  채널 지정")
        self._channel_rows_holder.setVisible(self._channel_section_open)

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
        """지금 프로젝트에 해당하는 채널 역할 행만 남깁니다.
        재난망 전용(DISASTER_ONLY_CHANNEL_ROLES)은 프로젝트 이름으로, 해외 전용
        (OVERSEAS_ONLY_CHANNEL_ROLES)은 project_config.json의 region으로 판단합니다."""
        region = project_config_store.get_project_region(self._project) if self._project else None
        visibility = {
            DISASTER_ONLY_CHANNEL_ROLES: self._project in COMMON_CALL_GROUP_PROJECTS,
            OVERSEAS_ONLY_CHANNEL_ROLES: region == "해외",
        }
        for roles, visible in visibility.items():
            for role in roles:
                self._channel_rows[role].setVisible(visible)
                if not visible:
                    # 숨긴 행은 콤보까지 "(미지정)"으로 되돌립니다. 값을 남겨두면
                    # 다음 groups_ready 때 _refresh_channel_combos가 콤보 값을 보고
                    # channel_roles를 다시 채워, 안 보이는 역할이 되살아납니다.
                    combo = self._channel_combos[role]
                    combo.blockSignals(True)
                    combo.setCurrentIndex(0)
                    combo.blockSignals(False)
                    self.panel.channel_roles[role] = None

    # ---------- 프로젝트 전환 ----------
    def set_project(self, project_name):
        self._project = project_name
        self.setWindowTitle(f"{project_name} — MCX QA")
        self._update_channel_row_visibility()
        self.refresh_scenarios()

    def refresh_scenarios(self):
        # self._scenario_layout은 이제 스크롤 영역 안 목록 전용 레이아웃이라
        # (헤더/프로젝트 이름/안내문구/채널 지정은 그 밖에 고정되어 있음) 통째로 비웁니다.
        clear_layout(self._scenario_layout, keep=0)
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
            # 시나리오 작성 화면에서 나눠둔 폴더 그대로 묶어서 보여줍니다. 폴더 줄을
            # 누르면 그 폴더만 접히고(여기서는 실행만 하므로 폴더 이름 수정/삭제는
            # 넣지 않습니다), 폴더가 기본 폴더 하나뿐이면 줄 자체를 생략합니다.
            by_folder = {folder: [] for folder in scenario_store.list_folders(self._project)}
            for name, steps in saved.items():
                folder = scenario_store.scenario_folder(self._project, name)
                by_folder.setdefault(folder, []).append((name, steps))

            single_folder = len(by_folder) <= 1
            for folder, items in by_folder.items():
                if not single_folder:
                    self._scenario_layout.addWidget(self._make_folder_header(folder, items))
                    if folder in self._collapsed_scenario_folders:
                        continue
                for name, steps in items:
                    self._scenario_layout.addWidget(
                        self._make_scenario_row(name, steps, indent=not single_folder)
                    )

        self._scenario_layout.addStretch(1)

    def _make_folder_header(self, folder, items):
        """시나리오 목록 안의 폴더 구분 줄. 누르면 그 폴더를 접었다 폅니다. 오른쪽
        '전체 진행' 버튼을 누르면 이 폴더 안의 시나리오를 순서대로 이어서 실행합니다."""
        collapsed = folder in self._collapsed_scenario_folders

        holder = QWidget()
        row = QHBoxLayout(holder)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        # 예전엔 펼침/접힘을 ▶/▼ 화살표 글자로 표시했지만, 다른 화면과 맞춰
        # 폴더 아이콘으로 바꿨습니다(접힘: 닫힌 폴더, 펼침: 열린 폴더).
        btn = navy_button(
            f"{folder}  ({len(items)})", kind="quiet", height=26,
            icon_name="fa5s.folder" if collapsed else "fa5s.folder-open", icon_size=13,
        )
        # 다른 화면의 폴더 줄과 같은 이유로 옅은 회색 대신 본문 색을 씁니다.
        btn.setFont(kfont(11, True))
        btn.setStyleSheet(
            btn.styleSheet()
            + f"QPushButton {{ text-align:left; padding-left:2px; color:{Navy.text}; }}"
        )
        btn.clicked.connect(lambda checked=False, f=folder: self._toggle_scenario_folder(f))
        row.addWidget(btn, 1)

        names = [name for name, _steps in items]
        btn_run_all = navy_button(
            "전체 진행", kind="ghost", height=26, icon_name="fa5s.play", icon_size=11
        )
        btn_run_all.setFont(kfont(10, True))
        btn_run_all.setToolTip(f"'{folder}' 폴더의 시나리오 {len(names)}개를 순서대로 이어서 실행")
        btn_run_all.clicked.connect(lambda checked=False, n=names: self._run_folder(n))
        row.addWidget(btn_run_all)

        return holder

    def _toggle_scenario_folder(self, folder):
        if folder in self._collapsed_scenario_folders:
            self._collapsed_scenario_folders.discard(folder)
        else:
            self._collapsed_scenario_folders.add(folder)
        # 누른 버튼 자신이 지워지는 자리라, 지금 처리 중인 클릭이 끝난 뒤로 미룹니다.
        QTimer.singleShot(0, self.refresh_scenarios)

    def _make_scenario_row(self, name, steps, indent=False):
        """[세로선(폴더 하위일 때만)] + [이름 + 스텝 수 + PASS/FAIL이 담긴 카드] 한 줄.
        카드는 폭 전체가 클릭 영역이라 어디를 눌러도 실행됩니다(삼각형 재생
        아이콘은 카드 자체가 버튼 역할을 해서 더 필요 없어 뺐습니다)."""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(4)

        # 폴더 줄 바로 아래 속한 시나리오라는 걸 세로선으로 보여줍니다. 폴더 줄이
        # 아예 없는 경우(기본 폴더 하나뿐)엔 표시하지 않습니다.
        if indent:
            row_layout.addWidget(_TreeConnector())
        else:
            spacer = QWidget()
            spacer.setFixedWidth(16)
            row_layout.addWidget(spacer)

        card = _ScenarioCardRow()
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(14, 4, 14, 4)
        card_layout.setSpacing(8)

        name_lbl = QLabel(name)
        # 목록에서 제일 많이 읽는 글자라 한 단계 크게 씁니다.
        name_lbl.setFont(kfont(12, True))
        name_lbl.setStyleSheet(f"color:{Navy.text}; background:transparent;")
        card_layout.addWidget(name_lbl)

        # 스텝 수는 이름과 헷갈리지 않게 진한 회색으로 따로 둡니다.
        steps_lbl = QLabel(f"{len(steps)}스텝")
        steps_lbl.setFont(kfont(10))
        steps_lbl.setStyleSheet("color:#333333; background:transparent;")
        card_layout.addWidget(steps_lbl)
        card_layout.addStretch(1)

        card.clicked.connect(lambda n=name: self._run_scenario(n))
        row_layout.addWidget(card, 1)

        # 결과(PASS/FAIL)는 카드 안이 아니라 카드 옆에 따로 둡니다. 결과가 없을
        # 때도 자리는 그대로 남겨둬서 결과가 뜨는 순간 옆 카드들과 자리가 안
        # 밀리게 합니다.
        result_lbl = QLabel("")
        result_lbl.setFont(kfont(10, True))
        result_lbl.setFixedWidth(40)
        result_lbl.setAlignment(Qt.AlignCenter)
        row_layout.addWidget(result_lbl)
        self._scenario_result_labels[name] = result_lbl

        return row

    def showEvent(self, event):
        super().showEvent(event)
        # 다른 창에서 시나리오를 추가/삭제하고 돌아왔을 때도 목록이 최신이도록.
        self.refresh_scenarios()

    # ---------- 실행 ----------
    def _run_scenario(self, name):
        if self._running or self._run_queue:
            QMessageBox.information(self, "실행 중", "이미 실행 중인 시나리오가 있습니다.")
            return
        if not self.panel.current_uuid:
            QMessageBox.warning(self, "단말 미연결", "먼저 왼쪽 대시보드에서 단말을 연결해주세요.")
            return

        steps = scenario_store.list_scenarios(self._project).get(name)
        if not steps:
            QMessageBox.warning(self, "스텝 없음", f"'{name}'에 실행할 스텝이 없습니다.")
            return

        self._start_scenario_run(name, steps)

    def _run_folder(self, names):
        """'전체 진행' 버튼: 폴더 안 시나리오를 이름 순서 그대로 하나씩 이어서
        실행합니다(동시 실행은 안 되므로 한 개가 끝나야 다음이 시작됩니다)."""
        if self._running or self._run_queue:
            QMessageBox.information(self, "실행 중", "이미 실행 중인 시나리오가 있습니다.")
            return
        if not self.panel.current_uuid:
            QMessageBox.warning(self, "단말 미연결", "먼저 왼쪽 대시보드에서 단말을 연결해주세요.")
            return
        if not names:
            return

        self._run_queue = list(names)
        self._run_next_in_queue()

    def _run_next_in_queue(self):
        """대기열에서 다음 시나리오를 꺼내 실행합니다. 스텝이 없어 실행할 수 없는
        시나리오는 (전체 진행 중에 대화상자로 끊기지 않도록) 건너뜁니다."""
        while self._run_queue:
            name = self._run_queue.pop(0)
            steps = scenario_store.list_scenarios(self._project).get(name)
            if not steps:
                continue
            self._start_scenario_run(name, steps)
            return

    def _start_scenario_run(self, name, steps):
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
        # 더 이상 없을 수 있어 조용히 무시합니다(대기열은 계속 이어갑니다).
        result_lbl = self._scenario_result_labels.get(name)
        if result_lbl is not None:
            if success:
                result_lbl.setText("PASS")
                result_lbl.setStyleSheet(f"color:{Navy.success}; font-weight:bold;")
            else:
                result_lbl.setText("FAIL")
                result_lbl.setStyleSheet(f"color:{Navy.danger}; font-weight:bold;")
        if self._run_queue:
            self._run_next_in_queue()

    def _on_run_log(self, text):
        # 실행 로그는 왼쪽 대시보드의 로그창에 그대로 흘려보냅니다.
        self.panel.safe_log_insert(text, is_error="❌" in text or "⏹" in text)
