import customtkinter as ctk
import tkinter as tk
import adb_logic
import os
import ctypes
import sys
import datetime
import json
import time
import pymysql
import re
import subprocess
import importlib
import time
import threading
from tkinter import filedialog
from file_manager import FileManager
from common_logger import start_device_logging


def load_custom_font(font_filename):
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    font_path = os.path.join(base_path, "assets", "fonts", font_filename)

    if os.path.exists(font_path):
        ctk.FontManager.load_font(font_path)
    else:
        print(f"⚠️ 폰트 파일을 찾을 수 없습니다: {font_path}")


load_custom_font("NotoSansKR-Regular.ttf")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("QA Automation Dashboard")
        self.geometry("1450x850")  # 3단 구성을 위해 가로를 조금 더 넓혔습니다.

        # ==========================================
        # 🎨 [Modern SaaS Color Palette]
        # ==========================================
        self.bg_color = "#F4F5F7"  # 밝은 쿨그레이 (배경)
        self.panel_bg = "#FFFFFF"  # 순백색 (카드/패널)
        self.border_color = "#E2E8F0"  # 연한 테두리

        self.text_main = "#0F172A"  # 진한 흑회색 (기본 텍스트)
        self.text_sub = "#64748B"  # 중간 회색 (서브 텍스트)

        self.point_blue = "#3B82F6"  # 포인트 파랑 (설정, 일반 버튼)
        self.point_pink = "#EC4899"  # 포인트 핑크 (PCAP, 로그, 분석)
        self.point_green = "#10B981"  # 포인트 초록 (연결, 실행, 성공)
        self.danger_color = "#EF4444"  # 빨강 (삭제, 중지)

        self.btn_bg_light = "#F1F5F9"
        self.btn_hover_light = "#E2E8F0"

        self.configure(fg_color=self.bg_color)
        self.current_uuid = None
        self.radius = 12  # 둥근 모서리 강화

        # ------------------------------------------
        # 📱 1. 좌측 영역: Device & Configuration (설정)
        # ------------------------------------------
        self.left_panel = ctk.CTkFrame(
            self,
            width=300,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        self.left_panel.pack(side="left", fill="y", padx=(16, 8), pady=16)
        self.left_panel.pack_propagate(False)

        # 기기 연결 섹션
        ctk.CTkLabel(
            self.left_panel,
            text="Device Setup",
            font=("Noto Sans KR", 16, "bold"),
            text_color=self.text_main,
        ).pack(pady=(20, 5), padx=20, anchor="w")

        # ✨ 1. 프로젝트명을 더 크고(14) 진한 검정색(text_main)으로 변경!
        self.lbl_project = ctk.CTkLabel(
            self.left_panel,
            text="프로젝트: 대기 중",
            font=("Noto Sans KR", 14, "bold"),
            text_color=self.text_main,
        )
        self.lbl_project.pack(padx=20, anchor="w")

        self.label = ctk.CTkLabel(
            self.left_panel,
            text="단말을 연결해주세요.",
            font=("Noto Sans KR", 12),
            text_color=self.text_sub,
        )
        self.label.pack(pady=(5, 15), padx=20, anchor="w")

        self.btn_connect = ctk.CTkButton(
            self.left_panel,
            text="🟢 기기 연결 및 미러링",
            font=("Noto Sans KR", 13, "bold"),
            fg_color=self.point_green,
            hover_color="#059669",
            height=42,
            corner_radius=self.radius,
            command=self.check_device,
        )
        self.btn_connect.pack(padx=20, fill="x")

        # 기기 정보 요약
        self.info_frame = ctk.CTkFrame(
            self.left_panel, fg_color=self.btn_bg_light, corner_radius=8
        )
        self.info_frame.pack(fill="x", padx=20, pady=15)

        # ✨ 2 & 3. 텍스트를 검정색(text_main)으로 통일하고 버전 정보들 추가!
        self.lbl_model = ctk.CTkLabel(
            self.info_frame,
            text="모델: -",
            font=("Noto Sans KR", 12),
            text_color=self.text_main,
        )
        self.lbl_model.pack(pady=(10, 2), padx=10, anchor="w")

        self.lbl_hw_version = ctk.CTkLabel(
            self.info_frame,
            text="HW 버전: -",
            font=("Noto Sans KR", 12),
            text_color=self.text_main,
        )
        self.lbl_hw_version.pack(pady=2, padx=10, anchor="w")

        self.lbl_android_ver = ctk.CTkLabel(
            self.info_frame,
            text="Android 버전: -",
            font=("Noto Sans KR", 12),
            text_color=self.text_main,
        )
        self.lbl_android_ver.pack(pady=2, padx=10, anchor="w")

        self.lbl_os_build = ctk.CTkLabel(
            self.info_frame,
            text="OS 버전: -",
            font=("Noto Sans KR", 12),
            text_color=self.text_main,
        )
        self.lbl_os_build.pack(pady=2, padx=10, anchor="w")

        self.lbl_version = ctk.CTkLabel(
            self.info_frame,
            text="앱 버전: -",
            font=("Noto Sans KR", 12),
            text_color=self.text_main,
        )
        self.lbl_version.pack(pady=2, padx=10, anchor="w")

        self.lbl_network = ctk.CTkLabel(
            self.info_frame,
            text="📶 네트워크: -",
            font=("Noto Sans KR", 12),
            text_color=self.text_main,
        )
        self.lbl_network.pack(pady=(2, 10), padx=10, anchor="w")

        ctk.CTkFrame(self.left_panel, height=1, fg_color=self.border_color).pack(
            fill="x", padx=20, pady=5
        )

        # 설정 섹션 (환경, WiFi)
        ctk.CTkLabel(
            self.left_panel,
            text="Configuration",
            font=("Noto Sans KR", 14, "bold"),
            text_color=self.text_main,
        ).pack(pady=(15, 10), padx=20, anchor="w")

        row_config = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        row_config.pack(fill="x", padx=20, pady=2)
        self.btn_env = ctk.CTkButton(
            row_config,
            text="⚙️ 환경 설정",
            font=("Noto Sans KR", 12),
            fg_color=self.btn_bg_light,
            text_color=self.point_blue,
            hover_color=self.btn_hover_light,
            height=36,
            corner_radius=self.radius,
            command=self.open_env_setup,
        )
        self.btn_env.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.btn_wifi = ctk.CTkButton(
            row_config,
            text="📶 WiFi 설정",
            font=("Noto Sans KR", 12),
            fg_color=self.btn_bg_light,
            text_color=self.point_blue,
            hover_color=self.btn_hover_light,
            height=36,
            corner_radius=self.radius,
            command=self.open_wifi_setup,
        )
        self.btn_wifi.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # 앱 관리 섹션
        ctk.CTkLabel(
            self.left_panel,
            text="App Management",
            font=("Noto Sans KR", 14, "bold"),
            text_color=self.text_main,
        ).pack(pady=(25, 10), padx=20, anchor="w")

        self.btn_install = ctk.CTkButton(
            self.left_panel,
            text="📦 앱 설치 (.apk)",
            font=("Noto Sans KR", 12),
            fg_color="transparent",
            border_width=1,
            border_color=self.border_color,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            height=36,
            command=self.run_install_app,
        )
        self.btn_install.pack(fill="x", padx=20, pady=4)

        row_app = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        row_app.pack(fill="x", padx=20, pady=4)
        self.btn_clear_data = ctk.CTkButton(
            row_app,
            text="🧹 데이터 삭제",
            font=("Noto Sans KR", 12),
            fg_color="transparent",
            border_width=1,
            border_color=self.border_color,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            height=36,
            command=self.run_clear_data,
        )
        self.btn_clear_data.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.btn_uninstall = ctk.CTkButton(
            row_app,
            text="🗑️ 앱 삭제",
            font=("Noto Sans KR", 12),
            fg_color="transparent",
            border_width=1,
            border_color=self.danger_color,
            text_color=self.danger_color,
            hover_color="#FEE2E2",
            height=36,
            command=self.run_uninstall_app,
        )
        self.btn_uninstall.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # ------------------------------------------
        # ⚡ 2. 중앙 영역: Execution & Mirroring (실행 및 화면)
        # ------------------------------------------
        self.mid_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.mid_panel.pack(side="left", expand=True, fill="both", padx=8, pady=16)

        # 상단 실행 컨트롤 (버튼 3개 나란히 배치)
        self.mid_top = ctk.CTkFrame(
            self.mid_panel,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        self.mid_top.pack(fill="x", pady=(0, 12), ipady=5)

        self.btn_run_scenario = ctk.CTkButton(
            self.mid_top,
            text="▶ 전체 시나리오 실행",
            font=("Noto Sans KR", 13, "bold"),
            fg_color=self.point_blue,
            hover_color="#2563EB",
            text_color="#FFFFFF",
            height=36,
            corner_radius=self.radius,
            command=self.run_automation,
        )
        self.btn_run_scenario.pack(side="left", padx=(15, 5), pady=10)

        self.btn_stop_scenario = ctk.CTkButton(
            self.mid_top,
            text="⏹ 중지",
            font=("Noto Sans KR", 13, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=self.danger_color,
            text_color=self.danger_color,
            hover_color="#FEE2E2",
            height=36,
            command=self.stop_automation,
        )
        self.btn_stop_scenario.pack(side="left", padx=5, pady=10)

        # ✨ [신규] 단위 테스트 팝업 버튼 추가
        self.btn_unit_test = ctk.CTkButton(
            self.mid_top,
            text="🛠️ 단위 테스트",
            font=("Noto Sans KR", 13, "bold"),
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            height=36,
            corner_radius=self.radius,
            command=self.open_unit_test_popup,
        )
        self.btn_unit_test.pack(side="left", padx=5, pady=10)

        # ==========================================
        # 💡 [신규] 프로젝트 기능을 표시할 가로로 긴 하얀색 카드!
        # ==========================================
        self.feature_card = ctk.CTkFrame(
            self.mid_panel,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        # 윗 카드와 동일하게 가로로 꽉 차게(fill="x") 배치합니다.
        self.feature_card.pack(fill="x", pady=(0, 12), ipady=5)

        # 이 카드 안에 태그들을 담을 쟁반을 만듭니다. (이름은 기존과 동일하게 유지)
        self.feature_tag_frame = ctk.CTkFrame(self.feature_card, fg_color="transparent")
        self.feature_tag_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            self.feature_tag_frame,
            text="단말기를 연결하면 이곳에 프로젝트 지원 기능이 표시됩니다.",
            font=("Noto Sans KR", 12),
            text_color=self.text_sub,
        ).pack(pady=2)
        # ==========================================

        # 단위 테스트 & 미러링 분할 (가로배치)
        self.mid_content = ctk.CTkFrame(self.mid_panel, fg_color="transparent")
        self.mid_content.pack(expand=True, fill="both")

        # ------------------------------------------
        # 2-1. 중앙-좌측 컨트롤 (단위 테스트 & 그룹 목록 탭 스위칭)
        # ------------------------------------------

        self.current_mode = "call"  # 기본값: 통화 모드
        self.all_cards = []

        self.action_container = ctk.CTkFrame(
            self.mid_content,
            width=350,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        self.action_container.pack_propagate(False)

        self.action_container.pack(side="left", fill="y", padx=(0, 12))

        # 1. 헤더 프레임 (버튼들을 담을 공간)
        header_frame = ctk.CTkFrame(self.action_container, fg_color="transparent")
        header_frame.pack(fill="x", padx=5, pady=(5, 5))

        # 2. Group List 버튼
        self.btn_tab_group = ctk.CTkButton(
            header_frame,
            text="Group List",
            height=32,
            corner_radius=6,
            fg_color=self.point_blue,
            text_color="white",
            command=lambda: self.switch_tab("group"),
        )
        self.btn_tab_group.pack(side="left", expand=True, fill="x", padx=(0, 2))

        # 3. User List 버튼
        self.btn_tab_user = ctk.CTkButton(
            header_frame,
            text="User List",
            height=32,
            corner_radius=6,
            fg_color="#E2E8F0",
            text_color="#475569",
            command=lambda: self.switch_tab("user"),
        )
        self.btn_tab_user.pack(side="left", expand=True, fill="x", padx=(2, 2))

        # 4. 새로고침 버튼 (우측에 배치)
        self.btn_refresh = ctk.CTkButton(
            header_frame,
            text="🔄",
            width=32,
            height=32,
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            command=self.refresh_all_lists,
        )
        self.btn_refresh.pack(side="right", padx=(2, 0))

        # 1. 탭 전환용 리스트 프레임들을 먼저 나란히 생성합니다.
        self.group_list_frame = ctk.CTkScrollableFrame(
            self.action_container, fg_color="transparent"
        )
        self.group_list_frame.pack(expand=True, fill="both", padx=5, pady=5)

        self.user_list_frame = ctk.CTkScrollableFrame(
            self.action_container, fg_color="transparent"
        )
        # user_list_frame은 처음엔 숨겨둡니다 (pack 하지 않음)

        # 2. 하단 액션 버튼 프레임을 생성하고 맨 '아래'에 고정시킵니다.
        btn_action_frame = ctk.CTkFrame(self.action_container, fg_color="transparent")
        # 💡 [핵심] side="bottom"을 추가해서 탭을 바꿔도 버튼이 항상 아래에 있도록 합니다.
        btn_action_frame.pack(side="bottom", fill="x", padx=5, pady=(0, 10))

        # 3. 버튼들 생성 (btn_action_frame 안에 배치)
        self.btn_group_call = ctk.CTkButton(
            btn_action_frame,
            text="📞 통화",
            font=("Noto Sans KR", 13, "bold"),
            fg_color=self.point_green,
            hover_color="#059669",
            text_color="#FFFFFF",
            height=36,
            corner_radius=self.radius,
            command=self.on_main_call_button_clicked,
        )
        self.btn_group_call.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_group_msg = ctk.CTkButton(
            btn_action_frame,
            text="💬 메시지",
            font=("Noto Sans KR", 13, "bold"),
            fg_color=self.point_blue,
            hover_color="#2563EB",
            text_color="#FFFFFF",
            height=36,
            corner_radius=self.radius,
            command=self.send_group_message,
        )
        self.btn_group_msg.pack(side="left", expand=True, fill="x", padx=(4, 0))

        self.my_id_label = ctk.CTkLabel(
            self.action_container,
            text="내 정보: 연결 대기",
            font=("Noto Sans KR", 12, "bold"),
            text_color=self.point_blue,
        )
        self.my_id_label.pack(fill="x", padx=10, pady=(0, 5))

        # 2-2. 미러링 화면
        self.mirror_section = ctk.CTkFrame(
            self.mid_content,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        self.mirror_section.pack(side="left", expand=True, fill="both")

        mirror_top = ctk.CTkFrame(
            self.mirror_section, height=40, fg_color="transparent"
        )
        mirror_top.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(
            mirror_top,
            text="📱 Device Preview",
            font=("Noto Sans KR", 13, "bold"),
            text_color=self.text_main,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            mirror_top,
            text="📸 캡쳐",
            font=("Noto Sans KR", 11),
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            width=60,
            height=26,
            command=self.capture_screen,
        ).pack(side="right", padx=2)

        self.mirror_container = tk.Frame(
            self.mirror_section, bg="#1E293B"
        )  # 순수 프레임 유지
        self.mirror_container.pack(expand=True, fill="both", padx=10, pady=(0, 10))
        self.lbl_placeholder = ctk.CTkLabel(
            self.mirror_container,
            text="미러링 대기 중...",
            font=("Noto Sans KR", 14),
            text_color="#94A3B8",
        )
        self.lbl_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # ------------------------------------------
        # 📊 3. 우측 영역: Monitoring & Analysis (로그/SIP)
        # ------------------------------------------
        self.right_panel = ctk.CTkFrame(
            self,
            width=400,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        self.right_panel.pack(side="right", fill="y", padx=(8, 16), pady=16)
        self.right_panel.pack_propagate(False)

        # 상단 모니터링 컨트롤
        self.monitor_ctrl = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.monitor_ctrl.pack(fill="x", padx=15, pady=15)

        self.btn_toggle_pcap = ctk.CTkButton(
            self.monitor_ctrl,
            text="🔴 PCAPdroid ON",
            font=("Noto Sans KR", 12, "bold"),
            fg_color=self.btn_bg_light,
            text_color=self.point_pink,
            hover_color="#FCE7F3",
            height=36,
            corner_radius=self.radius,
            command=self.toggle_pcap,
        )
        self.btn_toggle_pcap.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.btn_toggle_log = ctk.CTkButton(
            self.monitor_ctrl,
            text="📝 Logcat ON",
            font=("Noto Sans KR", 12, "bold"),
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            height=36,
            corner_radius=self.radius,
            command=self.toggle_log,
        )
        self.btn_toggle_log.pack(side="left", expand=True, fill="x", padx=(5, 0))

        # 탭 뷰 생성 (SIP Flow, Logcat, PCAP)
        self.tab_view = ctk.CTkTabview(
            self.right_panel,
            fg_color=self.btn_bg_light,
            segmented_button_selected_color=self.point_pink,
            segmented_button_selected_hover_color="#DB2777",
        )
        self.tab_view.pack(expand=True, fill="both", padx=15, pady=(0, 15))

        self.tab_view.add("SIP Flow")
        self.tab_view.add("System Log")
        self.tab_view.add("PCAP Dump")

        # [Tab 1] SIP Flow (최종 목표 공간)
        ctk.CTkLabel(
            self.tab_view.tab("SIP Flow"),
            text="SIP Flow Visualization\n(향후 Call 진행 시 이곳에 패킷 흐름 표시)",
            font=("Noto Sans KR", 12),
            text_color=self.text_sub,
        ).pack(expand=True)
        # TODO: 추후 여기에 트리뷰(Treeview)나 캔버스를 넣어 화살표 흐름을 그릴 수 있습니다.

        # [Tab 2] System Log
        self.entry_search = ctk.CTkEntry(
            self.tab_view.tab("System Log"),
            placeholder_text="🔍 검색 필터 (INVITE, Exception 등)",
            height=32,
            corner_radius=8,
        )
        self.entry_search.pack(fill="x", pady=(0, 5))
        self.txt_log = ctk.CTkTextbox(
            self.tab_view.tab("System Log"),
            font=("Consolas", 11),
            fg_color="#FFFFFF",
            text_color=self.text_main,
            border_width=1,
            border_color=self.border_color,
            corner_radius=8,
        )
        self.txt_log.pack(expand=True, fill="both")
        self.txt_log.insert("1.0", "시스템 로그 대기 중...\n")

        # [Tab 3] PCAP Dump
        self.txt_pcap = ctk.CTkTextbox(
            self.tab_view.tab("PCAP Dump"),
            font=("Consolas", 11),
            fg_color="#FFFFFF",
            text_color=self.text_main,
            border_width=1,
            border_color=self.border_color,
            corner_radius=8,
        )
        self.txt_pcap.pack(expand=True, fill="both")
        self.txt_pcap.insert("1.0", "패킷 캡처 대기 중...\n")

        self.is_log_on = False
        self.is_pcap_on = False

    def refresh_all_lists(self):
        # 2. 버튼 눌렀을 때 실행되는 함수 내부에서는 이렇게 호출하세요!
        self.config_handler.setup_environment()

    # ==========================================
    # 기능 동작 메서드들
    # ==========================================
    def check_device(self):
        devices = adb_logic.get_devices()
        if devices:
            self.current_uuid = devices[0]

            # 1. adb_logic에서 단말 정보 가져오기
            model = adb_logic.get_model_name(self.current_uuid)
            android_version = adb_logic.get_os_version(self.current_uuid)

            try:
                os_build = adb_logic.get_build_image_version(self.current_uuid)
            except AttributeError:
                os_build = "조회 불가"

            version_name = adb_logic.get_everytalk_version(self.current_uuid)
            project_name = FileManager.get_project_name(version_name)

            # (선택) HW 버전 가져오는 함수가 있다면 연결, 없다면 알 수 없음 처리
            hw_version = getattr(adb_logic, "get_hw_version", lambda x: "조회 불가")(
                self.current_uuid
            )

            network_status = adb_logic.get_network_status(self.current_uuid)

            # 2. UI 라벨 텍스트 업데이트
            # (🌟 이전에 쓰던 lbl_battery 같은 코드가 있으면 여기서 에러가 났을 겁니다)
            self.label.configure(text=f"연결됨: {model}", text_color=self.point_green)

            self.lbl_model.configure(text=f"모델: {model}")
            self.lbl_hw_version.configure(text=f"HW 버전: {hw_version}")
            self.lbl_android_ver.configure(text=f"Android 버전: {android_version}")
            self.lbl_os_build.configure(text=f"OS 버전: {os_build}")
            self.lbl_version.configure(text=f"앱 버전: {version_name}")

            self.lbl_network.configure(
                text=f"📶 네트워크: {network_status}", text_color=self.text_main
            )

            self.lbl_project.configure(text=f"프로젝트: {project_name}")

            self.update_project_features(project_name)

            adb_logic.unlock_screen(self.current_uuid)

            # 3. 미러링 및 그룹 목록 새로고침 실행
            self.run_mirror()
            # self.refresh_group_list()

        else:
            # 단말기 연결이 끊겼을 때 UI 초기화
            self.current_uuid = None
            self.label.configure(text="연결된 단말 없음", text_color=self.text_sub)

            self.lbl_model.configure(text="모델: -")
            self.lbl_hw_version.configure(text="HW 버전: -")
            self.lbl_android_ver.configure(text="Android 버전: -")
            self.lbl_os_build.configure(text="OS 버전: -")
            self.lbl_version.configure(text="앱 버전: -")
            self.lbl_network.configure(text="📶 네트워크: -", text_color=self.text_main)
            self.lbl_project.configure(
                text="프로젝트: 대기 중", text_color=self.text_main
            )

            for widget in self.feature_tag_frame.winfo_children():
                widget.destroy()

            ctk.CTkLabel(
                self.feature_tag_frame,
                text="단말기를 연결하면 이곳에 프로젝트 지원 기능이 표시됩니다.",
                font=("Noto Sans KR", 12),
                text_color=self.text_sub,
            ).pack(pady=2)

    def update_project_features(self, project_name):
        """JSON 설정에 따라 지원하는 기능(1)만 카테고리별로 3줄로 나누어 표시합니다."""
        # 1. 기존에 그려진 태그들 싹 지우기
        for widget in self.feature_tag_frame.winfo_children():
            widget.destroy()

        # 2. JSON에서 지원 기능 가져오기
        features = FileManager.get_project_features(project_name)
        if not features:
            self.has_private_call = False  # 기능 정보가 없으면 기본 차단
            return

        group_map = {"regroup": "ReGroup", "prearranged": "PreArranged", "chat": "Chat"}
        private_map = {
            "normal": "Normal",
            "without_floor_control": "W/O Floor",
            "mcvideo_push": "Video Push",
            "mcvideo_pull": "Video Pull",
            "first_answer": "First Answer",
        }
        msg_map = {
            "normal": "일반",
            "emergency": "비상",
            "pre_defined": "Pre-Defined",
            "canned": "상용문구",
            "attachment": "첨부파일",
        }

        # ==========================================
        # 💡 [핵심 차단 로직 1] Private Call 지원 여부 판별 및 UI 제어
        # ==========================================
        private_call_data = features.get("private_call", {})
        
        # private_call 안에 1(활성화)인 값이 하나라도 있는지 검사
        self.has_private_call = any(val == 1 for val in private_call_data.values())

        if self.has_private_call:
            # 🟢 지원하는 경우: User List 버튼 활성화
            self.btn_tab_user.configure(state="normal", text_color="#475569")
        else:
            # 🔴 지원하지 않는 경우: User List 버튼 비활성화 (클릭 불가)
            self.btn_tab_user.configure(state="disabled", text_color="#CBD5E1")
            
            # 유저 탭을 보고 있던 중에 프로젝트가 바뀌었다면 강제로 그룹 탭으로 이동
            if getattr(self, "current_mode", "group") == "user":
                self.switch_tab("group")
        # ==========================================

        # 🎨 카테고리별로 줄(Row)을 생성하는 함수
        def create_tag_row(title, icon, category_data, name_map, bg_color, txt_color):
            active_features = [
                name_map[key]
                for key, val in category_data.items()
                if val == 1 and key in name_map
            ]
            if not active_features:
                return

            row_frame = ctk.CTkFrame(self.feature_tag_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=3)  # 줄 사이의 간격

            ctk.CTkLabel(
                row_frame,
                text=f"{icon} {title}:",
                font=("Noto Sans KR", 12, "bold"),
                text_color=self.text_sub,
                width=80,  # 정렬을 위해 타이틀 라벨 가로 길이를 고정
                anchor="w",  # 왼쪽 정렬
            ).pack(side="left", padx=(0, 5))

            # 해당 줄에 뱃지들 가로로 나열
            for f_name in active_features:
                ctk.CTkLabel(
                    row_frame,
                    text=f_name,
                    font=("Noto Sans KR", 11, "bold"),
                    fg_color=bg_color,  
                    text_color=txt_color,  
                    corner_radius=6,
                    padx=8,
                    pady=2,
                ).pack(side="left", padx=3)

        # 4. 각 카테고리를 독립된 줄로 생성 (최대 3줄)
        create_tag_row("Group", "👥", features.get("group_call", {}), group_map, bg_color="#DBEAFE", txt_color="#1E40AF")
        create_tag_row("Private", "👤", private_call_data, private_map, bg_color="#D1FAE5", txt_color="#065F46")
        create_tag_row("Message", "✉️", features.get("message", {}), msg_map, bg_color="#FFEDD5", txt_color="#9A3412")

    def refresh_group_list(self):
        if not self.current_uuid:
            return

        # 1. 단말기에서 XML 폴더 가져오기
        path = FileManager.pull_profile_xml(self.current_uuid)
        if not path or not os.path.exists(path):
            return

        groups = FileManager.parse_group_list(path)
        my_info = FileManager.parse_my_info(path)
        self.my_id_label.configure(text=f"내 정보: {my_info}")

        # 3. 기존 화면 초기화
        self.all_cards = []
        self.group_check_vars = {}
        for widget in self.group_list_frame.winfo_children():
            widget.destroy()

        # ==========================================
        # 🎨 내부 함수: 섹션 그리기
        # ==========================================
        def create_section(title, group_list):
            # 해당 타입의 그룹이 없으면 섹션 자체를 그리지 않고 패스
            if not group_list:
                return

            # 섹션 타이틀 라벨
            ctk.CTkLabel(
                self.group_list_frame,
                text=title,
                font=("Noto Sans KR", 12, "bold"),
                text_color=self.text_sub,
            ).pack(anchor="w", padx=5, pady=(15, 5))

            # 그룹 개수만큼 카드 생성
            for g_info in group_list:
                # 1) 카드 배경 프레임
                card = ctk.CTkFrame(
                    self.group_list_frame,
                    fg_color="#F8FAFC",
                    corner_radius=8,
                    border_width=1,
                    border_color=self.border_color,
                )
                card.pack(fill="x", padx=5, pady=4)

                # 2) 코덱 문자열 조립
                voice = g_info.get("voice_codec", "")
                video = g_info.get("video_codec", "")
                codec_str = ""
                if voice or video:
                    v_str = f"🎤 {voice}" if voice else ""
                    vd_str = f"🎬 {video}" if video else ""
                    divider = " | " if (voice and video) else ""
                    codec_str = f"[{v_str}{divider}{vd_str}]"

                # 3) 체크박스 (그룹명 & ID)
                var_check = ctk.StringVar(value="off")
                chk = ctk.CTkCheckBox(
                    card,
                    text=f"{g_info['name']} ({g_info['id']})",
                    variable=var_check,
                    onvalue="on",
                    offvalue="off",
                    border_width=1,
                    border_color="#94A3B8",
                    fg_color=self.point_blue,
                    font=("Noto Sans KR", 13, "bold"),
                    text_color=self.text_main,
                    command=self.update_group_visibility,
                )
                chk.pack(anchor="w", padx=10, pady=(10, 0))

                # 4) 코덱 라벨 출력
                if codec_str:
                    lbl_codec = ctk.CTkLabel(
                        card,
                        text=codec_str,
                        font=("Noto Sans KR", 10),
                        text_color="#64748B",
                    )
                    lbl_codec.pack(anchor="w", padx=(36, 10), pady=(0, 10))

                # 5) 액션 버튼 행 (통화, 메시지)
                action_row = ctk.CTkFrame(card, fg_color="transparent")

                seg_call = ctk.CTkSegmentedButton(
                    action_row,
                    values=["🔊 PTT", "📹 PTV", "🚨 E-PTT", "🚨 E-PTV"],
                    height=32,
                    font=("Noto Sans KR", 11, "bold"),
                    fg_color="#F8FAFC",
                    selected_color="#2563EB",
                    selected_hover_color="#2563EB",
                    unselected_color="#E2E8F0",
                    unselected_hover_color="#CBD5E1",
                    text_color="#CBD5E1",
                )

                seg_msg = ctk.CTkSegmentedButton(
                    action_row,
                    values=["📄 Text", "🖼️ Photo", "🎥 Video"],
                    height=32,
                    font=("Noto Sans KR", 11, "bold"),
                    fg_color="#F8FAFC",
                    selected_color="#2563EB",
                    selected_hover_color="#2563EB",
                    unselected_color="#E2E8F0",
                    unselected_hover_color="#CBD5E1",
                    text_color="#CBD5E1",
                )

                # 6) 데이터 저장 (나중에 제어하기 위함)
                card.check_var = var_check
                card.action_row = action_row
                card.seg_call = seg_call
                card.seg_msg = seg_msg

                self.all_cards.append(card)
                self.group_check_vars[g_info["id"]] = {
                    "check_var": var_check,
                    "call_var": seg_call,
                    "msg_var": seg_msg,
                    "name": g_info["name"],
                }

        # ==========================================
        # 🚀 화면에 순서대로 섹션 출력
        # ==========================================
        # 1. ReGroup을 최상단에 출력
        create_section("◆ ReGroup", [g for g in groups if g.get("type") == "ReGroup"])

        # 2. PreArranged 출력
        create_section(
            "◆ PreArranged Group",
            [g for g in groups if g.get("type") == "PreArranged Group"],
        )

        # 3. Chat Group 출력
        create_section(
            "◆ Chat Group", [g for g in groups if g.get("type") == "Chat Group"]
        )

        # 4. 최종 렌더링 업데이트 (선택 안 된 버튼들 숨기기 등)
        self.update_group_visibility()

    def update_group_visibility(self):
        # 모드가 설정되지 않은 초기 상태 방어
        if not hasattr(self, "current_mode") or self.current_mode is None:
            self.current_mode = "call"

        # 모든 카드를 돌면서 상태 동기화
        for card in self.all_cards:

            # ✨ [핵심 해결 포인트] 1. 버튼을 숨기기 '전에' 체크 해제 상태면 값을 먼저 비워줍니다!
            if card.check_var.get() == "off":
                card.seg_call.set("")  # 통화 종류 선택 초기화
                card.seg_msg.set("")  # 메시지 종류 선택 초기화

            # 2. 그 다음, 안전하게 액션 로우를 화면에서 숨깁니다.
            card.action_row.pack_forget()
            card.seg_call.pack_forget()
            card.seg_msg.pack_forget()

            # 3. 체크박스가 켜져(on) 있을 때만 다시 보여줍니다.
            if card.check_var.get() == "on":
                card.action_row.pack(fill="x", padx=10, pady=(0, 10))

                # 현재 모드에 맞는 버튼만 보여줍니다.
                if self.current_mode == "call":
                    card.seg_call.pack(side="left", expand=True, fill="x", padx=(0, 10))
                else:
                    card.seg_msg.pack(side="left", expand=True, fill="x", padx=(0, 10))

    
    def on_call_button(self):
        self.current_mode = "call"
        self.update_group_visibility()

    def on_msg_button(self):
        self.current_mode = "msg"
        self.update_group_visibility()  # 화면 아이콘 먼저 갱신

    def on_main_call_button_clicked(self):

        

        if not self.current_uuid:
            self.txt_log.insert("end", "⚠️ 단말기가 연결되지 않았습니다!\n")
            return

        selected_targets = []
        
        # 1. 딕셔너리를 돌면서 체크된 그룹과 선택된 통화 모드를 수집합니다.
        for group_id, data in self.group_check_vars.items():
            if data["check_var"].get() == "on": # 체크박스가 켜져 있다면!
                
                # seg_call에서 현재 눌려있는 값을 가져옵니다 (예: "🔊 PTT" 또는 "📹 PTV")
                raw_mode = data["call_var"].get() 
                
                if not raw_mode:
                    self.txt_log.insert("end", f"⚠️ '{data['name']}' 그룹의 통화 방식(PTT/PTV)이 선택되지 않아 제외됩니다.\n")
                    self.txt_log.see("end")
                    continue
                
                # 💡 "🔊 PTT" 같은 문자열에서 아이콘을 떼고 "PTT" 글자만 깔끔하게 추출합니다.
                # (빈칸 기준으로 쪼개서 맨 마지막 글자 가져오기)
                clean_mode = raw_mode.split(" ")[-1] 
                
                # 발신 리스트에 딕셔너리 형태로 추가
                selected_targets.append({
                    "id": group_id,         # 82900110119
                    "name": data["name"],   # CT APP 테스트 6_SRTP
                    "mode": clean_mode      # PTT, PTV, E-PTT 등
                })

        # 2. 발신할 대상이 없으면 종료
        if not selected_targets:
            self.txt_log.insert("end", "⚠️ 발신을 진행할 그룹이 없습니다. 체크박스와 통화 방식을 확인해주세요.\n")
            self.txt_log.see("end")
            return

        proj_name = self.project_name

        # 3. UI가 멈추지 않도록 백그라운드 쓰레드에서 순차 발신 실행!
        threading.Thread(target=self._process_sequential_calls, args=(proj_name, selected_targets), daemon=True).start()

    # ==========================================
    # 💡 백그라운드에서 순차 발신을 수행하는 쓰레드 함수
    # ==========================================
    def _process_sequential_calls(self, proj_name, selected_targets):
        self.txt_log.insert("end", f"\n[System] 총 {len(selected_targets)}개 그룹에 순차 발신을 시작합니다...\n")
        self.txt_log.see("end")

        try:
            import uiautomator2 as u2
            d = u2.connect(self.current_uuid)

            # 통역사 로직 (어떤 단말기 핸들러를 부를지 결정)
            if proj_name == "재난망":
                module_name = "config_handlers.ps_lte_handler"
                class_name = "PsLteHandler"
            elif proj_name == "재난망_LM75":
                module_name = "config_handlers.ps_lte_lm75_handler"
                class_name = "PsLteLm75Handler"
            else:
                self.txt_log.insert("end", f"⚠️ '{proj_name}'에 대한 발신 기능이 아직 없습니다.\n")
                return

            module = importlib.import_module(module_name)
            handler_class = getattr(module, class_name)
            handler_instance = handler_class()

            # 💡 핵심! 수집한 리스트를 하나씩 꺼내면서 전화를 겁니다.
            for idx, target in enumerate(selected_targets, 1):
                t_id = target["id"]
                t_name = target["name"]
                t_mode = target["mode"]
                
                self.txt_log.insert("end", f"\n▶️ [{idx}/{len(selected_targets)}] '{t_name}' ({t_mode}) 발신 진행 중...\n")
                self.txt_log.see("end")
                
                # 🚀 아까 우리가 짰던 완벽한 핸들러 호출! (call_mode 전달)
                handler_instance.make_call(d, target_info=t_id, call_mode=t_mode, log_console=self.txt_log)
                
                # 다음 통화를 걸기 전에 단말기와 네트워크가 안정화될 시간 3초 대기
                time.sleep(3) 

            self.txt_log.insert("end", "\n✅ 모든 순차 발신 테스트가 완료되었습니다!\n")
            self.txt_log.see("end")

        except Exception as e:
            self.txt_log.insert("end", f"❌ 발신 프로세스 중 오류 발생: {e}\n")
            self.txt_log.see("end")
    

    def on_group_selected(self, group_dict):
        # group_dict는 이제 {'name': '...', 'id': '...', 'type': '...'} 입니다.
        name = group_dict["name"]
        call_id = group_dict["id"]
        print(f"선택된 그룹: {name}, ID: {call_id}")

    def run_mirror(self):
        # ✨ [핵심 변경점 2] 대기 중 글자 가리기!
        self.lbl_placeholder.place_forget()

        # UI 강제 갱신
        self.mirror_container.update_idletasks()

        width = self.mirror_container.winfo_width()
        height = self.mirror_container.winfo_height()
        parent_hwnd = self.mirror_container.winfo_id()

        if width <= 1 or height <= 1:
            width, height = 400, 800

        # 미러링 시작
        adb_logic.start_mirroring_embedded(
            self.current_uuid, parent_hwnd, width, height
        )

    def press_key(self, keycode):
        if self.current_uuid:
            adb_logic.send_keyevent(self.current_uuid, keycode)

    def execute_action(self, category, item):
        print(f"▶ 개별 단위 테스트 실행: [{category}] -> {item}")

    def run_clear_data(self):
        if not self.current_uuid:
            return
        target_package = "com.EveryTalk.Global"
        adb_logic.clear_app_data(self.current_uuid, target_package)

    def run_install_app(self):
        if not self.current_uuid:
            return
        file_path = filedialog.askopenfilename(
            title="APK 파일 선택", filetypes=[("APK", "*.apk"), ("All", "*.*")]
        )
        if file_path:
            adb_logic.install_apk(self.current_uuid, file_path)

    def open_env_setup(self):
        # 1. JSON 파일 불러오기
        try:
            with open("env_config.json", "r", encoding="utf-8") as f:
                self.config_data = json.load(f)
        except FileNotFoundError:
            print("❌ 설정 파일(env_config.json)이 없습니다.")
            return

        # 2. 팝업 창 생성 (SaaS 디자인 적용)
        window = ctk.CTkToplevel(self)
        window.title("⚙️ 프로젝트 환경 설정")
        window.geometry("320x240")
        window.configure(fg_color=self.panel_bg)  # 배경을 깔끔한 흰색(패널색)으로 통일
        window.attributes("-topmost", True)  # ✨ 팝업이 뒤로 숨지 않게 최상단 고정!

        # 3. 프로젝트 목록 (JSON의 키값들) 가져오기
        project_list = list(self.config_data.keys())

        # 타이틀 라벨
        ctk.CTkLabel(
            window,
            text="적용할 프로젝트를 선택하세요",
            font=("Noto Sans KR", 14, "bold"),
            text_color=self.text_main,
        ).pack(pady=(30, 15))

        # 4. 선택형 메뉴 생성 (드롭다운 디자인 세련되게 수정)
        self.selected_project = ctk.StringVar(value=project_list[0])
        dropdown = ctk.CTkOptionMenu(
            window,
            variable=self.selected_project,
            values=project_list,
            font=("Noto Sans KR", 13),
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            button_color=self.point_blue,
            button_hover_color="#2563EB",
            dropdown_font=("Noto Sans KR", 12),
            height=36,
            corner_radius=self.radius,
        )
        dropdown.pack(fill="x", padx=40, pady=10)

        # 5. 적용 버튼 (초록색 포인트 컬러 적용)
        btn_apply = ctk.CTkButton(
            window,
            text="✅ 설정 적용",
            font=("Noto Sans KR", 13, "bold"),
            fg_color=self.point_green,
            hover_color="#059669",
            text_color="#FFFFFF",
            height=36,
            corner_radius=self.radius,
            command=lambda: self.apply_settings(window),
        )
        btn_apply.pack(fill="x", padx=40, pady=(20, 20))

    def apply_settings(self, window):
        proj_name = self.selected_project.get()  # 예: "재난망"
        env = self.config_data[proj_name]

        if self.current_uuid:
            self.txt_log.insert("end", "[System] 자동화 실행 중...\n")

            try:
                # ==========================================
                # 💡 [핵심 추가] UI 이름 -> 파이썬 친화적인 영문 이름으로 변환 (통역사 역할)
                # ==========================================
                if proj_name == "재난망":
                    safe_proj_name = "ps_lte"
                    class_name = "PsLteHandler"
                elif proj_name == "재난망_LM75":
                    safe_proj_name = "ps_lte_lm75"
                    class_name = "PsLteLm75Handler"
                elif proj_name.lower() == "450connect":
                    safe_proj_name = "connect450"
                    class_name = "Connect450Handler"
                else:
                    # 나머지 일반 프로젝트들은 기존 규칙 적용
                    safe_proj_name = proj_name.lower()
                    class_name = f"{proj_name.upper()}Handler"
                # ==========================================

                # 1. 해당 프로젝트 파일 가져오기 (예: config_handlers.ps_lte_handler)
                module_path = f"config_handlers.{safe_proj_name}_handler"
                
                import importlib
                module = importlib.import_module(module_path)

                # 2. 클래스 가져오기 (예: PsLteHandler)
                handler_class = getattr(module, class_name)
                handler = handler_class()

                # 3. 실행
                import uiautomator2 as u2
                d = u2.connect(self.current_uuid)
                handler.run(d, env)

                from common_logger import start_device_logging
                start_device_logging(d, self.txt_log) # 여기서 self.txt_log를 넘겨주는 게 정답!
                # ==========================================

                self.txt_log.insert("end", "[System] 완료!\n")
                
            except Exception as e:
                print(f"❌ 설정 실패: {e}")
                self.txt_log.insert("end", f"[Error] 설정 실패: {e}\n")

        window.destroy()

    def open_wifi_setup(self):
        # 1. WiFi 설정 파일 불러오기
        import os

        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "wifi_config.json"
        )

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.wifi_data = json.load(f)  # {SSID: Password} 형태의 딕셔너리
        except FileNotFoundError:
            print("❌ WiFi 설정 파일(wifi_config.json)이 없습니다.")
            return

        # 2. 팝업 창 생성 (SaaS 디자인 적용)
        window = ctk.CTkToplevel(self)
        window.title("📶 WiFi 설정")
        window.geometry("320x240")
        window.configure(fg_color=self.panel_bg)  # 배경을 깔끔한 흰색(패널색)으로 통일
        window.attributes("-topmost", True)  # 팝업 최상단 고정

        # 3. 목록 가져오기 (JSON의 키값들이 곧 WiFi SSID)
        wifi_list = list(self.wifi_data.keys())
        if not wifi_list:
            wifi_list = ["목록 없음"]

        # 타이틀 라벨
        ctk.CTkLabel(
            window,
            text="접속할 WiFi를 선택하세요",
            font=("Noto Sans KR", 14, "bold"),
            text_color=self.text_main,
        ).pack(pady=(30, 15))

        # 4. 선택형 메뉴 생성 (드롭다운 디자인 세련되게 수정)
        self.selected_wifi = ctk.StringVar(value=wifi_list[0])
        dropdown = ctk.CTkOptionMenu(
            window,
            variable=self.selected_wifi,
            values=wifi_list,
            font=("Noto Sans KR", 13),
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            button_color=self.point_blue,
            button_hover_color="#2563EB",
            dropdown_font=("Noto Sans KR", 12),
            height=36,
            corner_radius=self.radius,
        )
        dropdown.pack(fill="x", padx=40, pady=10)

        # 5. 연결 버튼 (초록색 포인트 컬러 적용)
        btn_connect = ctk.CTkButton(
            window,
            text="✅ WiFi 연결",
            font=("Noto Sans KR", 13, "bold"),
            fg_color=self.point_green,
            hover_color="#059669",
            text_color="#FFFFFF",
            height=36,
            corner_radius=self.radius,
            command=lambda: self.apply_wifi_settings(window),
        )
        btn_connect.pack(fill="x", padx=40, pady=(20, 20))

    def apply_wifi_settings(self, window):
        """WiFi 연결 버튼 클릭 시 실행"""
        ssid = self.selected_wifi.get()
        password = self.wifi_data.get(ssid)

        print(f"📡 WiFi 연결 시도: {ssid} / 비밀번호: {password}")

        if self.current_uuid:
            self.txt_log.insert("end", f"[System] {ssid} WiFi 연결 시도 중...\n")
            self.txt_log.see("end")  # 로그 아래로 자동 스크롤

            # 🌟 여기가 핵심입니다! 주석을 풀고 실제 연결 함수를 실행합니다.
            # adb_logic을 불러와서 connect_wifi를 실행합니다.
            success = adb_logic.connect_wifi(self.current_uuid, ssid, password)

            if success:
                self.txt_log.insert("end", f"[System] ✅ {ssid} 연결 성공!\n")
            else:
                self.txt_log.insert("end", f"[System] ❌ {ssid} 연결 실패!\n")
            self.txt_log.see("end")

        window.destroy()

    def capture_screen(self):
        if not self.current_uuid:
            print("⚠️ 연결된 단말기가 없습니다.")
            return

        # 1. 저장할 폴더 경로 만들기 (내 PC > 사진 > QA_Captures)
        pictures_dir = os.path.join(os.path.expanduser("~"), "Pictures", "QA_Captures")

        # 폴더가 없으면 자동으로 생성
        os.makedirs(pictures_dir, exist_ok=True)

        # 2. 파일명 지정 (예: screenshot_20231025_153022.png)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        save_path = os.path.join(pictures_dir, filename)

        print("📸 캡쳐를 진행 중입니다...")

        # 3. adb_logic의 캡쳐 함수 실행
        success = adb_logic.take_screenshot(self.current_uuid, save_path)

        if success:
            print(f"✅ 캡쳐 완료! 파일이 저장되었습니다:\n{save_path}")

            # 꿀팁: 캡쳐 완료 후 사진이 저장된 폴더를 윈도우 탐색기로 자동으로 열어줍니다!
            try:
                os.startfile(pictures_dir)
            except Exception:
                pass
        else:
            print("❌ 캡쳐에 실패했습니다.")

    def toggle_record(self):
        if not self.current_uuid:
            return
        print("🎥 동영상 녹화를 시작/종료합니다.")

    def run_automation(self):
        if not self.current_uuid:
            return
        print("🚀 [자동화 시작] 시나리오를 연속 실행합니다...")

    def stop_automation(self):
        print("⏹ [자동화 중지] 시나리오를 강제 중지합니다.")

    def generate_report(self):
        print("📊 [리포트 생성] 테스트 로그를 취합합니다.")

    def toggle_log(self):
        if not self.is_log_on:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = os.path.join(os.getcwd(), "logs", f"log_{timestamp}.txt")

            # 로그 프로세스 시작
            self.log_proc, self.log_file = adb_logic.start_log_process(
                self.current_uuid, log_path
            )

            # [상태 변경] 로그 켜짐 -> "중지(OFF)" 버튼으로 변경 (빨간색 경고 느낌)
            self.btn_toggle_log.configure(
                text="■ LOG OFF",
                fg_color=self.point_pink,  # 핑크색 배경
                text_color="#FFFFFF",
            )
            self.is_log_on = True

        else:
            adb_logic.stop_process(self.log_proc)
            self.log_file.close()  # 파일 닫기

            # 로그 시작 버튼을 핑크 포인트로 강조하고 싶을 때
            self.btn_toggle_log.configure(
                text="▶ LOG ON",
                fg_color=self.btn_bg_light,  # 아까 정의하신 연한 회색 배경 (#F1F5F9)
                text_color=self.point_pink,
            )
            self.is_log_on = False

    def toggle_pcap(self):
        if not self.current_uuid:
            self.txt_pcap.insert("end", "[System] ❌ 먼저 단말기를 연결해 주세요.\n")
            self.txt_pcap.see("end")
            return

        if not self.is_pcap_on:
            self.txt_pcap.insert("end", "[System] PCAPdroid 상태 점검 및 실행 중...\n")
            self.txt_pcap.see("end")

            # 1. 캡처 시작 (앱이 없으면 여기서 자동 설치까지 해줍니다)
            success = adb_logic.start_pcapdroid(self.current_uuid)

            if success:
                self.btn_toggle_pcap.configure(
                    text="■ PCAPdroid OFF",
                    fg_color=self.point_pink,  # 핑크색 배경
                    text_color="#FFFFFF",
                )
                self.is_pcap_on = True
                self.txt_pcap.insert("end", "[System] 📡 PCAPdroid 캡처 활성화 완료!\n")
            else:
                self.txt_pcap.insert(
                    "end",
                    "[System] ❌ 캡처를 시작하지 못했습니다. 로그를 확인하세요.\n",
                )

            self.txt_pcap.see("end")
        else:
            self.txt_pcap.insert("end", "[System] 캡처 종료 중...\n")
            self.txt_pcap.see("end")

            # 2. 캡처 중지
            adb_logic.stop_pcapdroid(self.current_uuid)

            self.btn_pcap.configure(
                text="● PCAPdroid ON",
                fg_color=self.btn_bg_light,  # 아까 정의하신 연한 회색 배경 (#F1F5F9)
                text_color=self.point_pink,  # 아까 정의하신 포인트 핑크색 (#EC4899)
            )
            self.is_pcap_on = False

            self.txt_pcap.insert("end", "[System] 🛑 캡처가 중지되었습니다.\n")
            self.txt_pcap.insert(
                "end",
                "[Info] 📥 패킷 파일은 단말기 내부 [Download] 폴더에 저장되어 있습니다.\n",
            )
            self.txt_pcap.see("end")

    def toggle_device_pcap(self):
        if not self.current_uuid:
            self.txt_pcap.insert("end", "[System] ❌ 먼저 단말기를 연결해 주세요.\n")
            self.txt_pcap.see("end")
            return

        if not self.is_device_pcap_on:
            self.txt_pcap.insert(
                "end", "[System] 📱 단말(히든 메뉴) PCAP 캡처 시작...\n"
            )
            self.txt_pcap.see("end")

            # adb_logic의 새 시작 함수 호출!
            success = adb_logic.start_device_pcap(self.current_uuid)

            if success:
                self.btn_toggle_device_pcap.configure(
                    text="■ 단말 PCAP OFF",
                    fg_color="#FEE2E2",
                    text_color=self.danger_color,
                )
                self.is_device_pcap_on = True
                self.txt_pcap.insert(
                    "end", "[System] 📡 단말 자체 PCAP 캡처 활성화 완료!\n"
                )
            else:
                self.txt_pcap.insert(
                    "end",
                    "[System] ❌ 단말 PCAP 시작 실패. 터미널 로그를 확인하세요.\n",
                )
            self.txt_pcap.see("end")

        else:
            self.txt_pcap.insert("end", "[System] 📱 단말 PCAP 캡처 중지 중...\n")
            self.txt_pcap.see("end")

            # adb_logic의 새 중지 함수 호출!
            success = adb_logic.stop_device_pcap(self.current_uuid)

            if success:
                self.btn_toggle_device_pcap.configure(
                    text="단말 PCAP ON",
                    fg_color=self.btn_bg_secondary,
                    text_color=self.text_main,
                )
                self.is_device_pcap_on = False
                self.txt_pcap.insert(
                    "end", "[System] 🛑 단말 PCAP 캡처가 완료되었습니다.\n"
                )
            else:
                self.txt_pcap.insert(
                    "end", "[System] ❌ 단말 PCAP 중지 실패. 수동으로 확인해 주세요.\n"
                )
            self.txt_pcap.see("end")

    def run_clear_data(self):
        print("데이터 지우기")

    def run_install_app(self):
        print("앱 설치 버튼 클릭됨")

        # 1. 파일 탐색기 열기 (APK 파일만 선택 가능하게 필터링)
        file_path = filedialog.askopenfilename(
            title="설치할 APK 파일을 선택하세요", filetypes=[("APK files", "*.apk")]
        )

        # 사용자가 취소를 눌렀을 경우 아무것도 하지 않음
        if not file_path:
            print("사용자가 설치를 취소했습니다.")
            return

        print(f"📂 선택된 파일: {file_path}")

        # 2. ADB를 통해 APK 설치 실행
        try:
            # 비동기로 실행하면 설치 중 UI가 멈출 수 있으므로,
            # 설치 과정이 끝날 때까지 조금 기다리는 것이 좋습니다.
            print("🚀 설치 진행 중...")
            result = subprocess.run(
                ["adb", "install", "-r", file_path], capture_output=True, text=True
            )

            # 3. 설치 결과 확인
            if "Success" in result.stdout:
                print("✅ 앱 설치 성공!")
                # 필요하다면 여기서 라벨을 "앱 버전: 설치됨" 등으로 업데이트할 수 있습니다.
            else:
                print(f"❌ 설치 실패: {result.stderr}")

        except Exception as e:
            print(f"🚨 설치 중 오류 발생: {e}")

    def run_uninstall_app(self):
        package_name = "com.EveryTalk.Global"
        print(f"🚀 앱 삭제 시도 중: {package_name}")

        try:
            result = subprocess.run(
                ["adb", "uninstall", package_name], capture_output=True, text=True
            )

            # 결과 확인
            if "Success" in result.stdout:
                print("✅ 앱 삭제 성공!")
                # UI 라벨 텍스트 변경
                if hasattr(self, "lbl_version"):
                    self.lbl_version.configure(text="앱 버전: 삭제됨")
            else:
                # 이미 삭제되었거나 패키지명을 찾을 수 없을 경우 등의 메시지 출력
                print(f"⚠️ 결과: {result.stdout.strip()}")
                if "Failure" in result.stdout:
                    print(
                        "❌ 삭제 실패: 앱이 설치되어 있지 않거나 권한이 필요할 수 있습니다."
                    )

        except Exception as e:
            print(f"🚨 삭제 중 에러 발생: {e}")

    def send_group_message(self):
        if not self.current_uuid:
            return

        selected_groups = []
        selected_groups = []
        for g_id, data in self.group_check_vars.items():
            if data["check_var"].get() == "on":
                selected_groups.append(
                    {
                        "name": data["name"],
                        "id": g_id,
                        "msg_type": data["msg_var"].get(),
                    }
                )

        if not selected_groups:
            print("⚠️ 메시지를 보낼 그룹을 먼저 선택해 주세요!")
            return

        print("=" * 40)
        print("💬 다음 그룹으로 IM 메시지 전송을 시도합니다:")
        for g in selected_groups:
            print(f" - {g['name']} (ID: {g['id']})")
        print("=" * 40)

        # TODO: adb_logic.send_message(self.current_uuid, selected_groups) 호출

    def open_unit_test_popup(self):
        """상단 단위 테스트 버튼 클릭 시 나타나는 팝업창"""
        popup = ctk.CTkToplevel(self)
        popup.title("단위 테스트 시나리오")
        popup.geometry("300x450")
        popup.attributes("-topmost", True)  # 메인 창보다 항상 위에 표시

        # 스크롤 가능한 프레임
        scroll_frame = ctk.CTkScrollableFrame(popup, fg_color="transparent")
        scroll_frame.pack(expand=True, fill="both", padx=15, pady=15)

        menu_data = {
            "📞 Group Call": ["ReGroup", "PreArranged", "Chat Group"],
            "👤 Private Call": ["Private PTT", "Private PTV", "MCVideo Push"],
            "💬 IM Message": ["일반 메시지", "사진 첨부", "동영상", "기타문서"],
        }

        # 메뉴 데이터 출력
        for category, items in menu_data.items():
            ctk.CTkLabel(
                scroll_frame,
                text=category,
                font=("Noto Sans KR", 13, "bold"),
                text_color=self.point_blue,
            ).pack(fill="x", pady=(15, 5), anchor="w")

            for item in items:
                btn = ctk.CTkButton(
                    scroll_frame,
                    text=f"  {item}",
                    font=("Noto Sans KR", 12),
                    fg_color=self.btn_bg_light,
                    text_color=self.text_main,
                    hover_color=self.btn_hover_light,
                    anchor="w",
                    height=34,
                    corner_radius=6,
                    command=lambda c=category, i=item: self.execute_action(c, i),
                )
                btn.pack(fill="x", pady=3)

    def switch_tab(self, tab_name):
        if tab_name == "group":
            # 1. 탭 버튼 색상 변경
            self.btn_tab_group.configure(fg_color=self.point_blue, text_color="white")
            self.btn_tab_user.configure(fg_color="#E2E8F0", text_color="#475569")

            # 2. 화면 전환: 유저는 숨기고, 그룹은 보여줌
            self.user_list_frame.pack_forget()
            self.group_list_frame.pack(expand=True, fill="both", padx=5, pady=5)

        else:
            # 1. 탭 버튼 색상 변경
            self.btn_tab_user.configure(fg_color=self.point_blue, text_color="white")
            self.btn_tab_group.configure(fg_color="#E2E8F0", text_color="#475569")

            # 2. 화면 전환: 그룹은 숨기고, 유저는 보여줌
            self.group_list_frame.pack_forget()
            self.user_list_frame.pack(expand=True, fill="both", padx=5, pady=5)

    def detect_project_from_xml(self):
        """
        temp_xml 폴더 안의 파일들을 뒤져서 project_config.json에 등록된
        키워드(PTA.R, CTB.R 등)가 있는지 자동으로 판별하고 project_name을 반환하는 함수
        """
        import os
        import json

        config_file = "project_config.json"
        xml_dir = "temp_xml"

        if not os.path.exists(config_file) or not os.path.exists(xml_dir):
            return "알 수 없는 프로젝트"

        # 1. project_config.json 읽기
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        # 2. temp_xml 폴더 안의 모든 파일 내용 검사
        for root_dir, _, files in os.walk(xml_dir):
            for file in files:
                if file.endswith(".xml"):
                    file_path = os.path.join(root_dir, file)
                    try:
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            content = f.read()

                            # JSON에 등록된 프로젝트 키워드가 파일 내용에 들어있는지 확인
                            for proj in config_data.get("projects", []):
                                if proj["keyword"] in content:
                                    print(
                                        f"🎯 단말기 데이터에서 키워드 [{proj['keyword']}] 포착 -> 프로젝트: {proj['project_name']}"
                                    )
                                    return proj[
                                        "project_name"
                                    ]  # 매칭되는 프로젝트명 즉시 반환!
                    except Exception as e:
                        print(f"파일 분석 중 오류 (무시함): {e}")

        return config_data.get("default", "알 수 없는 프로젝트")

    # def get_db_config_by_project(self, current_project_name):
    #     """
    #     project_config.json을 읽어서 현재 프로젝트에 맞는 DB 정보를 가져오는 함수
    #     """
    #     config_file = "project_config.json"
    #     if not os.path.exists(config_file):
    #         print("❌ project_config.json 파일이 없습니다.")
    #         return None

    #     with open(config_file, "r", encoding="utf-8") as f:
    #         config_data = json.load(f)

    #     for proj in config_data.get("projects", []):
    #         if proj.get("project_name") == current_project_name:
    #             return proj.get("db_config")

    #     print(f"❌ {current_project_name}에 해당하는 DB 설정이 JSON에 없습니다.")
    #     return None

    def refresh_user_list(self):
        """
        [DB 접속 대신 XML 탐색으로 변경됨]
        User List 갱신 및 체크박스 선택 시 액션 버튼 표시
        """
        if not self.current_uuid:
            print("❌ 연결된 단말기가 없어 유저 목록을 갱신할 수 없습니다.")
            return

        # 1. 단말기에서 XML 폴더 경로 가져오기
        path = FileManager.pull_profile_xml(self.current_uuid)
        if not path or not os.path.exists(path):
            return

        xml_folder_path = os.path.dirname(os.path.abspath(path))

        # 2. DB 대신 XML 폴더를 스캔해서 유저 목록 싹쓸이!
        users = FileManager.get_all_users_from_xml(xml_folder_path)

        # 3. 006으로 시작하는 유저만 필터링 (기존 로직 유지)
        my_group_code = "006"
        filtered_users = [
            u for u in users if str(u.get("name", "")).startswith(my_group_code)
        ]

        print(
            f"👥 [유저 목록 갱신] 총 {len(filtered_users)}명의 006 유저를 찾았습니다."
        )

        # ==========================================
        # 🎨 UI 그리기 시작
        # ==========================================
        for widget in self.user_list_frame.winfo_children():
            widget.destroy()

        self.user_checkbox_vars = {}
        self.user_ui_registry = {}  # 액션 로우 관리를 위한 레지스트리

        for user in filtered_users:
            u_name = user.get("name", "")
            d_name = user.get("display_name", "이름 없음")

            # 1. 카드 생성
            user_card = ctk.CTkFrame(
                self.user_list_frame, fg_color="#F1F5F9", corner_radius=6
            )
            user_card.pack(fill="x", padx=5, pady=2)

            # 2. 체크박스 변수 및 체크박스 생성
            chk_var = ctk.StringVar(value="off")
            self.user_checkbox_vars[u_name] = chk_var

            chk = ctk.CTkCheckBox(
                user_card,
                text=f"👤 {d_name} ({u_name})",
                font=("Noto Sans KR", 12, "bold"),
                text_color="#334155",
                variable=chk_var,
                onvalue="on",
                offvalue="off",
                # 💡 [여기에 추가!] 테두리 굵기와 색상 조정
                border_width=2,  # 굵기를 1 또는 2로 줄임 (기본값: 3)
                border_color="#94A3B8",  # 연한 회색으로 지정하면 더 깔끔합니다
                command=self.update_user_action_frame,
            )
            chk.pack(anchor="w", padx=10, pady=8)

            # 3. 액션 로우 생성 (기본적으로는 숨김)
            action_row = ctk.CTkFrame(user_card, fg_color="transparent")

            # [세그먼트 버튼] 동일한 스타일 적용
            seg_call = ctk.CTkSegmentedButton(
                action_row,
                values=["🔊 PTT", "📹 PTV", "🚨 E-PTT", "🚨 E-PTV"],
                height=32,
                font=("Noto Sans KR", 11, "bold"),
                fg_color="#F1F5F9",
                selected_color="#2563EB",
                unselected_color="#E2E8F0",
                text_color="#64748B",
            )
            seg_call.pack(fill="x", padx=10, pady=(0, 5))

            seg_msg = ctk.CTkSegmentedButton(
                action_row,
                values=["📄 Text", "🖼️ Photo", "🎥 Video"],
                height=32,
                font=("Noto Sans KR", 11, "bold"),
                fg_color="#F1F5F9",
                selected_color="#2563EB",
                unselected_color="#E2E8F0",
                text_color="#64748B",
            )
            seg_msg.pack(fill="x", padx=10, pady=(0, 10))

            # 4. 레지스트리에 저장 (나중에 토글할 때 필요)
            self.user_ui_registry[u_name] = {
                "checkbox_var": chk_var,
                "action_row": action_row,
            }

    def update_user_action_frame(self):
        """
        체크박스 상태에 따라 액션 버튼 구역(action_row)의 표시 여부를 결정합니다.
        """
        for u_name, ui_data in self.user_ui_registry.items():
            var = ui_data["checkbox_var"]
            row = ui_data["action_row"]

            if var.get() == "on":
                # 체크됨: 액션 로우 보여주기
                row.pack(fill="x", padx=0, pady=(0, 5))
            else:
                # 체크 해제됨: 액션 로우 숨기기
                row.pack_forget()

    def refresh_all_lists(self):
        """그룹 리스트와 유저 리스트를 새로고침합니다."""
        # 1. Group List는 무조건 갱신
        self.refresh_group_list() 

        # ==========================================
        # 💡 [핵심 차단 로직 2] 허가증(has_private_call) 검사 후 유저 로딩
        # ==========================================
        if getattr(self, "has_private_call", False):
            # 허가증이 있을 때만 서버/단말기에서 1000명 리스트를 가져옴
            self.refresh_user_list()
        else:
            print("🚫 Private Call 미지원 프로젝트: 유저 데이터 로딩 스킵 (서버 부하 방지)")
            
            # 유저 리스트 프레임 비우기
            for widget in self.user_list_frame.winfo_children():
                widget.destroy()
                
            # 빈 화면 대신 친절한 안내 문구 표시
            ctk.CTkLabel(
                self.user_list_frame,
                text="이 프로젝트는 1:1 통화를 지원하지 않으므로\n유저 목록을 불러오지 않습니다.",
                text_color=self.text_sub,
                font=("Noto Sans KR", 13)
            ).pack(expand=True, pady=50)

    def get_checked_users(self):
        """나중에 버튼(PTT 등) 눌렀을 때, 진짜로 선택된 유저 명단 가져오는 유틸 함수"""
        return [
            u_id for u_id, var in self.user_checkbox_vars.items() if var.get() == "on"
        ]
