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
        self.geometry("1600x900")  # 전문 모니터링을 위해 가로 해상도를 넓게 확보

        # ==========================================
        # 🎨 [Professional Corporate Palette]
        # ==========================================
        self.bg_color = "#F1F5F9"  # 차분한 슬레이트 배경
        self.panel_bg = "#FFFFFF"  # 순백색 패널
        self.border_color = "#E2E8F0"  # 부드러운 구분선

        self.text_main = "#0F172A"  # 텍스트: 다크 네이비 (가독성 극대화)
        self.text_sub = "#64748B"  # 텍스트: 미들 그레이

        self.point_blue = "#2563EB"  # 메인 액션 블루
        self.point_pink = "#E11D48"  # 모니터링/경고 로즈 핑크 (PCAP)
        self.point_green = "#059669"  # 연결/성공 에메랄드 그린
        self.danger_color = "#DC2626"  # 중지/삭제 레드

        self.btn_bg_light = "#F8FAFC"
        self.btn_hover_light = "#F1F5F9"

        self.configure(fg_color=self.bg_color)
        self.current_uuid = None
        self.radius = 4  # 전문 툴에 맞게 모서리 곡률을 타이트하게(4) 변경
        self.is_log_on = False
        self.is_pcap_on = False
        self.is_device_pcap_on = False
        self.project_name = "알 수 없는 프로젝트"

        self._build_ui()

    def _build_ui(self):
        # ------------------------------------------
        # 🗂️ 3단 분할 레이아웃 (Left / Center / Right)
        # ------------------------------------------
        # 1. 좌측 패널 (기기 설정 및 환경) - Width 고정
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

        # 2. 중앙 패널 (제어 및 리스트) - Width 고정
        self.center_panel = ctk.CTkFrame(
            self, width=380, fg_color=self.bg_color, corner_radius=0
        )
        self.center_panel.pack(side="left", fill="y", padx=10, pady=10)
        self.center_panel.pack_propagate(False)

        # 3. 우측 패널 (모니터링, 펄스, 미러링) - 나머지 공간 전체 차지
        self.right_panel = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.right_panel.pack(
            side="left", fill="both", expand=True, pady=10, padx=(0, 10)
        )

        # ==========================================
        # 📱 [LEFT] Device Setup & Management
        # ==========================================
        ctk.CTkLabel(
            self.left_panel,
            text="Device Setup",
            font=("Noto Sans KR", 14, "bold"),
            text_color=self.text_main,
        ).pack(pady=(20, 5), padx=20, anchor="w")

        self.lbl_project = ctk.CTkLabel(
            self.left_panel,
            text="프로젝트: 대기 중",
            font=("Noto Sans KR", 13, "bold"),
            text_color=self.point_blue,
        )
        self.lbl_project.pack(padx=20, anchor="w")

        self.label = ctk.CTkLabel(
            self.left_panel,
            text="단말을 연결해주세요.",
            font=("Noto Sans KR", 12),
            text_color=self.text_sub,
        )
        self.label.pack(pady=(0, 15), padx=20, anchor="w")

        self.btn_connect = ctk.CTkButton(
            self.left_panel,
            text="🟢 기기 연결 및 정보 로드",
            font=("Noto Sans KR", 12, "bold"),
            fg_color=self.point_green,
            hover_color="#047857",
            height=38,
            corner_radius=self.radius,
            command=self.check_device,
        )
        self.btn_connect.pack(padx=20, fill="x")

        # 기기 정보
        self.info_frame = ctk.CTkFrame(
            self.left_panel,
            fg_color=self.btn_bg_light,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        self.info_frame.pack(fill="x", padx=20, pady=15)

        info_font = ("Noto Sans KR", 11)
        self.lbl_model = ctk.CTkLabel(
            self.info_frame, text="모델: -", font=info_font, text_color=self.text_main
        )
        self.lbl_model.pack(pady=(10, 2), padx=10, anchor="w")
        self.lbl_hw_version = ctk.CTkLabel(
            self.info_frame,
            text="HW 버전: -",
            font=info_font,
            text_color=self.text_main,
        )
        self.lbl_hw_version.pack(pady=2, padx=10, anchor="w")
        self.lbl_android_ver = ctk.CTkLabel(
            self.info_frame,
            text="Android 버전: -",
            font=info_font,
            text_color=self.text_main,
        )
        self.lbl_android_ver.pack(pady=2, padx=10, anchor="w")
        self.lbl_os_build = ctk.CTkLabel(
            self.info_frame,
            text="OS 버전: -",
            font=info_font,
            text_color=self.text_main,
        )
        self.lbl_os_build.pack(pady=2, padx=10, anchor="w")
        self.lbl_version = ctk.CTkLabel(
            self.info_frame,
            text="앱 버전: -",
            font=info_font,
            text_color=self.text_main,
        )
        self.lbl_version.pack(pady=2, padx=10, anchor="w")
        self.lbl_network = ctk.CTkLabel(
            self.info_frame,
            text="📶 네트워크: -",
            font=info_font,
            text_color=self.text_main,
        )
        self.lbl_network.pack(pady=(2, 10), padx=10, anchor="w")

        ctk.CTkFrame(self.left_panel, height=1, fg_color=self.border_color).pack(
            fill="x", padx=20, pady=5
        )

        # Configuration
        ctk.CTkLabel(
            self.left_panel,
            text="Configuration",
            font=("Noto Sans KR", 13, "bold"),
            text_color=self.text_main,
        ).pack(pady=(15, 5), padx=20, anchor="w")
        row_config = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        row_config.pack(fill="x", padx=20, pady=2)
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
        self.btn_env.pack(side="left", expand=True, fill="x", padx=(0, 2))
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
        self.btn_wifi.pack(side="left", expand=True, fill="x", padx=(2, 0))

        # App Management
        ctk.CTkLabel(
            self.left_panel,
            text="App Management",
            font=("Noto Sans KR", 13, "bold"),
            text_color=self.text_main,
        ).pack(pady=(15, 5), padx=20, anchor="w")
        self.btn_install = ctk.CTkButton(
            self.left_panel,
            text="📦 앱 설치 (.apk)",
            font=("Noto Sans KR", 12),
            fg_color=self.btn_bg_light,
            border_width=1,
            border_color=self.border_color,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            height=32,
            command=self.run_install_app,
        )
        self.btn_install.pack(fill="x", padx=20, pady=(0, 6))
        row_app = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        row_app.pack(fill="x", padx=20, pady=0)
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
            command=self.run_clear_data,
        )
        self.btn_clear_data.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.btn_uninstall = ctk.CTkButton(
            row_app,
            text="🗑️ 앱 삭제",
            font=("Noto Sans KR", 11),
            fg_color="#FEF2F2",
            border_width=1,
            border_color="#FECACA",
            text_color=self.danger_color,
            hover_color="#FEE2E2",
            height=32,
            command=self.run_uninstall_app,
        )
        self.btn_uninstall.pack(side="left", expand=True, fill="x", padx=(2, 0))

        # ==========================================
        # 🕹️ [CENTER] Control & Target Lists
        # ==========================================
        # 상단 제어 버튼
        center_top = ctk.CTkFrame(self.center_panel, fg_color="transparent")
        center_top.pack(fill="x", pady=(0, 10))

        self.btn_run_scenario = ctk.CTkButton(
            center_top,
            text="▶ 전체 시나리오 실행",
            font=("Noto Sans KR", 12, "bold"),
            fg_color=self.point_blue,
            hover_color="#1D4ED8",
            height=36,
            corner_radius=self.radius,
            command=self.run_automation,
        )
        self.btn_run_scenario.pack(fill="x", pady=(0, 5))

        row_ctrl = ctk.CTkFrame(center_top, fg_color="transparent")
        row_ctrl.pack(fill="x")
        self.btn_stop_scenario = ctk.CTkButton(
            row_ctrl,
            text="⏹ 중지",
            font=("Noto Sans KR", 12, "bold"),
            fg_color=self.panel_bg,
            border_width=1,
            border_color=self.danger_color,
            text_color=self.danger_color,
            hover_color="#FEF2F2",
            height=34,
            corner_radius=self.radius,
            command=self.stop_automation,
        )
        self.btn_stop_scenario.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.btn_unit_test = ctk.CTkButton(
            row_ctrl,
            text="🛠️ 단위 테스트",
            font=("Noto Sans KR", 12, "bold"),
            fg_color=self.panel_bg,
            border_width=1,
            border_color=self.border_color,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            height=34,
            corner_radius=self.radius,
            command=self.open_unit_test_popup,
        )
        self.btn_unit_test.pack(side="left", expand=True, fill="x", padx=(2, 0))

        # 기능 태그
        self.feature_card = ctk.CTkFrame(
            self.center_panel,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        self.feature_card.pack(fill="x", pady=(0, 10))
        self.feature_tag_frame = ctk.CTkFrame(self.feature_card, fg_color="transparent")
        self.feature_tag_frame.pack(fill="both", expand=True, padx=10, pady=5)
        ctk.CTkLabel(
            self.feature_tag_frame,
            text="단말기 연결 시 프로젝트 지원 기능 표시",
            font=("Noto Sans KR", 11),
            text_color=self.text_sub,
        ).pack(expand=True, pady=10)

        # 리스트 영역 (세로로 길게 확보)
        self.list_container = ctk.CTkFrame(
            self.center_panel,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        self.list_container.pack(expand=True, fill="both")
        self.list_container.pack_propagate(False)

        header_frame = ctk.CTkFrame(self.list_container, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        self.btn_tab_group = ctk.CTkButton(
            header_frame,
            text="Group List",
            height=30,
            corner_radius=4,
            fg_color=self.point_blue,
            text_color="white",
            command=lambda: self.switch_tab("group"),
        )
        self.btn_tab_group.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.btn_tab_user = ctk.CTkButton(
            header_frame,
            text="User List",
            height=30,
            corner_radius=4,
            fg_color=self.btn_bg_light,
            text_color=self.text_sub,
            command=lambda: self.switch_tab("user"),
        )
        self.btn_tab_user.pack(side="left", expand=True, fill="x", padx=(2, 2))
        self.btn_refresh = ctk.CTkButton(
            header_frame,
            text="🔄",
            width=30,
            height=30,
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            hover_color=self.border_color,
            command=self.refresh_all_lists,
        )
        self.btn_refresh.pack(side="right", padx=(2, 0))

        self.current_mode = "call"
        self.all_cards = []
        self.group_list_frame = ctk.CTkScrollableFrame(
            self.list_container, fg_color="transparent"
        )
        self.group_list_frame.pack(expand=True, fill="both", padx=5, pady=5)
        self.user_list_frame = ctk.CTkScrollableFrame(
            self.list_container, fg_color="transparent"
        )

        btn_action_frame = ctk.CTkFrame(self.list_container, fg_color="transparent")
        btn_action_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        self.my_id_label = ctk.CTkLabel(
            btn_action_frame,
            text="내 정보: 연결 대기",
            font=("Noto Sans KR", 11, "bold"),
            text_color=self.point_blue,
        )
        self.my_id_label.pack(fill="x", pady=(0, 5))
        self.btn_group_call = ctk.CTkButton(
            btn_action_frame,
            text="📞 통화 발신",
            font=("Noto Sans KR", 13, "bold"),
            fg_color=self.point_green,
            hover_color="#047857",
            height=40,
            corner_radius=self.radius,
            command=self.on_main_call_button_clicked,
        )
        self.btn_group_call.pack(side="left", expand=True, fill="x", padx=(0, 2))
        self.btn_group_msg = ctk.CTkButton(
            btn_action_frame,
            text="💬 메시지 전송",
            font=("Noto Sans KR", 13, "bold"),
            fg_color=self.point_blue,
            hover_color="#1D4ED8",
            height=40,
            corner_radius=self.radius,
            command=self.send_group_message,
        )
        self.btn_group_msg.pack(side="left", expand=True, fill="x", padx=(2, 0))

        # ==========================================
        # 📈 [RIGHT] Monitoring, Pulse & SIP Flow Arena
        # ==========================================
        # 1. 우측 상단 (Preview & Audio Pulse)
        right_top = ctk.CTkFrame(self.right_panel, fg_color="transparent", height=380)
        right_top.pack(side="top", fill="x", pady=(0, 10))
        right_top.pack_propagate(False)

        # 미러링 (좌측 배치, 가로 고정)
        preview_bg = ctk.CTkFrame(
            right_top,
            width=240,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        preview_bg.pack(side="left", fill="y", padx=(0, 10))
        preview_bg.pack_propagate(False)

        mirror_top = ctk.CTkFrame(preview_bg, height=36, fg_color="transparent")
        mirror_top.pack(fill="x", padx=8, pady=5)
        ctk.CTkLabel(
            mirror_top,
            text="📱 Device Preview",
            font=("Noto Sans KR", 11, "bold"),
            text_color=self.text_main,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            mirror_top,
            text="📸 캡쳐",
            font=("Noto Sans KR", 10),
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            hover_color=self.border_color,
            width=50,
            height=24,
            corner_radius=4,
            command=self.capture_screen,
        ).pack(side="right", padx=2)

        self.mirror_container = tk.Frame(preview_bg, bg="#0F172A")
        self.mirror_container.pack(expand=True, fill="both", padx=8, pady=(0, 8))
        self.lbl_placeholder = ctk.CTkLabel(
            self.mirror_container,
            text="미러링 대기 중",
            font=("Noto Sans KR", 12),
            text_color="#64748B",
        )
        self.lbl_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # 오디오 펄스 (우측 배치, 남은 공간 전체 차지)
        self.pulse_frame = ctk.CTkFrame(
            right_top, fg_color="#1E293B", corner_radius=self.radius
        )
        self.pulse_frame.pack(side="left", expand=True, fill="both")

        pulse_header = ctk.CTkFrame(self.pulse_frame, height=36, fg_color="transparent")
        pulse_header.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(
            pulse_header,
            text="🎙️ Real-time Audio Pulse",
            font=("Noto Sans KR", 11, "bold"),
            text_color="#94A3B8",
        ).pack(side="left")

        self.pulse_canvas = tk.Canvas(
            self.pulse_frame, bg="#1E293B", highlightthickness=0
        )
        self.pulse_canvas.pack(expand=True, fill="both", padx=15, pady=(0, 15))
        self.lbl_pulse_placeholder = self.pulse_canvas.create_text(
            250,
            100,
            text="오디오 펄스 분석 대기 중...",
            fill="#475569",
            font=("Noto Sans KR", 12),
        )

        # 2. 우측 하단 (Terminal, SIP Flow, PCAP) - 전체 영역 8:2 분할!
        self.monitor_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.monitor_frame.pack(side="top", expand=True, fill="both")

        # Grid 레이아웃으로 8:2 비율 강제 설정
        self.monitor_frame.grid_columnconfigure(0, weight=8)
        self.monitor_frame.grid_columnconfigure(1, weight=2)
        self.monitor_frame.grid_rowconfigure(0, weight=1)

        # --------------------------------------------------
        # [좌측 80%]: 기존 터미널 및 탭 뷰 영역
        # --------------------------------------------------
        monitor_left = ctk.CTkFrame(
            self.monitor_frame,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        monitor_left.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # 터미널 헤더 (컨트롤 버튼)
        monitor_header = ctk.CTkFrame(monitor_left, height=44, fg_color="transparent")
        monitor_header.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            monitor_header,
            text="Network & System Logs",
            font=("Noto Sans KR", 13, "bold"),
            text_color=self.text_main,
        ).pack(side="left", padx=10)

        self.btn_toggle_pcap = ctk.CTkButton(
            monitor_header,
            text="🔴 PCAP ON",
            font=("Noto Sans KR", 11, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=self.point_pink,
            text_color=self.point_pink,
            hover_color="#FFE4E6",
            width=100,
            height=30,
            corner_radius=4,
            command=self.toggle_pcap,
        )
        self.btn_toggle_pcap.pack(side="right", padx=(5, 5))

        self.btn_toggle_log = ctk.CTkButton(
            monitor_header,
            text="📝 Logcat ON",
            font=("Noto Sans KR", 11, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=self.text_sub,
            text_color=self.text_sub,
            hover_color=self.btn_hover_light,
            width=100,
            height=30,
            corner_radius=4,
            command=self.toggle_log,
        )
        self.btn_toggle_log.pack(side="right", padx=5)

        # 터미널 탭 뷰
        self.tab_view = ctk.CTkTabview(
            monitor_left,
            fg_color="#F8FAFC",
            segmented_button_selected_color=self.point_blue,
            segmented_button_selected_hover_color="#1D4ED8",
            segmented_button_unselected_color="#E2E8F0",
            segmented_button_unselected_hover_color="#CBD5E1",
            text_color=self.text_main,
        )
        self.tab_view.pack(expand=True, fill="both", padx=10, pady=(0, 10))

        self.tab_view.add("SIP Flow")
        self.tab_view.add("System Log")

        # [SIP Flow Tab]
        ctk.CTkLabel(
            self.tab_view.tab("SIP Flow"),
            text="Wireshark Style SIP Flow Visualization\n(향후 Call 진행 시 이곳에 패킷 흐름 및 사다리꼴 다이어그램 표시)",
            font=("Noto Sans KR", 12),
            text_color=self.text_sub,
        ).pack(expand=True)

        # [SIP Flow Tab] - 실시간 시퀀스 다이어그램 스타일로 변경
        self.flow_scroll = ctk.CTkScrollableFrame(
            self.tab_view.tab("SIP Flow"), fg_color="transparent"
        )
        self.flow_scroll.pack(expand=True, fill="both", padx=5, pady=5)

        # 💡 [신규] 실시간 메시지 카드를 UI에 추가하는 함수
        def add_flow_card(event_type, title, detail, is_error=False):
            # 스레드 안전성을 위해 after 사용
            def update_ui():
                # 에러면 빨간색, 내부 처리면 파란색, 수신이면 초록색
                if is_error:
                    border_color = self.danger_color
                    bg_color = "#FEF2F2"  # 연한 빨강
                    icon = "🚨 ERROR"
                elif event_type == "RX":
                    border_color = self.point_green
                    bg_color = "#ECFDF5"  # 연한 초록
                    icon = "📥 RECV "
                else:
                    border_color = self.point_blue
                    bg_color = self.panel_bg
                    icon = "⚙️ PROC "

                card = ctk.CTkFrame(
                    self.flow_scroll,
                    fg_color=bg_color,
                    corner_radius=6,
                    border_width=1,
                    border_color=border_color,
                )
                card.pack(fill="x", padx=5, pady=4)

                # 좌측: 아이콘 및 이벤트 타이틀
                ctk.CTkLabel(
                    card,
                    text=f"{icon} | {title}",
                    font=("Noto Sans KR", 12, "bold"),
                    text_color=border_color,
                ).pack(side="left", padx=10, pady=8)

                # 우측: 상세 정보 (에러면 글씨도 빨간색)
                detail_color = self.danger_color if is_error else self.text_sub
                ctk.CTkLabel(
                    card, text=detail, font=("Consolas", 11), text_color=detail_color
                ).pack(side="left", padx=(5, 10))

                # 스크롤 맨 아래로 자동 이동
                self.flow_scroll._parent_canvas.yview_moveto(1.0)

            self.after(0, update_ui)

        # 함수를 클래스 변수로 저장해두어 나중에 백그라운드 스레드에서 쓸 수 있게 함
        self.add_flow_card = add_flow_card

        # UI에 잘 나오는지 확인하기 위한 샘플 데이터 (실제 연동 후엔 지우셔도 됩니다)
        self.add_flow_card("PROC", "Call Initiated", "대상: tel:+82900110120")
        self.add_flow_card("RX", "MBCP Receive", "FIELD_ID_MSN msn = 5")
        # 에러 발생 상황 시뮬레이션!
        # self.add_flow_card("ERR", "MediaManager Error", "Audio Stream Timeout!", is_error=True)

        # [System Log Tab] - 원래대로 단일창 복구
        self.entry_search = ctk.CTkEntry(
            self.tab_view.tab("System Log"),
            placeholder_text="🔍 터미널 로그 검색 (INVITE, Exception 등)",
            height=32,
            corner_radius=4,
            fg_color="#FFFFFF",
            border_color=self.border_color,
        )
        self.entry_search.pack(fill="x", pady=(0, 5))
        self.txt_log = ctk.CTkTextbox(
            self.tab_view.tab("System Log"),
            font=("Consolas", 12),
            fg_color="#FFFFFF",
            text_color=self.text_main,
            border_width=1,
            border_color=self.border_color,
            corner_radius=4,
        )
        self.txt_log.pack(expand=True, fill="both")
        self.txt_log.insert("1.0", "[Terminal] 시스템 로그 출력을 대기 중입니다...\n")

        # --------------------------------------------------
        # [우측 20%]: 통화 결과 (Result) 고정 영역
        # --------------------------------------------------
        monitor_right = ctk.CTkFrame(
            self.monitor_frame,
            fg_color=self.panel_bg,
            corner_radius=self.radius,
            border_width=1,
            border_color=self.border_color,
        )
        monitor_right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        # 결과 창 헤더 (좌측 헤더와 높이를 맞춤)
        result_header = ctk.CTkFrame(monitor_right, height=44, fg_color="transparent")
        result_header.pack(fill="x", padx=10, pady=5)
        result_header.pack_propagate(False)
        ctk.CTkLabel(
            result_header,
            text="🎯 통화 결과",
            font=("Noto Sans KR", 13, "bold"),
            text_color=self.text_main,
        ).pack(side="left", pady=10)

        # 결과 출력용 텍스트박스
        self.txt_result = ctk.CTkTextbox(
            monitor_right,
            font=("Consolas", 12, "bold"),
            fg_color="#FFFFFF",
            text_color=self.text_main,
            border_width=1,
            border_color=self.border_color,
            corner_radius=4,
        )
        self.txt_result.pack(expand=True, fill="both", padx=10, pady=(0, 10))
        self.txt_result.insert("1.0", "대기 중...\n")

        # 👇 펄스 애니메이션 초기화 (마지막 줄 고정)
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

            network_status = adb_logic.get_network_status(self.current_uuid)

            # 2. UI 라벨 텍스트 업데이트
            self.label.configure(text=f"연결됨: {model}", text_color=self.point_green)

            self.lbl_model.configure(text=f"모델: {model}")
            self.lbl_hw_version.configure(text=f"HW 버전: {hw_version}")
            self.lbl_android_ver.configure(text=f"Android 버전: {android_version}")
            self.lbl_os_build.configure(text=f"OS 버전: {os_build}")
            self.lbl_version.configure(text=f"앱 버전: {version_name}")

            self.lbl_network.configure(
                text=f"📶 네트워크: {network_status}", text_color=self.text_main
            )

            # ✅ [수정된 부분] 저장된 self.project_name을 UI에 표시합니다.
            self.lbl_project.configure(text=f"프로젝트: {self.project_name}")

            self.update_project_features(self.project_name)

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

    # ==========================================
    # 🎙️ 최적화된 오디오 펄스(Waveform) 애니메이션 로직
    # ==========================================
    def init_audio_pulse(self):
        """캔버스에 파형을 그릴 막대기(Line)들을 미리 생성해 둡니다. (최적화 핵심)"""
        self.pulse_canvas.delete("all")  # 기존 대기중 글자 삭제
        self.pulse_bars = []

        # 캔버스 크기 가져오기
        canvas_width = self.pulse_canvas.winfo_width()
        canvas_height = self.pulse_canvas.winfo_height()

        if canvas_width <= 1:
            canvas_width, canvas_height = 400, 100  # 기본값

        self.center_y = canvas_height // 2
        bar_width = 3  # 막대 두께
        spacing = 3  # 막대 사이 간격
        num_bars = canvas_width // (bar_width + spacing)

        # 화면 너비만큼 막대기 객체를 미리 만들어둠 (색상: 에메랄드 그린)
        for i in range(num_bars):
            x = i * (bar_width + spacing) + 10
            # 처음에는 길이가 0인 점으로 시작
            line = self.pulse_canvas.create_line(
                x,
                self.center_y,
                x,
                self.center_y,
                width=bar_width,
                fill="#10B981",
                capstyle="round",
            )
            self.pulse_bars.append((line, x))

        # 애니메이션 루프 시작
        self.animate_audio_pulse()

    def animate_audio_pulse(self):
        """실시간으로 막대기들의 길이를 변경하여 꿀렁이는 파형을 만듭니다."""
        import random

        # 현재 연결된 단말기가 있고, '통화 중' 상태일 때만 파형이 크게 움직이도록 설정
        # (임시로 단말기가 연결되면 무조건 움직이게 작성했습니다)
        is_active = self.current_uuid is not None

        for line, x in self.pulse_bars:
            if is_active:
                # 💡 나중에 이 random.randint 부분을 '실제 오디오 볼륨 크기 변수'로 교체하시면 됩니다!
                amplitude = random.randint(2, 40)
            else:
                amplitude = random.randint(1, 3)  # 대기 상태일 때는 잔잔하게

            # 기존 객체의 좌표(coords)만 업데이트 (CPU 부하 최소화)
            self.pulse_canvas.coords(
                line, x, self.center_y - amplitude, x, self.center_y + amplitude
            )

        # 50ms 마다 갱신 (초당 20프레임 수준으로 Tkinter가 충분히 버틸 수 있음)
        self.after(50, self.animate_audio_pulse)

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

        def create_tag_row(title, icon, category_data, name_map, bg_color, txt_color):
            active_features = [
                name_map[key]
                for key, val in category_data.items()
                if val == 1 and key in name_map
            ]
            if not active_features:
                return

            row_frame = ctk.CTkFrame(self.feature_tag_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=3)

            ctk.CTkLabel(
                row_frame,
                text=f"{icon} {title}:",
                font=("Noto Sans KR", 12, "bold"),
                text_color=self.text_sub,
                width=80,
                anchor="w",
            ).pack(side="left", padx=(0, 5))

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

        create_tag_row(
            "Group",
            "👥",
            features.get("group_call", {}),
            group_map,
            bg_color="#DBEAFE",
            txt_color="#1E40AF",
        )
        create_tag_row(
            "Private",
            "👤",
            private_call_data,
            private_map,
            bg_color="#D1FAE5",
            txt_color="#065F46",
        )
        create_tag_row(
            "Message",
            "✉️",
            features.get("message", {}),
            msg_map,
            bg_color="#FFEDD5",
            txt_color="#9A3412",
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

            # 1. 섹션 헤더 (가로 구분선 추가)
            header_frame = ctk.CTkFrame(self.group_list_frame, fg_color="transparent")
            header_frame.pack(fill="x", padx=5, pady=(15, 5))

            ctk.CTkLabel(
                header_frame,
                text=title,
                font=("Noto Sans KR", 12, "bold"),
                text_color=self.text_main,
            ).pack(side="left")

            ctk.CTkFrame(header_frame, height=1, fg_color=self.border_color).pack(
                side="left", fill="x", expand=True, padx=(10, 0)
            )

            # 2. 리스트 카드 생성
            for g_info in group_list:
                card = ctk.CTkFrame(
                    self.group_list_frame,
                    fg_color=self.panel_bg,
                    corner_radius=4,
                    border_width=1,
                    border_color=self.border_color,
                )
                card.pack(fill="x", padx=5, pady=3)

                voice = g_info.get("voice_codec", "")
                video = g_info.get("video_codec", "")
                codec_str = ""
                if voice or video:
                    v_str = f"🎤 {voice}" if voice else ""
                    vd_str = f"🎬 {video}" if video else ""
                    divider = " | " if (voice and video) else ""
                    codec_str = f"[{v_str}{divider}{vd_str}]"

                var_check = ctk.StringVar(value="off")

                # 상단 행 프레임
                top_row = ctk.CTkFrame(card, fg_color="transparent")
                top_row.pack(fill="x", padx=10, pady=(8, 4 if codec_str else 8))

                # ==========================================
                # 💡 [핵심 디자인 수정] 체크박스와 텍스트 분리 및 2줄 배치
                # ==========================================
                # 1) 체크박스 (글자 없이 박스만)
                chk = ctk.CTkCheckBox(
                    top_row,
                    text="",  # 글자를 비웁니다
                    width=28,  # 박스 크기 유지
                    variable=var_check,
                    onvalue="on",
                    offvalue="off",
                    border_width=2,
                    border_color="#94A3B8",
                    fg_color=self.point_blue,
                    command=self.update_group_visibility,
                )
                chk.pack(side="left", padx=(0, 8))

                # 2) 텍스트를 담을 세로 컨테이너 프레임
                text_frame = ctk.CTkFrame(top_row, fg_color="transparent")
                text_frame.pack(side="left", fill="both", expand=True)

                # 3) 채널명 (일반 굵기 'normal', 크기 12)
                lbl_name = ctk.CTkLabel(
                    text_frame,
                    text=g_info["name"],
                    font=("Noto Sans KR", 12, "normal"),  # bold를 normal로 변경
                    text_color=self.text_main,
                )
                lbl_name.pack(anchor="w")

                # 4) 서비스 ID (크기 11, 줄바꿈)
                lbl_id = ctk.CTkLabel(
                    text_frame,
                    text=f"ID: {g_info['id']}",  # 구분을 위해 ID: 라는 접두사 추가
                    font=("Noto Sans KR", 11, "normal"),  # 1px 작게
                    text_color=self.text_sub,  # 서브 텍스트 색상(회색)으로 세련되게 처리
                )
                # 글자 사이 여백을 최소화하여 깔끔하게 붙임
                lbl_id.pack(anchor="w", pady=(0, 0))

                # 편의성: 글자를 클릭해도 체크박스가 작동하도록 마우스 이벤트 연결
                def toggle_checkbox(event, var=var_check):
                    var.set("off" if var.get() == "on" else "on")
                    self.update_group_visibility()

                lbl_name.bind("<Button-1>", toggle_checkbox)
                lbl_id.bind("<Button-1>", toggle_checkbox)
                # ==========================================

                if codec_str:
                    lbl_codec = ctk.CTkLabel(
                        card,
                        text=codec_str,
                        font=("Noto Sans KR", 10),
                        text_color="#94A3B8",
                    )
                    lbl_codec.pack(anchor="w", padx=(38, 10), pady=(0, 8))

                action_row = ctk.CTkFrame(card, fg_color="transparent")

                # 3. 액션 버튼 (통화/메시지)
                seg_call = ctk.CTkSegmentedButton(
                    action_row,
                    values=["🔊 PTT", "📹 PTV", "🚨 E-PTT", "🚨 E-PTV"],
                    height=30,
                    font=("Noto Sans KR", 11, "bold"),
                    fg_color="#F8FAFC",
                    selected_color=self.point_blue,
                    selected_hover_color="#1D4ED8",
                    unselected_color="#E2E8F0",
                    unselected_hover_color="#CBD5E1",
                    text_color=self.text_main,
                )

                seg_msg = ctk.CTkSegmentedButton(
                    action_row,
                    values=["📄 Text", "🖼️ Photo", "🎥 Video"],
                    height=30,
                    font=("Noto Sans KR", 11, "bold"),
                    fg_color="#F8FAFC",
                    selected_color=self.point_blue,
                    selected_hover_color="#1D4ED8",
                    unselected_color="#E2E8F0",
                    unselected_hover_color="#CBD5E1",
                    text_color=self.text_main,
                )

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

        regroups = sorted(
            (g for g in groups if g.get("type") == "ReGroup"),
            key=lambda x: x.get("name", "").lower(),
        )

        pre_groups = sorted(
            (g for g in groups if g.get("type") == "PreArranged Group"),
            key=lambda x: x.get("name", "").lower(),
        )

        chat_groups = sorted(
            (g for g in groups if g.get("type") == "Chat Group"),
            key=lambda x: x.get("name", "").lower(),
        )

        create_section("📁 ReGroup", regroups)
        create_section("📁 PreArranged Group", pre_groups)
        create_section("💬 Chat Group", chat_groups)

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

    def on_call_button(self):
        self.current_mode = "call"
        self.update_group_visibility()

    def on_msg_button(self):
        self.current_mode = "msg"
        self.update_group_visibility()

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
                selected_targets.append(
                    {"id": group_id, "name": data["name"], "mode": clean_mode}
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

                self.safe_log_insert(
                    f"\n▶️ [{idx}/{len(selected_targets)}] '{t_name}' ({t_mode}) 발신 진행 중...\n"
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
        filtered_users = [
            u for u in users if str(u.get("name", "")).startswith(my_group_code)
        ]

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

            user_card = ctk.CTkFrame(
                self.user_list_frame, fg_color="#F1F5F9", corner_radius=6
            )
            user_card.pack(fill="x", padx=5, pady=2)

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
                border_width=2,
                border_color="#94A3B8",
                command=self.update_user_action_frame,
            )
            chk.pack(anchor="w", padx=10, pady=8)

            action_row = ctk.CTkFrame(user_card, fg_color="transparent")

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

            self.user_ui_registry[u_name] = {
                "checkbox_var": chk_var,
                "action_row": action_row,
            }

    def update_user_action_frame(self):
        for u_name, ui_data in self.user_ui_registry.items():
            var = ui_data["checkbox_var"]
            row = ui_data["action_row"]
            if var.get() == "on":
                row.pack(fill="x", padx=0, pady=(0, 5))
            else:
                row.pack_forget()

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


def start_realtime_log_analyzer(self):
    """단말기 로그를 실시간으로 스니핑하여 에러 및 흐름을 분석하는 백그라운드 스레드"""
    if not self.current_uuid:
        return

    import subprocess
    import threading

    def logcat_reader():
        # 이전 로그를 지우고 새로 시작
        subprocess.run(["adb", "-s", self.current_uuid, "logcat", "-c"])

        # 실시간 로그 스트림 열기
        process = subprocess.Popen(
            ["adb", "-s", self.current_uuid, "logcat", "-v", "time"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        self.add_flow_card(
            "PROC", "Analyzer Started", "실시간 Flow 및 에러 감지를 시작합니다."
        )

        while True:
            line = process.stdout.readline()
            if not line:
                break

            # ==========================================
            # 🔍 [핵심 필터링 로직] 여기서 원하는 상황을 낚아챕니다!
            # ==========================================

            # 1. 통화 발신 시도 (누구에게 걸었는지)
            if "getCalleeUri: calleeUri =" in line:
                target = line.split("calleeUri =")[1].strip()
                self.add_flow_card("PROC", "Call Target", f"대상: {target}")

            # 2. PTT 발언권 상태 변경 (가장 중요)
            elif "ACTION_MBCP_STATE:" in line:
                state = line.split("ACTION_MBCP_STATE:")[1].strip()
                self.add_flow_card("RX", "Floor State", f"상태 변경: {state}")

            # 3. 미디어(오디오) 연결 상태
            elif "playAudioPTT" in line:
                self.add_flow_card(
                    "PROC", "Audio Engine", "PTT 오디오 세션 활성화 완료"
                )

            # 4. 🚨 [가장 중요] 통화 실패나 에러 상황 감지!
            # (로그에 Exception, fail, error, timeout 등이 뜨면 무조건 캡처)
            elif "Exception" in line or (" E " in line and "MCPTT" in line):
                # " E " 는 로그캣에서 Error 레벨을 의미합니다.
                error_msg = line.split(":")[-1].strip()  # 로그의 맨 뒷부분 내용만 추출
                self.add_flow_card(
                    "ERR", "System Error", f"원인: {error_msg}", is_error=True
                )

    # UI가 멈추지 않도록 데몬 스레드로 실행
    threading.Thread(target=logcat_reader, daemon=True).start()
