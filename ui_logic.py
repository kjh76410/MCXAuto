import sys
import threading

from PySide6.QtWidgets import QApplication, QGridLayout, QWidget
from qfluentwidgets import FluentIcon, FluentWindow, Theme, setTheme, setThemeColor, setFontFamilies

import adb_logic
from device_panel import DevicePanel, ResultsPanel
from object_manager_page import ObjectManagerPage
from project_manager_page import ProjectManagerPage
from scenario_builder_page import ScenarioBuilderPage
from scenario_page import ScenarioLibraryPage
from ui_common import Palette, load_custom_font

# 하위 호환: 예전에 ui_logic에서 바로 이 이름들을 가져다 쓰던 코드(또는 향후 참조)를 위해
# 그대로 재노출합니다. 실제 정의는 ui_common.py에 있습니다.
from ui_common import (  # noqa: F401
    styled,
    add_shadow,
    card_css,
    btn_css,
    clear_layout,
    Signals,
    QtLogConsole,
    ClickableLabel,
    PulseCanvas,
)


class App(FluentWindow):
    """두 대의 단말을 동시에 다루는 메인 윈도우.
    실제 미러링/그룹·유저 리스트/SIP Flow/로그 등 기기별 상태와 위젯은
    모두 DevicePanel(device_panel.py)로 옮겨졌고, 이 클래스는 두 DevicePanel을
    나란히 배치하고 기기 탐색(adb devices 스캔)만 담당하는 얇은 셸입니다.

    Test Results 표(ResultsPanel)는 결국 하나의 TC 목록을 두 단말이 같이 채우는 것이라
    패널마다 따로 두지 않고 여기서 하나만 만들어서 두 DevicePanel에 공유시킵니다.
    다만 홈 화면에는 더 이상 표시하지 않고(자동 PASS/FAIL 판정 로직만 계속 쓰도록
    인스턴스만 유지), 화면 배치는 이 클래스가 QGridLayout으로 직접 맡습니다: 각
    DevicePanel은 더 이상 자기 완결적인 카드 위젯이 아니라 조각(상단 헤더/배너,
    미러링+리스트 컬럼, 로그카드 컬럼)만 넘겨주고, 여기서 두 로그카드를 나란히 놓습니다."""

    def __init__(self):
        setTheme(Theme.LIGHT)
        setThemeColor(Palette.accent)
        super().__init__()
        self.setCustomBackgroundColor(Palette.bg, "#202020")

        load_custom_font()
        # kfont()로 직접 폰트를 지정하는 위젯 밖에도, qfluentwidgets가 자체적으로
        # 그리는 네비게이션/메뉴/테이블 헤더 등은 이 라이브러리 전역 폰트 목록
        # (기본값 Segoe UI/Microsoft YaHei/PingFang SC)을 따로 써서 Pretendard가
        # 안 먹었었습니다. 여기서도 Pretendard를 최우선으로 쓰도록 맞춰줍니다.
        setFontFamilies(["Pretendard", "Microsoft YaHei", "Segoe UI"])
        self.setWindowTitle("MCX QA Automation Dashboard")
        self.resize(1960, 950)
        self.setStyleSheet(self._global_qss())

        root = QWidget()
        root.setObjectName("dashboardInterface")
        grid = QGridLayout(root)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.results_panel = ResultsPanel()
        self.panel_a = DevicePanel("A", results_panel=self.results_panel)
        self.panel_b = DevicePanel("B", results_panel=self.results_panel)
        self.device_mode = "1"
        self._grid = grid

        # 대시보드는 단말 1대만 보여줍니다. panel_b는 객체 관리/시나리오 작성 화면에서
        # 여전히 쓰이므로 인스턴스는 유지하되, 여기 그리드에는 올리지 않습니다.
        grid.addWidget(self.panel_a.top_block, 0, 0, 1, 2)
        grid.addWidget(self.panel_a.left_column_widget, 1, 0)
        grid.addWidget(self.panel_a.right_column_widget, 1, 1)

        grid.setRowStretch(1, 2)

        self.panel_a.btn_connect.clicked.connect(self.check_devices)

        # 사이드바는 기본 Fluent 방식대로: 아이콘은 평소에도 항상 보이고, ☰를 누르면
        # 아이콘 옆에 글자 라벨이 펼쳐집니다.
        self.navigationInterface.setExpandWidth(180)
        self.addSubInterface(root, FluentIcon.HOME, "대시보드")

        self.project_manager_page = ProjectManagerPage()
        self.addSubInterface(self.project_manager_page, FluentIcon.FOLDER_ADD, "프로젝트 관리")

        self.object_manager_page = ObjectManagerPage(self.panel_a, self.panel_b)
        self.addSubInterface(self.object_manager_page, FluentIcon.TAG, "객체 관리")

        self.scenario_builder_page = ScenarioBuilderPage(self.panel_a, self.panel_b)
        self.addSubInterface(self.scenario_builder_page, FluentIcon.EDIT, "시나리오 작성")

        self.scenario_page = ScenarioLibraryPage()
        self.addSubInterface(self.scenario_page, FluentIcon.LIBRARY, "시나리오")
        self.scenario_page.on_edit_builder_scenario = self._edit_scenario_in_builder

    def _edit_scenario_in_builder(self, project_name, scenario_name):
        """'시나리오' 화면에서 '시나리오 작성에서 편집' 버튼을 누르면 호출됩니다.
        '시나리오 작성' 화면으로 전환하고 해당 시나리오를 편집기에 바로 불러옵니다."""
        self.scenario_builder_page.load_scenario_for_edit(project_name, scenario_name)
        self.switchTo(self.scenario_builder_page)

    # ==========================================
    # 🎨 전역 스타일 (스크롤바 / 콤보박스 / 다이얼로그 등 기본 위젯 다듬기)
    # ==========================================
    def _global_qss(self):
        return f"""
            QMainWindow {{ background-color:{Palette.bg}; }}
            QToolTip {{ background-color:#1C1C1E; color:white; border:none; padding:4px 8px; border-radius:3px; }}
            QScrollBar:vertical {{ background:transparent; width:10px; margin:0; }}
            QScrollBar::handle:vertical {{ background:{Palette.neutral_hover}; border-radius:3px; min-height:24px; }}
            QScrollBar::handle:vertical:hover {{ background:{Palette.accent}; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:none; }}
            QScrollBar:horizontal {{ background:transparent; height:10px; margin:0; }}
            QScrollBar::handle:horizontal {{ background:{Palette.neutral_hover}; border-radius:3px; min-width:24px; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}
            QComboBox {{
                background-color:{Palette.bg}; border:1px solid {Palette.border}; border-radius:4px;
                padding:4px 10px; color:{Palette.text_main};
            }}
            QComboBox:hover {{ border-color:{Palette.accent}; }}
            QComboBox::drop-down {{ border:none; width:22px; }}
            QComboBox QAbstractItemView {{
                background-color:white; border:1px solid {Palette.border}; border-radius:3px;
                selection-background-color:{Palette.neutral_hover}; selection-color:{Palette.text_main}; outline:none;
            }}
            QDialog {{ background-color:{Palette.panel}; }}
            QLineEdit:focus {{ border:1px solid {Palette.accent}; }}
        """

    def closeEvent(self, event):
        """프로그램 종료 시 adb 서버를 내려서, 다음 실행 때 깨끗한 서버로 새로 시작하게 합니다.
        (SDK adb와 scrcpy 번들 adb 버전이 달라 서버 소유권 다툼으로 기기 인식이 멈추는 문제 방지)"""
        adb_logic.kill_adb_server()
        super().closeEvent(event)

    # ==========================================
    # 🔌 기기 연결 / 상태 조회 (두 대 동시 스캔)
    # ==========================================
    def check_devices(self):
        """adb 조회가 여러 번(모델/버전/HW/잠금해제 등) 필요해서 메인 스레드에서 돌리면
        그동안 Qt 이벤트 루프가 막혀 창 전체가 멈춘 것처럼 보입니다. 조회는 백그라운드
        스레드에서 하고, 결과만 패널의 signals.device_ready로 돌려받습니다."""
        self.panel_a.btn_connect.setEnabled(False)
        threading.Thread(target=self._check_devices_worker, daemon=True).start()

    def _check_devices_worker(self):
        devices = adb_logic.get_devices()
        if len(devices) > 1:
            print(f"⚠️ {len(devices)}대 연결됨 - 처음 1대만 사용합니다: {devices[:1]}")

        info_a = self._query_device_info(devices[0]) if len(devices) >= 1 else None
        self.panel_a.signals.device_ready.emit(info_a)

    def _query_device_info(self, uuid):
        model = adb_logic.get_model_name(uuid)
        android_version = adb_logic.get_os_version(uuid)
        try:
            os_build = adb_logic.get_build_image_version(uuid)
        except AttributeError:
            os_build = "조회 불가"
        version_name = adb_logic.get_everytalk_version(uuid)
        hw_version = getattr(adb_logic, "get_hw_version", lambda x: "조회 불가")(uuid)
        adb_logic.unlock_screen(uuid)

        return {
            "uuid": uuid,
            "model": model,
            "android_version": android_version,
            "os_build": os_build,
            "version_name": version_name,
            "hw_version": hw_version,
        }


def main():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
