import customtkinter as ctk
import tkinter as tk
import adb_logic
import os
import sys
import datetime
import json
import time
import subprocess
import importlib
import threading
import random
import math
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
        self.title("MCX QA Automation Dashboard")
        self.geometry("1600x900")

        # ==========================================
        # 🎨 [Jira & Modern SaaS Palette]
        # ==========================================
        self.bg_color = "#F4F5F7"  # Jira 차분한 쿨그레이 배경
        self.panel_bg = "#FFFFFF"  # 깔끔한 화이트 카드 패널
        self.border_color = "#DFE1E6"  # 은은하고 세련된 테두리선

        self.text_main = "#172B4D"  # Atlassian 딥 네이비
        self.text_sub = "#5E6C84"  # 슬레이트 그레이 (서브 텍스트)

        self.point_blue = "#0052CC"  # Jira 상징 메인 블루
        self.point_pink = "#DE350B"  # 경고/중지 레드
        self.point_green = "#00875A"  # 성공/연결 다크 그린
        self.danger_color = "#DE350B"

        self.btn_bg_light = "#EBECF0"  # 은은한 라이트 그레이 버튼
        self.btn_hover_light = "#C1C7D0"

        self.configure(fg_color=self.bg_color)
        self.current_uuid = None
        self.radius = 6  # SaaS 스타일에 맞게 라운딩을 살짝 줄여 sharp하게 변경
        self.is_log_on = False
        self.is_pcap_on = False
        self.is_device_pcap_on = False
        self.project_name = "알 수 없는 프로젝트"

        self._build_ui()

    def _build_ui(self):
        # ------------------------------------------
        # 🗂️ [STRUCTURE] Left Sidebar (Control) + Right Main Workspace (Dashboard)
        # ------------------------------------------

        # 1. 좌측 사이드바 (기기 정보 및 제어 전용 패널)
        self.left_panel = ctk.CTkFrame(
            self,
            width=280,
            fg_color=self.panel_bg,
            corner_radius=0,
            border_width=1,
            border_color=self.border_color,
        )
        self.left_panel.pack(side="left", fill="y")
        self.left_panel.pack_propagate(False)

        # 우측 전체를 감싸는 래퍼
        self.main_wrapper = ctk.CTkFrame(self, fg_color="transparent")
        self.main_wrapper.pack(side="left", fill="both", expand=True, padx=15, pady=15)

        # 2. 상단 상태 바 (글로벌 뱃지 영역)
        self.center_panel = ctk.CTkFrame(
            self.main_wrapper,
            height=50,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        self.center_panel.pack(side="top", fill="x", pady=(0, 12))
        self.center_panel.pack_propagate(False)

        # 3. 메인 하단 워크스페이스 (🔥 레이아웃 대공사: 미러링+SIP 아래에 결과창 배치)
        self.right_panel = ctk.CTkFrame(self.main_wrapper, fg_color="transparent")
        self.right_panel.pack(side="top", fill="both", expand=True)
        self.right_panel.grid_columnconfigure(0, weight=2)  # 20%: Lists
        self.right_panel.grid_columnconfigure(1, weight=3)  # 30%: Mirroring
        self.right_panel.grid_columnconfigure(2, weight=5)  # 50%: Pulse + SIP
        # 위/아래 비율 나누기 (결과 카드를 아래에 넣기 위함)
        self.right_panel.grid_rowconfigure(0, weight=7)  # 70%: 상단 (미러링, SIP)
        self.right_panel.grid_rowconfigure(1, weight=3)  # 30%: 하단 (통화 결과)

        # ==========================================
        # 📱 [LEFT SIDEBAR] - 기기 세팅 및 앱 제어 존
        # ==========================================
        ctk.CTkLabel(
            self.left_panel,
            text="Device Setup",
            font=("Noto Sans KR", 14, "bold"),
            text_color=self.text_main,
        ).pack(pady=(20, 4), padx=15, anchor="w")
        self.lbl_project = ctk.CTkLabel(
            self.left_panel,
            text="프로젝트: 대기 중",
            font=("Noto Sans KR", 12, "bold"),
            text_color=self.point_blue,
        )
        self.lbl_project.pack(padx=15, anchor="w")
        self.label = ctk.CTkLabel(
            self.left_panel,
            text="단말을 연결해주세요.",
            font=("Noto Sans KR", 11),
            text_color=self.text_sub,
        )
        self.label.pack(pady=(0, 12), padx=15, anchor="w")

        self.btn_connect = ctk.CTkButton(
            self.left_panel,
            text="🟢 기기 연결 및 로드",
            font=("Noto Sans KR", 12, "bold"),
            fg_color=self.point_green,
            hover_color="#006644",
            height=38,
            corner_radius=self.radius,
            command=self.check_device,
        )
        self.btn_connect.pack(padx=15, fill="x")

        self.info_frame = ctk.CTkFrame(
            self.left_panel,
            fg_color="#F4F5F7",
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        self.info_frame.pack(fill="x", padx=15, pady=12)
        info_font, info_pad = ("Noto Sans KR", 11), 3

        self.lbl_model = ctk.CTkLabel(
            self.info_frame, text="모델: -", font=info_font, text_color=self.text_main
        )
        self.lbl_model.pack(pady=(10, info_pad), padx=12, anchor="w")
        self.lbl_hw_version = ctk.CTkLabel(
            self.info_frame,
            text="HW 버전: -",
            font=info_font,
            text_color=self.text_main,
        )
        self.lbl_hw_version.pack(pady=info_pad, padx=12, anchor="w")
        self.lbl_android_ver = ctk.CTkLabel(
            self.info_frame,
            text="Android 버전: -",
            font=info_font,
            text_color=self.text_main,
        )
        self.lbl_android_ver.pack(pady=info_pad, padx=12, anchor="w")
        self.lbl_os_build = ctk.CTkLabel(
            self.info_frame,
            text="OS 버전: -",
            font=info_font,
            text_color=self.text_main,
        )
        self.lbl_os_build.pack(pady=info_pad, padx=12, anchor="w")
        self.lbl_version = ctk.CTkLabel(
            self.info_frame,
            text="앱 버전: -",
            font=info_font,
            text_color=self.text_main,
        )
        self.lbl_version.pack(pady=info_pad, padx=12, anchor="w")
        self.lbl_network = ctk.CTkLabel(
            self.info_frame,
            text="📶 네트워크: -",
            font=info_font,
            text_color=self.text_main,
        )
        self.lbl_network.pack(pady=(info_pad, 10), padx=12, anchor="w")

        ctk.CTkFrame(self.left_panel, height=1, fg_color=self.border_color).pack(
            fill="x", padx=15, pady=4
        )

        ctk.CTkLabel(
            self.left_panel,
            text="Configuration",
            font=("Noto Sans KR", 12, "bold"),
            text_color=self.text_main,
        ).pack(pady=(8, 6), padx=15, anchor="w")
        row_config = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        row_config.pack(fill="x", padx=15, pady=2)
        row_config.grid_columnconfigure(0, weight=1)
        row_config.grid_columnconfigure(1, weight=1)
        self.btn_env = ctk.CTkButton(
            row_config,
            text="⚙️ 환경 설정",
            font=("Noto Sans KR", 11),
            fg_color=self.panel_bg,
            border_width=1,
            border_color=self.border_color,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            height=32,
            corner_radius=self.radius,
            command=self.open_env_setup,
        )
        self.btn_env.grid(row=0, column=0, padx=(0, 3), sticky="ew")
        self.btn_wifi = ctk.CTkButton(
            row_config,
            text="📶 WiFi 설정",
            font=("Noto Sans KR", 11),
            fg_color=self.panel_bg,
            border_width=1,
            border_color=self.border_color,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            height=32,
            corner_radius=self.radius,
            command=self.open_wifi_setup,
        )
        self.btn_wifi.grid(row=0, column=1, padx=(3, 0), sticky="ew")

        ctk.CTkLabel(
            self.left_panel,
            text="App Management",
            font=("Noto Sans KR", 12, "bold"),
            text_color=self.text_main,
        ).pack(pady=(12, 6), padx=15, anchor="w")
        self.btn_install = ctk.CTkButton(
            self.left_panel,
            text="📦 앱 설치 (.apk)",
            font=("Noto Sans KR", 11),
            fg_color=self.btn_bg_light,
            border_width=1,
            border_color=self.border_color,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            height=32,
            corner_radius=self.radius,
            command=self.run_install_app,
        )
        self.btn_install.pack(fill="x", padx=15, pady=(0, 6))

        row_app = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        row_app.pack(fill="x", padx=15, pady=0)
        row_app.grid_columnconfigure(0, weight=1)
        row_app.grid_columnconfigure(1, weight=1)
        self.btn_clear_data = ctk.CTkButton(
            row_app,
            text="🧹 데이터 삭제",
            font=("Noto Sans KR", 11),
            fg_color=self.btn_bg_light,
            border_width=1,
            border_color=self.border_color,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            height=32,
            corner_radius=self.radius,
            command=self.run_clear_data,
        )
        self.btn_clear_data.grid(row=0, column=0, padx=(0, 3), sticky="ew")
        self.btn_uninstall = ctk.CTkButton(
            row_app,
            text="🗑️ 앱 삭제",
            font=("Noto Sans KR", 11),
            fg_color="#FFEBE6",
            text_color=self.danger_color,
            hover_color="#FFBDAD",
            height=32,
            corner_radius=self.radius,
            command=self.run_uninstall_app,
        )
        self.btn_uninstall.grid(row=0, column=1, padx=(3, 0), sticky="ew")

        # Top Banner Features
        self.feature_card = ctk.CTkFrame(self.center_panel, fg_color="transparent")
        self.feature_card.pack(fill="both", expand=True, padx=15)
        self.feature_tag_frame = ctk.CTkFrame(self.feature_card, fg_color="transparent")
        self.feature_tag_frame.pack(side="left", fill="y", pady=5)

        # ==========================================
        # 📋 [COLUMN 1 (20%)] Lists (그룹/유저 목록) 존
        # ==========================================
        col_list = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        col_list.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        self.list_container = ctk.CTkFrame(
            col_list,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        self.list_container.pack(fill="both", expand=True)

        list_header = ctk.CTkFrame(self.list_container, fg_color="transparent")
        list_header.pack(fill="x", padx=12, pady=(12, 8))

        self.btn_refresh = ctk.CTkButton(
            list_header,
            text="🔄",
            width=34,
            height=34,
            corner_radius=6,
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            command=self.refresh_all_lists,
        )
        self.btn_refresh.pack(side="right", padx=(8, 0))

        self.btn_tab_group = ctk.CTkButton(
            list_header,
            text="Group List",
            font=("Noto Sans KR", 11, "bold"),
            height=34,
            corner_radius=6,
            fg_color=self.point_blue,
            text_color="white",
            command=lambda: self.switch_tab("group"),
        )
        self.btn_tab_group.pack(side="left", expand=True, fill="x", padx=(0, 2))

        self.btn_tab_user = ctk.CTkButton(
            list_header,
            text="User List",
            font=("Noto Sans KR", 11, "bold"),
            height=34,
            corner_radius=6,
            fg_color=self.btn_bg_light,
            text_color=self.text_sub,
            hover_color=self.btn_hover_light,
            command=lambda: self.switch_tab("user"),
        )
        self.btn_tab_user.pack(side="left", expand=True, fill="x", padx=(2, 0))

        self.current_mode = "call"

        mode_toggle_frame = ctk.CTkFrame(self.list_container, fg_color="transparent")
        mode_toggle_frame.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(
            mode_toggle_frame,
            text="테스트 모드:",
            font=("Noto Sans KR", 11),
            text_color=self.text_sub,
        ).pack(side="left", padx=(0, 8))
        self.seg_mode_toggle = ctk.CTkSegmentedButton(
            mode_toggle_frame,
            values=["📞 통화", "💬 메시지"],
            height=30,
            font=("Noto Sans KR", 11, "bold"),
            selected_color=self.point_blue,
            command=self.on_mode_toggle_changed,
        )
        self.seg_mode_toggle.set("📞 통화")
        self.seg_mode_toggle.pack(side="left", fill="x", expand=True)

        self.all_cards = []
        self.group_list_frame = ctk.CTkScrollableFrame(
            self.list_container, fg_color="transparent"
        )
        self.group_list_frame.pack(expand=True, fill="both", padx=8, pady=4)
        self.user_list_frame = ctk.CTkScrollableFrame(
            self.list_container, fg_color="transparent"
        )

        btn_action_frame = ctk.CTkFrame(self.list_container, fg_color="transparent")
        btn_action_frame.pack(side="bottom", fill="x", padx=12, pady=(4, 12))

        self.my_id_label = ctk.CTkLabel(
            btn_action_frame,
            text="내 정보: 연결 대기",
            font=("Noto Sans KR", 11, "bold"),
            text_color=self.point_blue,
        )
        self.my_id_label.pack(fill="x", pady=(0, 6))

        self.btn_group_call = ctk.CTkButton(
            btn_action_frame,
            text="📞 통화 발신",
            font=("Noto Sans KR", 12, "bold"),
            fg_color=self.point_green,
            hover_color="#006644",
            height=40,
            corner_radius=self.radius,
            command=self.on_main_call_button_clicked,
        )
        self.btn_group_call.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_group_msg = ctk.CTkButton(
            btn_action_frame,
            text="💬 메시지 전송",
            font=("Noto Sans KR", 12, "bold"),
            fg_color=self.point_blue,
            hover_color="#0047B3",
            height=40,
            corner_radius=self.radius,
            command=self.send_group_message,
        )
        self.btn_group_msg.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # 📋 Group List 카드 하단: 시나리오 실행 제어 버튼
        scenario_ctrl_frame = ctk.CTkFrame(col_list, fg_color="transparent")
        scenario_ctrl_frame.pack(side="bottom", fill="x", pady=(12, 0))

        self.btn_run_scenario = ctk.CTkButton(
            scenario_ctrl_frame,
            text="▶ 전체 시나리오 실행",
            font=("Noto Sans KR", 13, "bold"),
            fg_color=self.point_blue,
            hover_color="#0047B3",
            height=42,
            corner_radius=self.radius,
            command=self.run_automation,
        )
        self.btn_run_scenario.pack(fill="x", pady=(0, 6))

        row_ctrl = ctk.CTkFrame(scenario_ctrl_frame, fg_color="transparent")
        row_ctrl.pack(fill="x")
        row_ctrl.grid_columnconfigure(0, weight=1)
        row_ctrl.grid_columnconfigure(1, weight=1)

        self.btn_stop_scenario = ctk.CTkButton(
            row_ctrl,
            text="⏹ 중지",
            font=("Noto Sans KR", 12, "bold"),
            fg_color="#FFEBE6",
            text_color=self.danger_color,
            hover_color="#FFBDAD",
            height=36,
            corner_radius=self.radius,
            command=self.stop_automation,
        )
        self.btn_stop_scenario.grid(row=0, column=0, padx=(0, 3), sticky="ew")

        self.btn_unit_test = ctk.CTkButton(
            row_ctrl,
            text="단위 테스트",
            font=("Noto Sans KR", 12, "bold"),
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            height=36,
            corner_radius=self.radius,
            command=self.open_unit_test_popup,
        )
        self.btn_unit_test.grid(row=0, column=1, padx=(3, 0), sticky="ew")

        # ==========================================
        # 📱 [COLUMN 2 (30%)] Mirroring 존 (버튼 튀어나감 완벽 방어)
        # ==========================================
        col_preview = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        col_preview.grid(row=0, column=1, sticky="nsew", padx=(0, 12))

        preview_bg = ctk.CTkFrame(
            col_preview,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        preview_bg.pack(fill="both", expand=True)

        phone_width = 300
        phone_height = 470

        # 🔥 철통 방어 구역: 폭과 높이를 명시하고 pack_propagate(False)로 내부 요소 팽창 차단
        phone_box = ctk.CTkFrame(
            preview_bg, fg_color="transparent", width=phone_width, height=570
        )
        phone_box.pack(expand=True, pady=(12, 8))
        phone_box.pack_propagate(False)

        # 버튼 폭을 강제로 줄여서(width=10) Grid 안에서만 크기가 결정되도록 유도
        btn_kwargs = {
            "width": 10,
            "height": 30,
            "corner_radius": 4,
            "fg_color": self.btn_bg_light,
            "text_color": self.text_main,
            "hover_color": self.btn_hover_light,
            "font": ("Noto Sans KR", 11),
        }

        # 📱 1. 캡쳐/촬영 (상단 버튼)
        top_nav_bar = ctk.CTkFrame(phone_box, fg_color="transparent")
        top_nav_bar.pack(fill="x", pady=(0, 5))
        top_nav_bar.grid_columnconfigure((0, 1), weight=1)

        record_cmd = getattr(
            self, "record_screen", lambda: print("🎥 동영상 촬영 기능 준비 중")
        )
        ctk.CTkButton(
            top_nav_bar, text="📸 캡쳐", command=self.capture_screen, **btn_kwargs
        ).grid(row=0, column=0, padx=1, sticky="ew")
        ctk.CTkButton(
            top_nav_bar, text="🎥 촬영", command=record_cmd, **btn_kwargs
        ).grid(row=0, column=1, padx=1, sticky="ew")

        # 📱 2. 미러링 화면 컨테이너 (고정)
        self.mirror_container = tk.Frame(
            phone_box, bg="#091E42", width=phone_width, height=phone_height
        )
        self.mirror_container.pack(pady=(0, 5))
        self.mirror_container.pack_propagate(False)
        self.lbl_placeholder = ctk.CTkLabel(
            self.mirror_container,
            text="대기 중",
            font=("Noto Sans KR", 11),
            text_color="#7A869A",
        )
        self.lbl_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # 📱 3. 하단 네비게이션 (하단 버튼)
        bottom_nav_bar = ctk.CTkFrame(phone_box, fg_color="transparent")
        bottom_nav_bar.pack(fill="x")
        bottom_nav_bar.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            bottom_nav_bar,
            text="🔙",
            command=lambda: self.send_adb_keyevent(4),
            **btn_kwargs,
        ).grid(row=0, column=0, padx=1, sticky="ew")
        ctk.CTkButton(
            bottom_nav_bar,
            text="🏠",
            command=lambda: self.send_adb_keyevent(3),
            **btn_kwargs,
        ).grid(row=0, column=1, padx=1, sticky="ew")
        ctk.CTkButton(
            bottom_nav_bar,
            text="🗂️",
            command=lambda: self.send_adb_keyevent(187),
            **btn_kwargs,
        ).grid(row=0, column=2, padx=1, sticky="ew")

        # ==========================================
        # 📈 [COLUMN 3 (50%)] Pulse + Logs 모니터링 존
        # ==========================================
        monitor_container = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        # 🔥 rowspan=2: 통화 결과 카드가 미러링 아래로만 옮겨간 만큼, SIP Flow 쪽은 아래 행까지 세로로 확장
        monitor_container.grid(row=0, column=2, rowspan=2, sticky="nsew")

        self.pulse_frame = ctk.CTkFrame(
            monitor_container, height=120, fg_color="#091E42", corner_radius=self.radius
        )
        self.pulse_frame.pack(side="top", fill="x", pady=(0, 12))
        self.pulse_frame.pack_propagate(False)

        pulse_header = ctk.CTkFrame(self.pulse_frame, height=32, fg_color="transparent")
        pulse_header.pack(fill="x", padx=15, pady=(8, 0))
        ctk.CTkLabel(
            pulse_header,
            text="🎙️ PTT Floor State",
            font=("Noto Sans KR", 12, "bold"),
            text_color="#8993A4",
        ).pack(side="left")
        self.lbl_pulse_status = ctk.CTkLabel(
            pulse_header,
            text="대기",
            font=("Noto Sans KR", 11, "bold"),
            text_color="#5E6C84",
        )
        self.lbl_pulse_status.pack(side="right")

        self.pulse_canvas = tk.Canvas(
            self.pulse_frame, bg="#091E42", highlightthickness=0
        )
        self.pulse_canvas.pack(expand=True, fill="both", padx=15, pady=(0, 8))

        monitor_top = ctk.CTkFrame(
            monitor_container,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        monitor_top.pack(fill="both", expand=True)

        monitor_header = ctk.CTkFrame(monitor_top, height=45, fg_color="transparent")
        monitor_header.pack(fill="x", padx=15, pady=(12, 4))
        ctk.CTkLabel(
            monitor_header,
            text="Network & System Logs",
            font=("Noto Sans KR", 14, "bold"),
            text_color=self.text_main,
        ).pack(side="left")

        self.btn_toggle_pcap = ctk.CTkButton(
            monitor_header,
            text="🔴 PCAP ON",
            font=("Noto Sans KR", 11, "bold"),
            fg_color="#FFEBE6",
            text_color=self.danger_color,
            hover_color="#FFBDAD",
            width=90,
            height=30,
            corner_radius=6,
            command=self.toggle_pcap,
        )
        self.btn_toggle_pcap.pack(side="right", padx=(8, 0))
        self.btn_toggle_log = ctk.CTkButton(
            monitor_header,
            text="📝 Logcat ON",
            font=("Noto Sans KR", 11, "bold"),
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            width=90,
            height=30,
            corner_radius=6,
            command=self.toggle_log,
        )
        self.btn_toggle_log.pack(side="right")

        self.tab_view = ctk.CTkTabview(
            monitor_top,
            fg_color="transparent",
            segmented_button_selected_color=self.point_blue,
            segmented_button_selected_hover_color="#0047B3",
            segmented_button_unselected_color=self.btn_bg_light,
            segmented_button_unselected_hover_color=self.btn_hover_light,
            text_color=self.text_main,
        )
        self.tab_view.pack(expand=True, fill="both", padx=15, pady=(0, 15))
        self.tab_view.add("SIP Flow")
        self.tab_view.add("System Log")

        self.flow_scroll = ctk.CTkScrollableFrame(
            self.tab_view.tab("SIP Flow"), fg_color="transparent"
        )
        self.flow_scroll.pack(expand=True, fill="both", padx=4, pady=4)

        def add_flow_card(event_type, title, detail, is_error=False):
            def update_ui():
                if is_error:
                    b_color, bg_col, icon = self.danger_color, "#FFEBE6", "🚨 ERROR"
                elif event_type == "RX":
                    b_color, bg_col, icon = self.point_green, "#E6F4EA", "📥 RECV "
                else:
                    b_color, bg_col, icon = self.point_blue, self.panel_bg, "⚙️ PROC "

                card = ctk.CTkFrame(
                    self.flow_scroll,
                    fg_color=bg_col,
                    corner_radius=6,
                    border_width=1,
                    border_color=b_color,
                )
                card.pack(fill="x", padx=4, pady=3)
                ctk.CTkLabel(
                    card,
                    text=f"{icon} | {title}",
                    font=("Noto Sans KR", 12, "bold"),
                    text_color=b_color,
                ).pack(side="left", padx=12, pady=8)
                ctk.CTkLabel(
                    card,
                    text=detail,
                    font=("Noto Sans KR", 11),
                    text_color=self.danger_color if is_error else self.text_sub,
                ).pack(side="left", padx=(4, 12))
                self.flow_scroll._parent_canvas.yview_moveto(1.0)

            self.after(0, update_ui)

        self.add_flow_card = add_flow_card
        self.lbl_sip_placeholder = ctk.CTkLabel(
            self.flow_scroll,
            text="단말을 연결하면 실시간 SIP/Call Flow가 이곳에 표시됩니다.",
            font=("Noto Sans KR", 12),
            text_color=self.text_sub,
        )
        self.lbl_sip_placeholder.pack(pady=20)

        self.entry_search = ctk.CTkEntry(
            self.tab_view.tab("System Log"),
            placeholder_text="🔍 터미널 로그 실시간 검색",
            height=36,
            corner_radius=6,
            fg_color="#FFFFFF",
            border_color=self.border_color,
        )
        self.entry_search.pack(fill="x", pady=(0, 8))
        self.txt_log = ctk.CTkTextbox(
            self.tab_view.tab("System Log"),
            font=("Noto Sans KR", 11),
            fg_color=self.bg_color,
            text_color=self.text_main,
            border_width=1,
            border_color=self.border_color,
            corner_radius=6,
        )
        self.txt_log.pack(expand=True, fill="both")
        self.txt_log.insert("1.0", "[Terminal] 시스템 로그 출력을 대기 중입니다...\n")

        # ==========================================
        # 🎯 [BOTTOM ROW] 통화 결과 (미러링 화면 바로 아래에만 배치)
        # ==========================================
        monitor_bottom = ctk.CTkFrame(
            self.right_panel,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        # 🔥 Column 1(미러링) 아래에만 배치 (Column 2는 SIP Flow가 세로로 넓게 차지)
        monitor_bottom.grid(row=1, column=1, sticky="nsew", pady=(12, 0))

        result_header = ctk.CTkFrame(monitor_bottom, height=40, fg_color="transparent")
        result_header.pack(fill="x", padx=12, pady=(12, 0))
        result_header.pack_propagate(False)
        ctk.CTkLabel(
            result_header,
            text="🎯 통화 결과",
            font=("Noto Sans KR", 13, "bold"),
            text_color=self.text_main,
        ).pack(side="left")

        self.txt_result = ctk.CTkTextbox(
            monitor_bottom,
            font=("Noto Sans KR", 11, "bold"),
            fg_color=self.bg_color,
            text_color=self.text_main,
            border_width=1,
            border_color=self.border_color,
            corner_radius=6,
        )
        self.txt_result.pack(expand=True, fill="both", padx=15, pady=(8, 15))
        self.txt_result.insert("1.0", "대기 중...\n")

        self.after(500, self.init_audio_pulse)

    # ==========================================
    # 유틸리티: 스레드 안전하게 UI 업데이트 (신규 추가)
    # ==========================================
    def safe_log_insert(self, text):
        """백그라운드 스레드에서 안전하게 UI 로그를 업데이트합니다."""

        def update_ui():
            self.txt_log.insert("end", text)
            self.txt_log.see("end")

        self.after(0, update_ui)

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

            # ✅ [수정된 부분] 여기서 프로젝트 이름을 self.project_name에 확실히 저장합니다!
            self.project_name = FileManager.get_project_name(version_name)

            # (선택) HW 버전 가져오는 함수가 있다면 연결, 없다면 알 수 없음 처리
            hw_version = getattr(adb_logic, "get_hw_version", lambda x: "조회 불가")(
                self.current_uuid
            )

            # 2. UI 라벨 텍스트 업데이트
            self.label.configure(text=f"연결됨: {model}", text_color=self.point_green)

            self.lbl_model.configure(text=f"모델: {model}")
            self.lbl_hw_version.configure(text=f"HW 버전: {hw_version}")
            self.lbl_android_ver.configure(text=f"Android 버전: {android_version}")
            self.lbl_os_build.configure(text=f"OS 버전: {os_build}")
            self.lbl_version.configure(text=f"앱 버전: {version_name}")

            # ✅ [수정된 부분] 저장된 self.project_name을 UI에 표시합니다.
            self.lbl_project.configure(text=f"프로젝트: {self.project_name}")

            self.update_project_features(self.project_name)

            adb_logic.unlock_screen(self.current_uuid)

            # 3. 미러링 및 그룹 목록 새로고침 실행
            self.run_mirror()
            # self.refresh_group_list()

            # 4. 실시간 네트워크 상태 폴링 + SIP/Call Flow 로그 분석 시작
            self.start_network_monitor()
            self.start_realtime_log_analyzer()

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

            # PTT 펄스 애니메이션 정지
            if hasattr(self, "pulse_active"):
                self.set_ptt_active(False)

            # SIP/Call Flow 분석기 중단 및 카드 초기화
            self._sip_analyzer_gen = getattr(self, "_sip_analyzer_gen", 0) + 1
            old_proc = getattr(self, "_sip_log_process", None)
            if old_proc:
                try:
                    old_proc.terminate()
                except Exception:
                    pass
            for widget in self.flow_scroll.winfo_children():
                widget.destroy()
            ctk.CTkLabel(
                self.flow_scroll,
                text="단말을 연결하면 실시간 SIP/Call Flow가 이곳에 표시됩니다.",
                font=("Noto Sans KR", 12),
                text_color=self.text_sub,
            ).pack(pady=20)

    # ==========================================
    # 📶 실시간 네트워크 상태 모니터링
    # ==========================================
    def start_network_monitor(self):
        """단말이 연결되어 있는 동안 네트워크 상태를 주기적으로 폴링하여 갱신합니다."""
        self._net_monitor_gen = getattr(self, "_net_monitor_gen", 0) + 1
        gen = self._net_monitor_gen
        uuid = self.current_uuid

        def poll():
            while self._net_monitor_gen == gen and self.current_uuid == uuid:
                status = adb_logic.get_network_status(uuid)
                self.after(0, lambda s=status: self._update_network_label(s))
                time.sleep(3)

        threading.Thread(target=poll, daemon=True).start()

    def _update_network_label(self, status):
        if self.current_uuid is None:
            return
        is_down = ("끊김" in status) or ("불가" in status)
        color = self.danger_color if is_down else self.point_green
        self.lbl_network.configure(text=f"📶 네트워크: {status}", text_color=color)

    def send_adb_keyevent(self, keycode):
        """안드로이드 단말기에 ADB Keyevent를 비동기로 전송합니다."""
        # 현재 연결된 단말기의 UUID가 있으면 해당 기기로 지정, 없으면 기본 전송
        target_device = getattr(self, "current_uuid", None)

        def run():
            try:
                # cmd 명령어 구성
                if target_device:
                    cmd = [
                        "adb",
                        "-s",
                        target_device,
                        "shell",
                        "input",
                        "keyevent",
                        str(keycode),
                    ]
                else:
                    cmd = ["adb", "shell", "input", "keyevent", str(keycode)]

                # subprocess를 이용한 백그라운드 실행 (창 안 뜨게 억제)
                if os.name == "nt":  # Windows 환경
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    subprocess.run(
                        cmd, startupinfo=startupinfo, capture_output=True, text=True
                    )
                else:
                    subprocess.run(cmd, capture_output=True, text=True)

            except Exception as e:
                print(f"⚠️ ADB 명령어 전송 실패: {e}")

        # UI가 멈추지 않도록 데몬 스레드로 실행
        threading.Thread(target=run, daemon=True).start()

    # ==========================================
    # 🎙️ PTT 발언권(Floor) 연동 펄스 애니메이션
    # 상시로 돌리지 않고, 실제 Floor State 이벤트가 잡힐 때만 움직입니다.
    # ==========================================
    def init_audio_pulse(self):
        self.pulse_offset = 0
        self.pulse_active = False
        self._pulse_idle_timer = None
        self._draw_idle_pulse()

    def set_ptt_active(self, active: bool):
        """PTT 발언권 상태에 따라 펄스 애니메이션을 켜고 끕니다."""
        was_active = self.pulse_active
        self.pulse_active = active

        if active:
            self.lbl_pulse_status.configure(text="🔴 송신 중", text_color=self.danger_color)
            if not was_active:
                self.update_wave_pulse()
        else:
            self.lbl_pulse_status.configure(text="대기", text_color="#5E6C84")
            self._draw_idle_pulse()

    def _on_floor_state(self, state_text):
        """mMBCPKeyEvent(MBCP_UI_EVENT_*) 로그 문자열을 보고 발언권 보유 여부를 추정해 펄스를 연동합니다.
        실측 확인된 값은 MBCP_UI_EVENT_IDLE / MBCP_UI_EVENT_NONE 뿐이라, GRANT 계열 값은
        추정치입니다. 정확한 전체 상태값 체계를 몰라도 동작하도록, 알 수 없는 값은
        짧게 반짝이는 것으로 처리합니다."""
        if self._pulse_idle_timer is not None:
            self.after_cancel(self._pulse_idle_timer)
            self._pulse_idle_timer = None

        txt = state_text.upper()
        if any(k in txt for k in ("GRANT", "TALK", "TRANSMIT", "TX")):
            self.set_ptt_active(True)
        elif any(
            k in txt
            for k in ("IDLE", "NONE", "RELEASE", "DENY", "DENIED", "REVOKE", "STOP")
        ):
            self.set_ptt_active(False)
        else:
            # 알 수 없는 상태값: 활동이 있었다는 것만 짧게 표시하고 자동으로 대기 상태로 복귀
            self.set_ptt_active(True)
            self._pulse_idle_timer = self.after(2000, lambda: self.set_ptt_active(False))

    def _draw_idle_pulse(self):
        self.pulse_canvas.delete("all")
        width = self.pulse_canvas.winfo_width() or 400
        height = self.pulse_canvas.winfo_height() or 130
        cy = height / 2
        self.pulse_canvas.create_line(0, cy, width, cy, fill="#3A4A63", width=2)

    def update_wave_pulse(self):
        if not self.pulse_active:
            return  # 비활성화되면 애니메이션 루프를 완전히 멈춰서 부하를 없앱니다.

        self.pulse_canvas.delete("all")

        width = self.pulse_canvas.winfo_width() or 400
        height = self.pulse_canvas.winfo_height() or 130
        cy = height / 2

        points = []
        # 부드러운 곡선을 위해 촘촘하게 좌표 계산
        for x in range(0, width, 4):
            # 두 개의 사인파를 겹쳐서 불규칙하고 자연스러운 소리 파동 생성
            amp = random.uniform(0.8, 1.2) * 35
            y = cy + math.sin((x + self.pulse_offset) * 0.05) * amp * math.cos(
                (x - self.pulse_offset) * 0.02
            )
            points.extend([x, y])

        # smooth=True 옵션으로 점들을 부드러운 곡선으로 연결
        if points:
            self.pulse_canvas.create_line(
                points, fill=self.point_green, width=2.5, smooth=True
            )

        self.pulse_offset += 8  # 파동이 옆으로 흐르는 속도
        self.after(50, self.update_wave_pulse)

    def update_project_features(self, project_name):
        for widget in self.feature_tag_frame.winfo_children():
            widget.destroy()

        features = FileManager.get_project_features(project_name)
        if not features:
            self.has_private_call = False
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

        private_call_data = features.get("private_call", {})
        self.has_private_call = any(val == 1 for val in private_call_data.values())

        if self.has_private_call:
            self.btn_tab_user.configure(state="normal", text_color="#475569")
        else:
            self.btn_tab_user.configure(state="disabled", text_color="#CBD5E1")
            if getattr(self, "current_mode", "group") == "user":
                self.switch_tab("group")

        # 👇 세로 스택(Vertical)을 가로 흐름(Horizontal) 둥근 뱃지 스타일로 변경
        def create_tag_group(title, icon, category_data, name_map, bg_color, txt_color):
            active_features = [
                name_map[key]
                for key, val in category_data.items()
                if val == 1 and key in name_map
            ]
            if not active_features:
                return

            # 위아래가 아닌 '왼쪽'으로 이어붙이도록 side="left" 적용
            group_frame = ctk.CTkFrame(self.feature_tag_frame, fg_color="transparent")
            group_frame.pack(side="left", padx=(0, 20), fill="y")

            # 카테고리 타이틀 (예: 👥 Group:)
            ctk.CTkLabel(
                group_frame,
                text=f"{icon} {title}:",
                font=("Noto Sans KR", 13, "bold"),
                text_color=self.text_sub,
            ).pack(side="left", padx=(0, 8))

            # 동적 둥근 뱃지 디자인 생성
            for f_name in active_features:
                badge = ctk.CTkFrame(group_frame, fg_color=bg_color, corner_radius=12)
                badge.pack(
                    side="left", padx=3, pady=10
                )  # pady로 상단 배너 중앙 정렬 유도

                ctk.CTkLabel(
                    badge,
                    text=f_name,
                    font=("Noto Sans KR", 11, "bold"),
                    text_color=txt_color,
                ).pack(padx=10, pady=3)

        # SaaS 컬러 팔레트 적용 (블루, 민트, 레드 톤)
        create_tag_group(
            "Group",
            "👥",
            features.get("group_call", {}),
            group_map,
            bg_color="#E0E7FF",
            txt_color="#4318FF",
        )
        create_tag_group(
            "Private",
            "👤",
            private_call_data,
            private_map,
            bg_color="#DCFCE7",
            txt_color="#05CD99",
        )
        create_tag_group(
            "Message",
            "✉️",
            features.get("message", {}),
            msg_map,
            bg_color="#FFEDD5",
            txt_color="#EE5D50",
        )

    def refresh_group_list(self):
        if not self.current_uuid:
            return
        path = FileManager.pull_profile_xml(self.current_uuid)
        if not path or not os.path.exists(path):
            return
        groups = FileManager.parse_group_list(path)
        my_info = FileManager.parse_my_info(path)
        self.my_id_label.configure(text=f"내 정보: {my_info}")
        self.all_cards = []
        self.group_check_vars = {}
        for widget in self.group_list_frame.winfo_children():
            widget.destroy()

        def create_section(title, group_list):
            if not group_list:
                return
            header_frame = ctk.CTkFrame(self.group_list_frame, fg_color="transparent")
            header_frame.pack(fill="x", padx=4, pady=(10, 4))
            ctk.CTkLabel(
                header_frame,
                text=title,
                font=("Noto Sans KR", 11, "bold"),
                text_color=self.text_main,
            ).pack(side="left")
            ctk.CTkFrame(header_frame, height=1, fg_color=self.border_color).pack(
                side="left", fill="x", expand=True, padx=(8, 0)
            )

            for g_info in group_list:
                card = ctk.CTkFrame(
                    self.group_list_frame,
                    fg_color=self.panel_bg,
                    corner_radius=4,
                    border_width=1,
                    border_color=self.border_color,
                )
                card.pack(fill="x", padx=4, pady=2)
                voice, video = g_info.get("voice_codec", ""), g_info.get(
                    "video_codec", ""
                )
                codec_str = f"[🎤 {voice} | 🎬 {video}]" if voice or video else ""
                var_check = ctk.StringVar(value="off")

                top_row = ctk.CTkFrame(card, fg_color="transparent")
                top_row.pack(fill="x", padx=8, pady=8)
                chk = ctk.CTkCheckBox(
                    top_row,
                    text="",
                    width=24,
                    variable=var_check,
                    onvalue="on",
                    offvalue="off",
                    border_width=2,
                    border_color="#94A3B8",
                    fg_color=self.point_blue,
                    command=self.update_group_visibility,
                )
                chk.pack(side="left", padx=(0, 6))

                repeat_var = ctk.StringVar(value="1")
                repeat_frame = ctk.CTkFrame(top_row, fg_color="transparent")
                repeat_frame.pack(side="right", padx=(6, 0))
                ctk.CTkLabel(
                    repeat_frame,
                    text="반복",
                    font=("Noto Sans KR", 10),
                    text_color=self.text_sub,
                ).pack(side="left", padx=(0, 4))
                vcmd_repeat = (self.register(lambda s: s == "" or s.isdigit()), "%P")
                entry_repeat = ctk.CTkEntry(
                    repeat_frame,
                    textvariable=repeat_var,
                    width=40,
                    height=24,
                    justify="center",
                    validate="key",
                    validatecommand=vcmd_repeat,
                )
                entry_repeat.pack(side="left")

                def on_repeat_focus_out(event, var=repeat_var):
                    if not var.get() or var.get() == "0":
                        var.set("1")

                entry_repeat.bind("<FocusOut>", on_repeat_focus_out)

                text_frame = ctk.CTkFrame(top_row, fg_color="transparent")
                text_frame.pack(side="left", fill="both", expand=True)

                # 👇 기본 높이(height)를 확 줄이고, pack()의 pady를 조절해 위아래로 착 붙입니다.
                lbl_name = ctk.CTkLabel(
                    text_frame,
                    text=g_info["name"],
                    font=(
                        "Noto Sans KR",
                        12,
                        "bold",
                    ),  # 이름은 확실히 구분되게 12폰트/bold로
                    text_color=self.text_main,
                    height=16,  # 핵심 포인트: 투명 여백 제거
                )
                lbl_name.pack(anchor="w", pady=(4, 0))  # 위쪽만 4px 여백, 아래는 0

                lbl_id = ctk.CTkLabel(
                    text_frame,
                    text=f"ID: {g_info['id']}",
                    font=("Noto Sans KR", 11),
                    text_color=self.text_sub,
                    height=14,  # 핵심 포인트: 투명 여백 제거
                )
                lbl_id.pack(
                    anchor="w", pady=(0, 4)
                )  # 위는 0(이름과 붙임), 아래는 4px 여백

                def toggle_checkbox(event, var=var_check):
                    var.set("off" if var.get() == "on" else "on")
                    self.update_group_visibility()

                lbl_name.bind("<Button-1>", toggle_checkbox)
                lbl_id.bind("<Button-1>", toggle_checkbox)

                if codec_str:
                    ctk.CTkLabel(
                        card,
                        text=codec_str,
                        font=("Noto Sans KR", 9),
                        text_color="#94A3B8",
                    ).pack(anchor="w", padx=(34, 8), pady=(0, 4))

                action_row = ctk.CTkFrame(card, fg_color="transparent")
                seg_call = ctk.CTkSegmentedButton(
                    action_row,
                    values=["🔊 PTT", "📹 PTV", "🚨 E-PTT", "🚨 E-PTV"],
                    height=26,
                    font=("Noto Sans KR", 10),
                    selected_color=self.point_blue,
                )
                seg_msg = ctk.CTkSegmentedButton(
                    action_row,
                    values=["📄 Text", "🖼️ Photo"],
                    height=26,
                    font=("Noto Sans KR", 10),
                    selected_color=self.point_blue,
                )
                card.check_var, card.action_row, card.seg_call, card.seg_msg = (
                    var_check,
                    action_row,
                    seg_call,
                    seg_msg,
                )
                self.all_cards.append(card)
                self.group_check_vars[g_info["id"]] = {
                    "check_var": var_check,
                    "call_var": seg_call,
                    "msg_var": seg_msg,
                    "repeat_var": repeat_var,
                    "name": g_info["name"],
                }

        groups_reg = sorted(
            (g for g in groups if g.get("type") == "ReGroup"),
            key=lambda x: x.get("name", "").lower(),
        )
        groups_pre = sorted(
            (g for g in groups if g.get("type") == "PreArranged Group"),
            key=lambda x: x.get("name", "").lower(),
        )
        create_section("📁 ReGroup", groups_reg)
        create_section("📁 PreArranged", groups_pre)
        self.update_group_visibility()

    def update_group_visibility(self):
        if not hasattr(self, "current_mode") or self.current_mode is None:
            self.current_mode = "call"

        for card in self.all_cards:
            if card.check_var.get() == "off":
                card.seg_call.set("")
                card.seg_msg.set("")

            card.action_row.pack_forget()
            card.seg_call.pack_forget()
            card.seg_msg.pack_forget()

            if card.check_var.get() == "on":
                card.action_row.pack(fill="x", padx=10, pady=(0, 10))
                if self.current_mode == "call":
                    card.seg_call.pack(side="left", expand=True, fill="x", padx=(0, 10))
                else:
                    card.seg_msg.pack(side="left", expand=True, fill="x", padx=(0, 10))

    def on_mode_toggle_changed(self, selected_value):
        self.current_mode = "call" if "통화" in selected_value else "msg"
        self.update_group_visibility()
        if hasattr(self, "user_ui_registry"):
            self.update_user_action_frame()

    def on_main_call_button_clicked(self):
        if not self.current_uuid:
            self.txt_log.insert("end", "⚠️ 단말기가 연결되지 않았습니다!\n")
            return

        selected_targets = []
        for group_id, data in self.group_check_vars.items():
            if data["check_var"].get() == "on":
                raw_mode = data["call_var"].get()
                if not raw_mode:
                    self.txt_log.insert(
                        "end",
                        f"⚠️ '{data['name']}' 그룹의 통화 방식이 선택되지 않아 제외됩니다.\n",
                    )
                    self.txt_log.see("end")
                    continue

                clean_mode = raw_mode.split(" ")[-1]
                try:
                    repeat_count = int(data["repeat_var"].get())
                except (KeyError, ValueError):
                    repeat_count = 1
                repeat_count = max(1, repeat_count)
                selected_targets.append(
                    {
                        "id": group_id,
                        "name": data["name"],
                        "mode": clean_mode,
                        "repeat": repeat_count,
                    }
                )

        if not selected_targets:
            self.txt_log.insert(
                "end",
                "⚠️ 발신을 진행할 그룹이 없습니다. 체크박스와 통화 방식을 확인해주세요.\n",
            )
            self.txt_log.see("end")
            return

        proj_name = getattr(self, "project_name", "알 수 없는 프로젝트")

        # UI가 멈추지 않도록 백그라운드 쓰레드에서 실행
        threading.Thread(
            target=self._process_sequential_calls,
            args=(proj_name, selected_targets),
            daemon=True,
        ).start()

    def _process_sequential_calls(self, proj_name, selected_targets):
        # safe_log_insert를 활용하여 스레드 안전성 확보
        self.safe_log_insert(
            f"\n[System] 총 {len(selected_targets)}개 그룹에 순차 발신을 시작합니다...\n"
        )

        try:
            import uiautomator2 as u2

            d = u2.connect(self.current_uuid)

            if proj_name == "재난망":
                module_name = "config_handlers.ps_lte_handler"
                class_name = "PsLteHandler"
            elif proj_name == "재난망_LM75":
                module_name = "config_handlers.ps_lte_lm75_handler"
                class_name = "PsLteLm75Handler"
            else:
                self.safe_log_insert(
                    f"⚠️ '{proj_name}'에 대한 발신 기능이 아직 없습니다.\n"
                )
                return

            module = importlib.import_module(module_name)
            handler_class = getattr(module, class_name)
            handler_instance = handler_class()

            for idx, target in enumerate(selected_targets, 1):
                t_id = target["id"]
                t_name = target["name"]
                t_mode = target["mode"]
                t_repeat = target.get("repeat", 1)

                for rep in range(1, t_repeat + 1):
                    self.safe_log_insert(
                        f"\n▶️ [{idx}/{len(selected_targets)}] '{t_name}' ({t_mode}) 발신 진행 중... ({rep}/{t_repeat}회)\n"
                    )

                    # 주의: handler_instance 내부에서 log_console.insert()를 쓴다면 여전히 UI 충돌 가능성이 있습니다.
                    # 완벽히 하려면 handler 내에서도 after를 쓰거나 콜백을 던져주는 형태로 수정하시는 것이 좋습니다.
                    handler_instance.make_call(
                        d, target_info=t_id, call_mode=t_mode, log_console=self.txt_log
                    )

                    time.sleep(3)

            self.safe_log_insert("\n✅ 모든 순차 발신 테스트가 완료되었습니다!\n")

        except Exception as e:
            self.safe_log_insert(f"❌ 발신 프로세스 중 오류 발생: {e}\n")

    def on_group_selected(self, group_dict):
        name = group_dict["name"]
        call_id = group_dict["id"]
        print(f"선택된 그룹: {name}, ID: {call_id}")

    def run_mirror(self):
        self.lbl_placeholder.place_forget()
        self.mirror_container.update_idletasks()
        width = self.mirror_container.winfo_width()
        height = self.mirror_container.winfo_height()
        parent_hwnd = self.mirror_container.winfo_id()

        if width <= 1 or height <= 1:
            width, height = 400, 800

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
        print("✅ 앱 데이터 초기화 완료")

    def run_install_app(self):
        if not self.current_uuid:
            return
        file_path = filedialog.askopenfilename(
            title="설치할 APK 파일을 선택하세요", filetypes=[("APK files", "*.apk")]
        )
        if not file_path:
            print("사용자가 설치를 취소했습니다.")
            return

        print(f"📂 선택된 파일: {file_path}")
        try:
            print("🚀 설치 진행 중...")
            result = subprocess.run(
                ["adb", "install", "-r", file_path],
                capture_output=True,
                text=True,
                check=True,
            )
            if "Success" in result.stdout:
                print("✅ 앱 설치 성공!")
            else:
                print(f"❌ 설치 실패: {result.stderr}")
        except subprocess.CalledProcessError as e:
            print(f"🚨 설치 프로세스 오류: {e.stderr}")
        except Exception as e:
            print(f"🚨 알 수 없는 오류 발생: {e}")

    def run_uninstall_app(self):
        package_name = "com.EveryTalk.Global"
        print(f"🚀 앱 삭제 시도 중: {package_name}")
        try:
            result = subprocess.run(
                ["adb", "uninstall", package_name], capture_output=True, text=True
            )
            if "Success" in result.stdout:
                print("✅ 앱 삭제 성공!")
                if hasattr(self, "lbl_version"):
                    self.lbl_version.configure(text="앱 버전: 삭제됨")
            else:
                print(f"⚠️ 결과: {result.stdout.strip()}")
                if "Failure" in result.stdout:
                    print(
                        "❌ 삭제 실패: 앱이 설치되어 있지 않거나 권한이 필요할 수 있습니다."
                    )
        except Exception as e:
            print(f"🚨 삭제 중 에러 발생: {e}")

    def open_env_setup(self):
        try:
            with open("env_config.json", "r", encoding="utf-8") as f:
                self.config_data = json.load(f)
        except FileNotFoundError:
            print("❌ 설정 파일(env_config.json)이 없습니다.")
            return

        window = ctk.CTkToplevel(self)
        window.title("⚙️ 프로젝트 환경 설정")
        window.geometry("320x240")
        window.configure(fg_color=self.panel_bg)
        window.attributes("-topmost", True)

        project_list = list(self.config_data.keys())

        ctk.CTkLabel(
            window,
            text="적용할 프로젝트를 선택하세요",
            font=("Noto Sans KR", 14, "bold"),
            text_color=self.text_main,
        ).pack(pady=(30, 15))

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
        proj_name = self.selected_project.get()
        env = self.config_data[proj_name]

        if self.current_uuid:
            self.txt_log.insert("end", "[System] 자동화 실행 중...\n")

            try:
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
                    safe_proj_name = proj_name.lower()
                    class_name = f"{proj_name.upper()}Handler"

                module_path = f"config_handlers.{safe_proj_name}_handler"
                module = importlib.import_module(module_path)
                handler_class = getattr(module, class_name)
                handler = handler_class()

                import uiautomator2 as u2

                d = u2.connect(self.current_uuid)
                handler.run(d, env)

                from common_logger import start_device_logging

                start_device_logging(d, self.txt_log)

                self.txt_log.insert("end", "[System] 완료!\n")

            except ImportError:
                print(f"❌ 모듈 로드 실패: {module_path} 모듈을 찾을 수 없습니다.")
                self.txt_log.insert(
                    "end", f"[Error] 설정 실패: 모듈을 찾을 수 없습니다.\n"
                )
            except Exception as e:
                print(f"❌ 설정 실패: {e}")
                self.txt_log.insert("end", f"[Error] 설정 실패: {e}\n")

        window.destroy()

    def open_wifi_setup(self):
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "wifi_config.json"
        )
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.wifi_data = json.load(f)
        except FileNotFoundError:
            print("❌ WiFi 설정 파일(wifi_config.json)이 없습니다.")
            return

        window = ctk.CTkToplevel(self)
        window.title("📶 WiFi 설정")
        window.geometry("320x240")
        window.configure(fg_color=self.panel_bg)
        window.attributes("-topmost", True)

        wifi_list = list(self.wifi_data.keys())
        if not wifi_list:
            wifi_list = ["목록 없음"]

        ctk.CTkLabel(
            window,
            text="접속할 WiFi를 선택하세요",
            font=("Noto Sans KR", 14, "bold"),
            text_color=self.text_main,
        ).pack(pady=(30, 15))

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
        ssid = self.selected_wifi.get()
        password = self.wifi_data.get(ssid)

        if self.current_uuid:
            self.txt_log.insert("end", f"[System] {ssid} WiFi 연결 시도 중...\n")
            self.txt_log.see("end")

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

        pictures_dir = os.path.join(os.path.expanduser("~"), "Pictures", "QA_Captures")
        os.makedirs(pictures_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        save_path = os.path.join(pictures_dir, filename)

        print("📸 캡쳐를 진행 중입니다...")
        success = adb_logic.take_screenshot(self.current_uuid, save_path)

        if success:
            print(f"✅ 캡쳐 완료! 파일이 저장되었습니다:\n{save_path}")
            try:
                os.startfile(pictures_dir)
            except Exception:
                pass
        else:
            print("❌ 캡쳐에 실패했습니다.")

    def toggle_log(self):
        if not self.is_log_on:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = os.path.join(os.getcwd(), "logs", f"log_{timestamp}.txt")

            self.log_proc, self.log_file = adb_logic.start_log_process(
                self.current_uuid, log_path
            )

            self.btn_toggle_log.configure(
                text="■ LOG OFF",
                fg_color=self.point_pink,
                text_color="#FFFFFF",
            )
            self.is_log_on = True

        else:
            adb_logic.stop_process(self.log_proc)
            self.log_file.close()

            self.btn_toggle_log.configure(
                text="▶ LOG ON",
                fg_color=self.btn_bg_light,
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

            success = adb_logic.start_pcapdroid(self.current_uuid)

            if success:
                self.btn_toggle_pcap.configure(
                    text="■ PCAPdroid OFF",
                    fg_color=self.point_pink,
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

            adb_logic.stop_pcapdroid(self.current_uuid)

            self.btn_toggle_pcap.configure(
                text="● PCAPdroid ON",
                fg_color=self.btn_bg_light,
                text_color=self.point_pink,
            )
            self.is_pcap_on = False

            self.txt_pcap.insert("end", "[System] 🛑 캡처가 중지되었습니다.\n")
            self.txt_pcap.see("end")

    def run_automation(self):
        if not self.current_uuid:
            return
        print("🚀 [자동화 시작] 시나리오를 연속 실행합니다...")

    def stop_automation(self):
        print("⏹ [자동화 중지] 시나리오를 강제 중지합니다.")

    def send_group_message(self):
        if not self.current_uuid:
            return

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
        # adb_logic.send_message(self.current_uuid, selected_groups) 호출

    def open_unit_test_popup(self):
        popup = ctk.CTkToplevel(self)
        popup.title("단위 테스트 시나리오")
        popup.geometry("300x450")
        popup.attributes("-topmost", True)

        scroll_frame = ctk.CTkScrollableFrame(popup, fg_color="transparent")
        scroll_frame.pack(expand=True, fill="both", padx=15, pady=15)

        menu_data = {
            "📞 Group Call": ["ReGroup", "PreArranged", "Chat Group"],
            "👤 Private Call": ["Private PTT", "Private PTV", "MCVideo Push"],
            "💬 IM Message": ["일반 메시지", "사진 첨부", "동영상", "기타문서"],
        }

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
            self.btn_tab_group.configure(fg_color=self.point_blue, text_color="white")
            self.btn_tab_user.configure(fg_color="#E2E8F0", text_color="#475569")
            self.user_list_frame.pack_forget()
            self.group_list_frame.pack(expand=True, fill="both", padx=5, pady=5)
        else:
            self.btn_tab_user.configure(fg_color=self.point_blue, text_color="white")
            self.btn_tab_group.configure(fg_color="#E2E8F0", text_color="#475569")
            self.group_list_frame.pack_forget()
            self.user_list_frame.pack(expand=True, fill="both", padx=5, pady=5)

    def detect_project_from_xml(self):
        config_file = "project_config.json"
        xml_dir = "temp_xml"

        if not os.path.exists(config_file) or not os.path.exists(xml_dir):
            return "알 수 없는 프로젝트"

        with open(config_file, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        for root_dir, _, files in os.walk(xml_dir):
            for file in files:
                if file.endswith(".xml"):
                    file_path = os.path.join(root_dir, file)
                    try:
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            content = f.read()
                            for proj in config_data.get("projects", []):
                                if proj["keyword"] in content:
                                    print(
                                        f"🎯 단말기 데이터에서 키워드 [{proj['keyword']}] 포착 -> 프로젝트: {proj['project_name']}"
                                    )
                                    return proj["project_name"]
                    except Exception as e:
                        print(f"파일 분석 중 오류 (무시함): {e}")

        return config_data.get("default", "알 수 없는 프로젝트")

    def refresh_user_list(self):
        if not self.current_uuid:
            print("❌ 연결된 단말기가 없어 유저 목록을 갱신할 수 없습니다.")
            return

        path = FileManager.pull_profile_xml(self.current_uuid)
        if not path or not os.path.exists(path):
            return

        xml_folder_path = os.path.dirname(os.path.abspath(path))
        users = FileManager.get_all_users_from_xml(xml_folder_path)
        my_group_code = "006"

        # 💡 [정렬 추가] Service ID (u.get("name")) 기준으로 오름차순 정렬
        filtered_users = sorted(
            [u for u in users if str(u.get("name", "")).startswith(my_group_code)],
            key=lambda x: str(x.get("name", "")),
        )

        print(
            f"👥 [유저 목록 갱신] 총 {len(filtered_users)}명의 006 유저를 찾았습니다."
        )

        for widget in self.user_list_frame.winfo_children():
            widget.destroy()

        self.user_checkbox_vars = {}
        self.user_ui_registry = {}

        for user in filtered_users:
            u_name = user.get("name", "")
            d_name = user.get("display_name", "이름 없음")

            # 그룹 리스트와 동일한 카드 테마 적용
            user_card = ctk.CTkFrame(
                self.user_list_frame,
                fg_color=self.panel_bg,
                corner_radius=4,
                border_width=1,
                border_color=self.border_color,
            )
            user_card.pack(fill="x", padx=4, pady=2)

            chk_var = ctk.StringVar(value="off")
            self.user_checkbox_vars[u_name] = chk_var

            top_row = ctk.CTkFrame(user_card, fg_color="transparent")
            top_row.pack(fill="x", padx=8, pady=4)

            # 1. 체크박스 (글자 비움)
            chk = ctk.CTkCheckBox(
                top_row,
                text="",
                width=24,
                variable=chk_var,
                onvalue="on",
                offvalue="off",
                border_width=2,
                border_color="#94A3B8",
                fg_color=self.point_blue,
                command=self.update_user_action_frame,
            )
            chk.pack(side="left", padx=(0, 6))

            # 2-1. 반복 횟수 입력란 (오른쪽 정렬)
            repeat_var = ctk.StringVar(value="1")
            repeat_frame = ctk.CTkFrame(top_row, fg_color="transparent")
            repeat_frame.pack(side="right", padx=(6, 0))
            ctk.CTkLabel(
                repeat_frame,
                text="반복",
                font=("Noto Sans KR", 10),
                text_color=self.text_sub,
            ).pack(side="left", padx=(0, 4))
            vcmd_repeat = (self.register(lambda s: s == "" or s.isdigit()), "%P")
            entry_repeat = ctk.CTkEntry(
                repeat_frame,
                textvariable=repeat_var,
                width=40,
                height=24,
                justify="center",
                validate="key",
                validatecommand=vcmd_repeat,
            )
            entry_repeat.pack(side="left")

            def on_repeat_focus_out(event, var=repeat_var):
                if not var.get() or var.get() == "0":
                    var.set("1")

            entry_repeat.bind("<FocusOut>", on_repeat_focus_out)

            # 2-2. 텍스트 프레임 (이름 & ID 상하 밀착 배치)
            text_frame = ctk.CTkFrame(top_row, fg_color="transparent")
            text_frame.pack(side="left", fill="both", expand=True)

            lbl_name = ctk.CTkLabel(
                text_frame,
                text=d_name,
                font=("Noto Sans KR", 12, "bold"),
                text_color=self.text_main,
                height=16,  # 투명 여백 제거
            )
            lbl_name.pack(anchor="w", pady=(4, 0))

            lbl_id = ctk.CTkLabel(
                text_frame,
                text=f"ID: {u_name}",
                font=("Noto Sans KR", 11),
                text_color=self.text_sub,
                height=14,  # 투명 여백 제거
            )
            lbl_id.pack(anchor="w", pady=(0, 4))

            # 3. 글씨 클릭 시 체크박스 연동
            def toggle_user_checkbox(event, var=chk_var):
                var.set("off" if var.get() == "on" else "on")
                self.update_user_action_frame()

            lbl_name.bind("<Button-1>", toggle_user_checkbox)
            lbl_id.bind("<Button-1>", toggle_user_checkbox)

            # 4. 액션 버튼 영역 (그룹 리스트처럼 숨김 처리용)
            action_row = ctk.CTkFrame(user_card, fg_color="transparent")

            seg_call = ctk.CTkSegmentedButton(
                action_row,
                values=["🔊 PTT", "📹 PTV", "🚨 E-PTT", "🚨 E-PTV"],
                height=26,
                font=("Noto Sans KR", 10),
                selected_color=self.point_blue,
            )

            seg_msg = ctk.CTkSegmentedButton(
                action_row,
                values=["📄 Text", "🖼️ Photo", "🎥 Video"],
                height=26,
                font=("Noto Sans KR", 10),
                selected_color=self.point_blue,
            )

            self.user_ui_registry[u_name] = {
                "checkbox_var": chk_var,
                "action_row": action_row,
                "seg_call": seg_call,
                "seg_msg": seg_msg,
                "repeat_var": repeat_var,
            }

    def update_user_action_frame(self):
        # 현재 모드가 없으면 기본값 세팅
        if not hasattr(self, "current_mode") or self.current_mode is None:
            self.current_mode = "call"

        for u_name, ui_data in self.user_ui_registry.items():
            var = ui_data["checkbox_var"]
            row = ui_data["action_row"]
            seg_call = ui_data["seg_call"]
            seg_msg = ui_data["seg_msg"]

            # 1) 체크가 풀렸으면 초기화 및 숨김
            if var.get() == "off":
                seg_call.set("")
                seg_msg.set("")
                row.pack_forget()
                seg_call.pack_forget()
                seg_msg.pack_forget()

            # 2) 체크되었으면 현재 모드에 따라 버튼 표시
            elif var.get() == "on":
                row.pack(fill="x", padx=8, pady=(0, 6))

                # 이전 상태 깔끔하게 지우기
                seg_call.pack_forget()
                seg_msg.pack_forget()

                # 모드에 맞게 출력
                if self.current_mode == "call":
                    seg_call.pack(fill="x", expand=True)
                else:
                    seg_msg.pack(fill="x", expand=True)

    def refresh_all_lists(self):
        self.refresh_group_list()

        if getattr(self, "has_private_call", False):
            self.refresh_user_list()
        else:
            print(
                "🚫 Private Call 미지원 프로젝트: 유저 데이터 로딩 스킵 (서버 부하 방지)"
            )
            for widget in self.user_list_frame.winfo_children():
                widget.destroy()
            ctk.CTkLabel(
                self.user_list_frame,
                text="이 프로젝트는 1:1 통화를 지원하지 않으므로\n유저 목록을 불러오지 않습니다.",
                text_color=self.text_sub,
                font=("Noto Sans KR", 13),
            ).pack(expand=True, pady=50)

    def get_checked_users(self):
        return [
            u_id for u_id, var in self.user_checkbox_vars.items() if var.get() == "on"
        ]

    # ==========================================
    # 📡 실시간 SIP/Call Flow 로그 분석
    # ==========================================
    def _emit_flow(self, key, event_type, title, detail, is_error=False, window=1.5):
        """같은 종류(key)의 이벤트가 짧은 시간 안에 같은 내용으로 반복되면 무시합니다.
        EveryTalk 앱은 같은 이벤트를 여러 UI 컴포넌트에서 각각 로깅해서 실제로
        한 번의 통화에 동일 라인이 6~8번씩 찍히는 걸 실측으로 확인했습니다.
        반환값: 실제로 새 카드를 띄웠으면 True, 중복이라 무시했으면 False."""
        now = time.time()
        last = self._flow_dedupe.get(key)
        if last and last[0] == detail and (now - last[1]) < window:
            self._flow_dedupe[key] = (detail, now)
            return False
        self._flow_dedupe[key] = (detail, now)
        self.add_flow_card(event_type, title, detail, is_error=is_error)
        return True

    def start_realtime_log_analyzer(self):
        """단말 로그를 실시간으로 스니핑하여 SIP/Call Flow 카드로 표시하는 백그라운드 스레드"""
        if not self.current_uuid:
            return

        # 기존에 돌고 있던 분석기가 있다면 종료
        old_proc = getattr(self, "_sip_log_process", None)
        if old_proc:
            try:
                old_proc.terminate()
            except Exception:
                pass

        self._sip_analyzer_gen = getattr(self, "_sip_analyzer_gen", 0) + 1
        gen = self._sip_analyzer_gen
        uuid = self.current_uuid
        self._flow_dedupe = {}
        self._pending_dnd_reason = False

        for widget in self.flow_scroll.winfo_children():
            widget.destroy()

        def logcat_reader():
            # 이전 로그를 지우고 새로 시작
            subprocess.run(["adb", "-s", uuid, "logcat", "-c"])

            # 실시간 로그 스트림 열기
            process = subprocess.Popen(
                ["adb", "-s", uuid, "logcat", "-v", "time"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self._sip_log_process = process

            self.add_flow_card(
                "PROC", "Analyzer Started", "실시간 SIP/Call Flow 감지를 시작합니다."
            )

            while self._sip_analyzer_gen == gen:
                line = process.stdout.readline()
                if not line:
                    break

                # ==========================================
                # 🔍 [핵심 필터링 로직] 실제 단말 로그 캡처로 검증된 패턴만 사용합니다.
                # (getCalleeUri / uiEventType / mMBCPKeyEvent 는 전부 실측 확인됨.
                #  같은 이벤트가 EveryTalkMain/UIService/ContactActivity 등 여러
                #  컴포넌트에서 중복 로깅되므로 _emit_flow로 짧은 시간 내 중복은 묶습니다.)
                # ==========================================

                # 어떤 프로세스에서 난 것이든, Exception은 원본 그대로 System Log 탭에 남깁니다.
                # (SIP Flow 카드는 아래에서 EveryTalk/MCPTT 관련된 것만 별도로 띄웁니다)
                if "Exception" in line:
                    self.safe_log_insert(line)

                # 0. 발신 대상 (누구에게 걸었는지)
                if "getCalleeUri: calleeUri =" in line:
                    target = line.split("calleeUri =")[1].strip()
                    self._emit_flow("callee", "PROC", "Call Target", f"대상: {target}")
                    self.safe_log_insert(line)

                # 1. 통화 요청 → 미디어 준비 → 연결 성공 (앱 UI 이벤트 흐름)
                elif "uiEventType = TYPE_REQUEST_CALL" in line:
                    self._emit_flow("call_state", "PROC", "Call Requested", "발신 요청")
                    self.safe_log_insert(line)
                elif "uiEventType = TYPE_MEDIA_PREPARE_COMPLETE" in line:
                    self._emit_flow("call_state", "PROC", "Media Ready", "미디어 준비 완료")
                    self.safe_log_insert(line)
                elif "uiEventType = TYPE_CALL_CONNECT_OK" in line:
                    self._pending_dnd_reason = False
                    self._emit_flow("call_state", "RX", "Call Connected", "통화 연결 성공")
                    self.safe_log_insert(line)

                # 2. 통화 실패/DND (uiEventType 줄 다음에 오는 extra=사유 줄과 짝을 맞춥니다)
                elif "uiEventType = TYPE_INFO_CALL_DND" in line:
                    self._pending_dnd_reason = True
                    self.safe_log_insert(line)
                elif self._pending_dnd_reason and "extra = " in line:
                    self._pending_dnd_reason = False
                    reason = line.split("extra = ", 1)[1].strip()
                    if reason and reason != "null":
                        self._emit_flow(
                            "call_fail", "ERR", "Call Failed", reason, is_error=True
                        )
                    self.safe_log_insert(line)

                # 3. 세션 종료
                elif "uiEventType = TYPE_DELETE_SESSION" in line or (
                    "uiEventType = TYPE_DELETED_SESSION" in line
                ):
                    self._emit_flow("session_end", "PROC", "Session End", "세션 종료")
                    self.safe_log_insert(line)

                # 4. PTT 발언권 상태 변경 - 펄스 애니메이션도 이 상태에 연동
                elif "mMBCPKeyEvent =" in line:
                    state = line.split("mMBCPKeyEvent =")[1].strip()
                    changed = self._emit_flow("mbcp", "RX", "Floor State", f"상태: {state}")
                    if changed:
                        self.after(0, lambda s=state: self._on_floor_state(s))
                    self.safe_log_insert(line)

                # 5. 🚨 [가장 중요] 통화 실패나 에러 상황 감지!
                # (앱/MCPTT와 무관한 다른 프로세스의 Exception까지 전부 잡히는 것을
                #  막기 위해 EveryTalk/MCPTT 관련 라인으로 한정합니다.)
                elif ("Exception" in line or " E " in line) and (
                    "MCPTT" in line or "EveryTalk" in line
                ):
                    error_msg = line.split(":")[-1].strip()  # 로그의 맨 뒷부분 내용만 추출
                    self._emit_flow(
                        "error", "ERR", "System Error", f"원인: {error_msg}", is_error=True
                    )
                    # "Exception"이 포함된 줄은 위에서 이미 원본을 System Log에 남겼으므로 중복 방지
                    if "Exception" not in line:
                        self.safe_log_insert(line)

            if self.current_uuid == uuid:
                process.terminate()

        # UI가 멈추지 않도록 데몬 스레드로 실행
        threading.Thread(target=logcat_reader, daemon=True).start()
