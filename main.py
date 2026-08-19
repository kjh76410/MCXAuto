import sys

from PySide6.QtWidgets import QApplication

import adb_logic
import project_config_store
from project_window import ProjectWindow
from ui_common import RobotLauncherButton, place_as_left_card
from ui_logic import App

# 프로젝트 메뉴 박스에 돌려가며 쓸 색.
PROJECT_COLORS = ["#7FA8E8", "#F0AA6E", "#EF9A96", "#7FD8C6", "#E29BDB"]


def build_menu_items(open_admin, open_project):
    """런처를 펼칠 때마다 새로 만드는 메뉴 박스 목록.
    맨 앞(런처와 가장 가까운 쪽)은 '시나리오 추가'(= 관리 창), 그 왼쪽으로
    project_config.json에 등록된 프로젝트들이 이어집니다."""
    items = [{
        "label": "시나리오 추가",
        "icon": "fa5s.plus",
        "color": RobotLauncherButton.QA_COLOR,
        "on_click": open_admin,
    }]

    for i, proj in enumerate(project_config_store.list_projects()):
        name = proj.get("project_name")
        if not name:
            continue
        items.append({
            "label": name,
            "icon": "fa5s.folder",
            "color": PROJECT_COLORS[i % len(PROJECT_COLORS)],
            "on_click": lambda p=name: open_project(p),
        })

    return items


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 관리 창(사이드바: 프로젝트 관리 / 객체 관리 / 시나리오 작성 / 시나리오)과
    # 프로젝트 창(대시보드 + 시나리오 목록)은 서로 다른 창이지만, 단말 패널
    # (DevicePanel) 인스턴스는 관리 창이 만든 것을 프로젝트 창이 같이 씁니다.
    admin_window = App()
    project_window = ProjectWindow(admin_window.panel_a)

    def open_project(project_name):
        project_window.set_project(project_name)
        place_as_left_card(project_window)

    # 예전에는 관리 창을 닫을 때 adb 서버를 내렸지만, 이제 창이 둘로 나뉘어서
    # 한쪽 창만 닫아도 다른 창의 adb 작업이 끊깁니다. 프로그램 자체가 끝날 때만 내립니다.
    app.aboutToQuit.connect(adb_logic.kill_adb_server)

    launcher = RobotLauncherButton()
    launcher.set_menu_items_provider(
        lambda: build_menu_items(admin_window.show_as_left_card, open_project)
    )
    launcher.show()

    sys.exit(app.exec())
