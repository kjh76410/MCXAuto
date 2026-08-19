"""프로젝트 창.

런처(데스크톱 아이콘)의 프로젝트 박스를 누르면 뜨는 창입니다. 사이드바가 있는
'관리 창'(ui_logic.App: 프로젝트 관리/객체 관리/시나리오 작성/시나리오)과 달리,
여기는 실제로 테스트를 돌릴 때 보는 화면만 모아둡니다.

  [ 왼쪽 : 단말 A 대시보드(미러링/리스트/로그) ][ 오른쪽 : 이 프로젝트의 시나리오 목록 ]

대시보드 위젯은 DevicePanel이 만들어 둔 조각(top_block / left_column_widget /
right_column_widget)을 그대로 가져와 배치합니다. DevicePanel 인스턴스는 관리 창과
공유하는 하나뿐이라, 이 창이 살아있는 동안 대시보드는 여기에만 보입니다(관리 창에는
더 이상 대시보드 탭이 없습니다).

시나리오 목록에서 항목을 누르면 그 자리에서 바로 실행되고, 진행 로그는 왼쪽
대시보드의 로그창에 그대로 찍힙니다.
"""

import threading

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import PushButton
import qtawesome as qta

import scenario_runner
import scenario_store
from ui_common import Palette, add_shadow, card_css, clear_layout, kfont, styled


class _RunSignals(QObject):
    log = Signal(str)


class ProjectWindow(QWidget):
    """프로젝트 하나를 기준으로 '대시보드 + 시나리오 목록'을 함께 보여주는 창.
    창은 하나만 만들어 두고 set_project()로 프로젝트만 갈아끼우며 재사용합니다."""

    SCENARIO_PANEL_WIDTH = 320

    def __init__(self, panel, project_name=None, parent=None):
        super().__init__(parent)
        self.panel = panel
        self._project = None
        self._run_signals = _RunSignals()
        self._run_signals.log.connect(self._on_run_log)
        self._running = False

        self.setWindowTitle("MCX QA")
        self.setStyleSheet(f"QWidget {{ background-color:{Palette.bg}; color:{Palette.text_main}; }}")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(10)
        outer.addWidget(self._build_dashboard(), 1)
        outer.addWidget(self._build_scenario_panel(), 0)

        if project_name:
            self.set_project(project_name)

    # ---------- 왼쪽: 단말 A 대시보드 ----------
    def _build_dashboard(self):
        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.addWidget(self.panel.top_block, 0, 0, 1, 2)
        grid.addWidget(self.panel.left_column_widget, 1, 0)
        grid.addWidget(self.panel.right_column_widget, 1, 1)
        grid.setRowStretch(1, 2)
        return holder

    # ---------- 오른쪽: 시나리오 목록 ----------
    def _build_scenario_panel(self):
        card = styled(QFrame(), card_css())
        card.setFixedWidth(self.SCENARIO_PANEL_WIDTH)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 14, 12, 14)
        layout.setSpacing(6)

        title = QLabel("시나리오")
        title.setFont(kfont(12, True))
        title.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(title)

        self._project_label = QLabel("-")
        self._project_label.setFont(kfont(13, True))
        self._project_label.setStyleSheet(f"color:{Palette.text_main};")
        layout.addWidget(self._project_label)

        hint = QLabel("항목을 누르면 연결된 단말에서 바로 실행됩니다.")
        hint.setFont(kfont(9))
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(hint)

        self._scenario_layout = layout
        layout.addStretch(1)
        return add_shadow(card)

    # ---------- 프로젝트 전환 ----------
    def set_project(self, project_name):
        self._project = project_name
        self.setWindowTitle(f"{project_name} — MCX QA")
        self._project_label.setText(project_name)
        self.refresh_scenarios()

    def refresh_scenarios(self):
        # keep=3: 타이틀 / 프로젝트 이름 / 안내문구
        clear_layout(self._scenario_layout, keep=3)

        saved = scenario_store.list_scenarios(self._project) if self._project else {}
        if not saved:
            empty = QLabel("저장된 시나리오가 없습니다.\n'시나리오 작성'에서 만들어 주세요.")
            empty.setFont(kfont(10))
            empty.setWordWrap(True)
            empty.setStyleSheet(f"color:{Palette.text_sub};")
            self._scenario_layout.addWidget(empty)
        else:
            for name, steps in saved.items():
                btn = PushButton(qta.icon("fa5s.play", color=Palette.text_main), f"{name}  ({len(steps)}스텝)")
                btn.setFont(kfont(11, True))
                btn.setFixedHeight(32)
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked=False, n=name: self._run_scenario(n))
                self._scenario_layout.addWidget(btn)

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

        self._running = True
        threading.Thread(
            target=self._run_worker,
            args=(self.panel.current_uuid, self._project, [dict(s) for s in steps], name),
            daemon=True,
        ).start()

    def _run_worker(self, uuid, project, steps, name):
        try:
            scenario_runner.run_scenario(
                uuid, project, steps, on_log=self._run_signals.log.emit, title=name
            )
        finally:
            self._running = False

    def _on_run_log(self, text):
        # 실행 로그는 왼쪽 대시보드의 로그창에 그대로 흘려보냅니다.
        self.panel.safe_log_insert(text, is_error="❌" in text or "⏹" in text)
