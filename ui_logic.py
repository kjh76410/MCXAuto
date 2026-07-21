import sys
import threading

from PySide6.QtWidgets import QApplication, QGridLayout, QMainWindow, QWidget

import adb_logic
from device_panel import DevicePanel, ResultsPanel
from ui_common import Palette, load_custom_font

# 하위 호환: 예전에 ui_logic에서 바로 이 이름들을 가져다 쓰던 코드(또는 향후 참조)를 위해
# 그대로 재노출합니다. 실제 정의는 ui_common.py에 있습니다.
from ui_common import (  # noqa: F401
    kfont,
    styled,
    add_shadow,
    card_css,
    btn_css,
    clear_layout,
    Signals,
    QtLogConsole,
    ClickableLabel,
    SegmentedButton,
    PulseCanvas,
)


class App(QMainWindow):
    """두 대의 단말을 동시에 다루는 메인 윈도우.
    실제 미러링/그룹·유저 리스트/SIP Flow/로그 등 기기별 상태와 위젯은
    모두 DevicePanel(device_panel.py)로 옮겨졌고, 이 클래스는 두 DevicePanel을
    나란히 배치하고 기기 탐색(adb devices 스캔)만 담당하는 얇은 셸입니다.

    Test Results 표(ResultsPanel)는 결국 하나의 TC 목록을 두 단말이 같이 채우는 것이라
    패널마다 따로 두지 않고 여기서 하나만 만들어서 두 DevicePanel에 공유시킵니다.
    화면 배치도 이 클래스가 QGridLayout으로 직접 맡습니다: 각 DevicePanel은 더 이상
    자기 완결적인 카드 위젯이 아니라 조각(상단 헤더/배너, 미러링+리스트 컬럼, 로그카드
    컬럼)만 넘겨주고, 여기서 두 로그카드를 나란히 놓은 뒤 그 아래에 결과표를 두 로그카드
    폭만큼만 걸치는 하나의 병합된 띠로 붙입니다(미러링 화면 아래까지는 내려오지 않음)."""

    def __init__(self):
        super().__init__()
        load_custom_font()
        self.setWindowTitle("MCX QA Automation Dashboard")
        self.resize(1960, 950)
        self.setStyleSheet(self._global_qss())

        root = QWidget()
        self.setCentralWidget(root)
        grid = QGridLayout(root)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        self.results_panel = ResultsPanel()
        self.panel_a = DevicePanel("A", results_panel=self.results_panel)
        self.panel_b = DevicePanel("B", results_panel=self.results_panel)

        # 4열 그리드: [미러+리스트 A] [로그카드 A] [로그카드 B] [미러+리스트 B].
        # 결과표는 두 로그카드 칸(col 1~2)에만 걸쳐서 그 아래 한 줄로 병합해 붙이고,
        # 미러링 컬럼(col 0, 3)은 로그카드+결과표 두 줄(row 1~2) 높이를 그대로 이어받습니다.
        grid.addWidget(self.panel_a.top_block, 0, 0, 1, 2)
        grid.addWidget(self.panel_b.top_block, 0, 2, 1, 2)
        grid.addWidget(self.panel_a.left_column_widget, 1, 0, 2, 1)
        grid.addWidget(self.panel_a.right_column_widget, 1, 1)
        grid.addWidget(self.panel_b.right_column_widget, 1, 2)
        grid.addWidget(self.panel_b.left_column_widget, 1, 3, 2, 1)
        grid.addWidget(self.results_panel, 2, 1, 1, 2)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        grid.setRowStretch(1, 2)
        grid.setRowStretch(2, 1)

        # 두 패널의 연결 버튼 모두 같은 스캔을 호출합니다 - adb devices 목록의
        # 1번째 기기는 항상 패널 A, 2번째 기기는 항상 패널 B에 배정됩니다.
        self.panel_a.btn_connect.clicked.connect(self.check_devices)
        self.panel_b.btn_connect.clicked.connect(self.check_devices)

    # ==========================================
    # 🎨 전역 스타일 (스크롤바 / 콤보박스 / 다이얼로그 등 기본 위젯 다듬기)
    # ==========================================
    def _global_qss(self):
        return f"""
            QMainWindow {{ background-color:{Palette.bg}; }}
            QToolTip {{ background-color:#1C1C1E; color:white; border:none; padding:4px 8px; border-radius:3px; }}
            QScrollBar:vertical {{ background:transparent; width:10px; margin:0; }}
            QScrollBar::handle:vertical {{ background:#C7C7CC; border-radius:3px; min-height:24px; }}
            QScrollBar::handle:vertical:hover {{ background:#AEAEB2; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:none; }}
            QScrollBar:horizontal {{ background:transparent; height:10px; margin:0; }}
            QScrollBar::handle:horizontal {{ background:#C7C7CC; border-radius:3px; min-width:24px; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}
            QComboBox {{
                background-color:{Palette.bg}; border:1px solid {Palette.border}; border-radius:4px;
                padding:4px 10px; color:{Palette.text_main};
            }}
            QComboBox:hover {{ border-color:{Palette.blue}; }}
            QComboBox::drop-down {{ border:none; width:22px; }}
            QComboBox QAbstractItemView {{
                background-color:white; border:1px solid {Palette.border}; border-radius:3px;
                selection-background-color:{Palette.tint_blue_bg}; selection-color:{Palette.blue}; outline:none;
            }}
            QDialog {{ background-color:{Palette.panel}; }}
            QLineEdit:focus {{ border:1px solid {Palette.blue}; }}
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
        스레드에서 하고, 결과만 각 패널의 signals.device_ready로 돌려받습니다."""
        self.panel_a.btn_connect.setEnabled(False)
        self.panel_b.btn_connect.setEnabled(False)
        threading.Thread(target=self._check_devices_worker, daemon=True).start()

    def _check_devices_worker(self):
        devices = adb_logic.get_devices()
        if len(devices) > 2:
            print(f"⚠️ {len(devices)}대 연결됨 - 처음 2대만 사용합니다: {devices[:2]}")

        info_a = self._query_device_info(devices[0]) if len(devices) >= 1 else None
        info_b = self._query_device_info(devices[1]) if len(devices) >= 2 else None

        self.panel_a.signals.device_ready.emit(info_a)
        self.panel_b.signals.device_ready.emit(info_b)

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
