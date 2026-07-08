import customtkinter as ctk
import tkinter as tk  # ✨ [추가됨] 순수 프레임을 쓰기 위해 가져옵니다!
import adb_logic
import os
import ctypes
import sys
import datetime
import json
import time
from tkinter import filedialog
from file_manager import FileManager


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


load_custom_font("Pretendard-Regular.otf")


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
            font=("Pretendard", 16, "bold"),
            text_color=self.text_main,
        ).pack(pady=(20, 5), padx=20, anchor="w")

        # ✨ 1. 프로젝트명을 더 크고(14) 진한 검정색(text_main)으로 변경!
        self.lbl_project = ctk.CTkLabel(
            self.left_panel,
            text="프로젝트: 대기 중",
            font=("Pretendard", 14, "bold"),
            text_color=self.text_main,
        )
        self.lbl_project.pack(padx=20, anchor="w")

        self.label = ctk.CTkLabel(
            self.left_panel,
            text="단말을 연결해주세요.",
            font=("Pretendard", 12),
            text_color=self.text_sub,
        )
        self.label.pack(pady=(5, 15), padx=20, anchor="w")

        self.btn_connect = ctk.CTkButton(
            self.left_panel,
            text="🟢 기기 연결 및 미러링",
            font=("Pretendard", 13, "bold"),
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
            font=("Pretendard", 12),
            text_color=self.text_main,
        )
        self.lbl_model.pack(pady=(10, 2), padx=10, anchor="w")

        self.lbl_hw_version = ctk.CTkLabel(
            self.info_frame,
            text="HW 버전: -",
            font=("Pretendard", 12),
            text_color=self.text_main,
        )
        self.lbl_hw_version.pack(pady=2, padx=10, anchor="w")

        self.lbl_android_ver = ctk.CTkLabel(
            self.info_frame,
            text="Android 버전: -",
            font=("Pretendard", 12),
            text_color=self.text_main,
        )
        self.lbl_android_ver.pack(pady=2, padx=10, anchor="w")

        self.lbl_os_build = ctk.CTkLabel(
            self.info_frame,
            text="OS 버전: -",
            font=("Pretendard", 12),
            text_color=self.text_main,
        )
        self.lbl_os_build.pack(pady=2, padx=10, anchor="w")

        self.lbl_version = ctk.CTkLabel(
            self.info_frame,
            text="앱 버전: -",
            font=("Pretendard", 12),
            text_color=self.text_main,
        )
        self.lbl_version.pack(pady=2, padx=10, anchor="w")

        self.lbl_network = ctk.CTkLabel(
            self.info_frame,
            text="📶 네트워크: -",
            font=("Pretendard", 12),
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
            font=("Pretendard", 14, "bold"),
            text_color=self.text_main,
        ).pack(pady=(15, 10), padx=20, anchor="w")

        row_config = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        row_config.pack(fill="x", padx=20, pady=2)
        self.btn_env = ctk.CTkButton(
            row_config,
            text="⚙️ 환경 설정",
            font=("Pretendard", 12),
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
            font=("Pretendard", 12),
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
            font=("Pretendard", 14, "bold"),
            text_color=self.text_main,
        ).pack(pady=(25, 10), padx=20, anchor="w")

        self.btn_install = ctk.CTkButton(
            self.left_panel,
            text="📦 앱 설치 (.apk)",
            font=("Pretendard", 12),
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
            font=("Pretendard", 12),
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
            font=("Pretendard", 12),
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
            font=("Pretendard", 13, "bold"),
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
            font=("Pretendard", 13, "bold"),
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
            font=("Pretendard", 13, "bold"),
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            hover_color=self.btn_hover_light,
            height=36,
            corner_radius=self.radius,
            command=self.open_unit_test_popup,
        )
        self.btn_unit_test.pack(side="left", padx=5, pady=10)

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
            command=self.refresh_group_list,
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
            font=("Pretendard", 13, "bold"),
            fg_color=self.point_green,
            hover_color="#059669",
            text_color="#FFFFFF",
            height=36,
            corner_radius=self.radius,
            command=self.make_group_call,
        )
        self.btn_group_call.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_group_msg = ctk.CTkButton(
            btn_action_frame,
            text="💬 메시지",
            font=("Pretendard", 13, "bold"),
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
            font=("Pretendard", 12, "bold"),
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
            font=("Pretendard", 13, "bold"),
            text_color=self.text_main,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            mirror_top,
            text="📸 캡쳐",
            font=("Pretendard", 11),
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
            font=("Pretendard", 14),
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
            font=("Pretendard", 12, "bold"),
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
            font=("Pretendard", 12, "bold"),
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
            font=("Pretendard", 12),
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

            network_status = "LTE (SKT)"

            # 2. UI 라벨 텍스트 업데이트
            # (🌟 이전에 쓰던 lbl_battery 같은 코드가 있으면 여기서 에러가 났을 겁니다)
            self.label.configure(text=f"연결됨: {model}", text_color=self.point_green)

            self.lbl_model.configure(text=f"모델: {model}")
            self.lbl_hw_version.configure(text=f"HW 버전: {hw_version}")
            self.lbl_android_ver.configure(text=f"Android 버전: {android_version}")
            self.lbl_os_build.configure(text=f"OS 버전: {os_build}")
            self.lbl_version.configure(text=f"앱 버전: {version_name}")

            self.lbl_network.configure(
                text=f"📶 {network_status}", text_color=self.text_main
            )
            self.lbl_project.configure(text=f"프로젝트: {project_name}")

            adb_logic.unlock_screen(self.current_uuid)

            # 3. 미러링 및 그룹 목록 새로고침 실행
            self.run_mirror()
            self.refresh_group_list()

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

    def refresh_group_list(self):
        if not self.current_uuid:
            return

        path = FileManager.pull_profile_xml(self.current_uuid)
        if not os.path.exists(path):
            return

        groups = FileManager.parse_group_list(path)
        my_info = FileManager.parse_my_info(path)
        self.my_id_label.configure(text=f"내 정보: {my_info}")

        # 초기화
        self.all_cards = []
        self.group_check_vars = {}
        for widget in self.group_list_frame.winfo_children():
            widget.destroy()

        # 내부 함수: 섹션 그리기
        def create_section(title, group_list):
            if not group_list:
                return
            ctk.CTkLabel(
                self.group_list_frame,
                text=title,
                font=("Pretendard", 12, "bold"),
                text_color=self.text_sub,
            ).pack(anchor="w", padx=5, pady=(15, 5))

            for g_info in group_list:
                # 1. 카드 생성
                card = ctk.CTkFrame(
                    self.group_list_frame,
                    fg_color="#F8FAFC",
                    corner_radius=8,
                    border_width=1,
                    border_color=self.border_color,
                )
                card.pack(fill="x", padx=5, pady=4)

                # 2. 코덱 정보 가져오기
                voice = g_info.get("voice_codec", "")
                video = g_info.get("video_codec", "")

                codec_str = ""
                if voice or video:
                    v_str = f"🎤 {voice}" if voice else ""
                    vd_str = f"🎬 {video}" if video else ""
                    divider = " | " if (voice and video) else ""
                    codec_str = f"[{v_str}{divider}{vd_str}]"

                # 3. 체크박스 (그룹명) - 부모를 다시 card로 변경!
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
                    font=("Pretendard", 13, "bold"),
                    text_color=self.text_main,
                    command=self.update_group_visibility,
                )
                # 아래쪽 여백(pady)을 0으로 줘서 아래 코덱 글자와 간격을 좁힙니다.
                chk.pack(anchor="w", padx=10, pady=(10, 0))

                # 4. 코덱 라벨 (그룹명 바로 아래 배치)
                if codec_str:
                    lbl_codec = ctk.CTkLabel(
                        card,
                        text=codec_str,
                        font=("Pretendard", 10),
                        text_color="#64748B",
                    )
                    # 💡 [핵심 디테일] 체크박스 네모칸 너비(약 26px)만큼 여백을 더 줘서 글자 줄을 맞춥니다.
                    lbl_codec.pack(anchor="w", padx=(36, 10), pady=(0, 10))

                # 5. 액션 로우 (버튼들을 담을 그릇)
                action_row = ctk.CTkFrame(card, fg_color="transparent")

                # 4. 세그먼트 버튼 생성
                seg_call = ctk.CTkSegmentedButton(
                    action_row,
                    values=["🔊 PTT", "📹 PTV", "🚨 E-PTT", "🚨 E-PTV"],
                    height=32,
                    font=("Pretendard", 11, "bold"),
                    # [핵심 스타일링]
                    fg_color="#F8FAFC",  # 카드 배경색과 동일하게 맞춤 (통일감)
                    selected_color="#2563EB",  # [사진 느낌] 선택 시 예쁜 파란색
                    selected_hover_color="#2563EB",
                    unselected_color="#E2E8F0",  # [핵심] 기존 칙칙한 회색 대신 아주 연한 회색
                    unselected_hover_color="#CBD5E1",
                    text_color="#CBD5E1",  # 글자색도 진한 회색으로 조정
                )
                seg_msg = ctk.CTkSegmentedButton(
                    action_row,
                    values=["📄 Text", "🖼️ Photo", "🎥 Video"],
                    height=32,
                    font=("Pretendard", 11, "bold"),
                    # [핵심 스타일링]
                    fg_color="#F8FAFC",  # 카드 배경색과 동일하게 맞춤 (통일감)
                    selected_color="#2563EB",  # [사진 느낌] 선택 시 예쁜 파란색
                    selected_hover_color="#2563EB",
                    unselected_color="#E2E8F0",  # [핵심] 기존 칙칙한 회색 대신 아주 연한 회색
                    unselected_hover_color="#CBD5E1",
                    text_color="#CBD5E1",  # 글자색도 진한 회색으로 조정
                )

                # 5. 카드에 참조 저장
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

        create_section(
            "◆ PreArranged Group",
            [g for g in groups if g["type"] == "PreArranged Group"],
        )
        create_section("◆ Chat Group", [g for g in groups if g["type"] == "Chat Group"])

        # 마지막에 한번 업데이트해서 초기 상태 적용
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

    def make_group_call(self):
        if not self.current_uuid:
            return

        selected_groups = []

        # 1. 딕셔너리를 돌면서 'on'으로 체크된 그룹만 골라냅니다.
        for g_id, data in self.group_check_vars.items():
            if data["check_var"].get() == "on":

                # 사용자가 버튼을 선택했는지 확인 (선택 안 했으면 "" 빈칸임)
                call_type = data["call_var"].get()
                if not call_type:
                    print(f"⚠️ [{data['name']}] 통화 방식을 선택하지 않았습니다!")
                    continue  # 선택 안 된 그룹은 제외하고 다음으로 넘어감

                selected_groups.append(
                    {
                        "name": data["name"],
                        "id": g_id,
                        "call_type": call_type,
                    }
                )

        # 2. 아무것도 선택 안 하고 버튼을 눌렀을 때의 방어 로직
        if not selected_groups:
            print("⚠️ 통화할 그룹을 먼저 선택해 주세요!")
            return

        # 3. 결과 출력 (추후 adb_logic과 연결할 부분)
        print("=" * 40)
        print("📞 다음 그룹으로 통화 연결을 시도합니다:")
        for g in selected_groups:
            print(f" - {g['name']} (ID: {g['id']})")
        print("=" * 40)

        # TODO: adb_logic.make_call(self.current_uuid, selected_groups) 호출

    def on_call_button(self):
        self.current_mode = "call"
        self.update_group_visibility()

    def on_msg_button(self):
        self.current_mode = "msg"
        self.update_group_visibility()  # 화면 아이콘 먼저 갱신

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
            font=("Pretendard", 14, "bold"),
            text_color=self.text_main,
        ).pack(pady=(30, 15))

        # 4. 선택형 메뉴 생성 (드롭다운 디자인 세련되게 수정)
        self.selected_project = ctk.StringVar(value=project_list[0])
        dropdown = ctk.CTkOptionMenu(
            window,
            variable=self.selected_project,
            values=project_list,
            font=("Pretendard", 13),
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            button_color=self.point_blue,
            button_hover_color="#2563EB",
            dropdown_font=("Pretendard", 12),
            height=36,
            corner_radius=self.radius,
        )
        dropdown.pack(fill="x", padx=40, pady=10)

        # 5. 적용 버튼 (초록색 포인트 컬러 적용)
        btn_apply = ctk.CTkButton(
            window,
            text="✅ 설정 적용",
            font=("Pretendard", 13, "bold"),
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
        env = self.config_data[proj_name]  # 이 env 변수에 JSON 내용이 다 들어있습니다!

        if self.current_uuid:
            self.txt_log.insert("end", "[System] 자동화 실행 중...\n")

            # 여기서 env(데이터 덩어리)를 그냥 통째로 넘겨버립니다.
            adb_logic.automate_pta_login_u2(self.current_uuid, env)

            self.txt_log.insert("end", "[System] 완료!\n")

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
            font=("Pretendard", 14, "bold"),
            text_color=self.text_main,
        ).pack(pady=(30, 15))

        # 4. 선택형 메뉴 생성 (드롭다운 디자인 세련되게 수정)
        self.selected_wifi = ctk.StringVar(value=wifi_list[0])
        dropdown = ctk.CTkOptionMenu(
            window,
            variable=self.selected_wifi,
            values=wifi_list,
            font=("Pretendard", 13),
            fg_color=self.btn_bg_light,
            text_color=self.text_main,
            button_color=self.point_blue,
            button_hover_color="#2563EB",
            dropdown_font=("Pretendard", 12),
            height=36,
            corner_radius=self.radius,
        )
        dropdown.pack(fill="x", padx=40, pady=10)

        # 5. 연결 버튼 (초록색 포인트 컬러 적용)
        btn_connect = ctk.CTkButton(
            window,
            text="✅ WiFi 연결",
            font=("Pretendard", 13, "bold"),
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

            self.btn_toggle_log.configure(
                text="■ LOG OFF", fg_color="#FEE2E2", text_color=self.danger_color
            )
            self.is_log_on = True
        else:
            adb_logic.stop_process(self.log_proc)
            self.log_file.close()  # 파일 닫기

            self.btn_toggle_log.configure(
                text="LOG ON", fg_color=self.btn_bg_secondary, text_color=self.text_main
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
                    fg_color="#FEE2E2",
                    text_color=self.danger_color,
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

            self.btn_toggle_pcap.configure(
                text="PCAPdroid ON",
                fg_color=self.btn_bg_secondary,
                text_color=self.text_main,
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
        print("앱 설치")

    def run_uninstall_app(self):
        print("앱 삭제")

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
                font=("Pretendard", 13, "bold"),
                text_color=self.point_blue,
            ).pack(fill="x", pady=(15, 5), anchor="w")

            for item in items:
                btn = ctk.CTkButton(
                    scroll_frame,
                    text=f"  {item}",
                    font=("Pretendard", 12),
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
