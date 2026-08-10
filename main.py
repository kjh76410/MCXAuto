import sys

from PySide6.QtWidgets import QApplication

from ui_common import RobotLauncherButton
from ui_logic import App

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = App()
    launcher = RobotLauncherButton()

    def launch_tool():
        window.show()
        window.raise_()
        window.activateWindow()

    launcher.open_main_requested.connect(launch_tool)
    launcher.show()

    sys.exit(app.exec())
