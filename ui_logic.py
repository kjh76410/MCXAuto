import customtkinter as ctk
import adb_logic
import os
import ctypes
import sys
from tkinter import filedialog

def load_custom_font(font_filename):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    font_path = os.path.join(base_path, 'assets', 'fonts', font_filename)
    
    if os.path.exists(font_path):
        ctk.FontManager.load_font(font_path)
    else:
        print(f"⚠️ 폰트 파일을 찾을 수 없습니다: {font_path}")

load_custom_font("Pretendard-Regular.otf")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("QA Automation Dashboard")
        self.geometry("1350x850")
        
        # ==========================================
        # [Modern SaaS Light Palette (Tailwind Vibe)]
        # ==========================================
        self.bg_color = "#F3F4F6"          # 앱 전체 배경 (매우 연한 쿨그레이)
        self.sidebar_bg = "#FFFFFF"        # 사이드바 & 카드 배경 (순백색)
        self.panel_bg = "#FFFFFF"          # 우측 콘텐츠 카드 배경
        self.border_color = "#E5E7EB"      # 경계선 (연한 회색)
        
        self.text_main = "#111827"         # 메인 텍스트 (다크 차콜, 거의 검정)
        self.text_sub = "#6B7280"          # 서브 텍스트 (중간 회색)
        
        self.brand_blue = "#2563EB"        # 메인 포인트: 신뢰의 블루
        self.brand_blue_hover = "#1D4ED8"
        
        self.accent_green = "#10B981"      # 서브 포인트: 성공의 에메랄드 그린
        self.accent_green_hover = "#059669"
        
        self.btn_bg_secondary = "#F3F4F6"  # 기본 서브 버튼 (연회색)
        self.btn_hover_secondary = "#E5E7EB"
        
        self.danger_color = "#EF4444"      # 경고용 레드
        self.danger_hover = "#DC2626"
        
        self.configure(fg_color=self.bg_color) 
        self.current_uuid = None
        
        # 모던 SaaS 특유의 둥글둥글하고 부드러운 라디우스
        self.radius = 8 
        
        # ==========================================
        # [좌측 영역] 컨트롤 패널
        # ==========================================
        self.control_panel = ctk.CTkFrame(self, width=280, fg_color=self.sidebar_bg, corner_radius=self.radius, border_width=1, border_color=self.border_color)
        self.control_panel.pack(side="left", fill="y", padx=16, pady=16)
        self.control_panel.pack_propagate(False) 
        
        self.lbl_project = ctk.CTkLabel(self.control_panel, text="프로젝트: 대기 중", font=("Pretendard", 16, "bold"), text_color=self.brand_blue)
        self.lbl_project.pack(pady=(30, 15), padx=20, anchor="w")
        
        self.label = ctk.CTkLabel(self.control_panel, text="단말을 연결해주세요.", font=("Pretendard", 13), text_color=self.text_sub)
        self.label.pack(pady=(0, 20), padx=20, anchor="w") 
        
        # 기기 연결 버튼 (메인 블루 포인트)
        self.btn_connect = ctk.CTkButton(self.control_panel, text="기기 연결 확인", font=("Pretendard", 13, "bold"), fg_color=self.brand_blue, hover_color=self.brand_blue_hover, text_color="#FFFFFF", height=38, corner_radius=self.radius, command=self.check_device)
        self.btn_connect.pack(pady=4, padx=20, fill="x")
        
        self.btn_mirror = ctk.CTkButton(self.control_panel, text="화면 띄우기", font=("Pretendard", 13, "bold"), fg_color=self.btn_bg_secondary, hover_color=self.btn_hover_secondary, text_color=self.text_main, height=38, corner_radius=self.radius, state="disabled", command=self.run_mirror)
        self.btn_mirror.pack(pady=4, padx=20, fill="x")

        self.util_frame = ctk.CTkFrame(self.control_panel, fg_color="transparent")
        self.util_frame.pack(pady=(20, 4), padx=20, fill="x") 
        
        self.btn_clear_data = ctk.CTkButton(self.util_frame, text="데이터 지우기", font=("Pretendard", 12, "bold"), fg_color="transparent", border_width=1, border_color=self.border_color, hover_color=self.btn_hover_secondary, text_color=self.danger_color, height=32, corner_radius=self.radius, command=self.run_clear_data)
        self.btn_clear_data.pack(side="left", expand=True, fill="x", padx=(0, 4))
        
        self.btn_install = ctk.CTkButton(self.util_frame, text="앱 설치", font=("Pretendard", 12, "bold"), fg_color="transparent", border_width=1, border_color=self.border_color, hover_color=self.btn_hover_secondary, text_color=self.text_main, height=32, corner_radius=self.radius, command=self.run_install_app)
        self.btn_install.pack(side="right", expand=True, fill="x", padx=(4, 0))

        self.btn_env = ctk.CTkButton(self.control_panel, text="⚙️ 환경 설정", font=("Pretendard", 12, "bold"), fg_color="transparent", border_width=1, border_color=self.border_color, hover_color=self.btn_hover_secondary, text_color=self.text_main, height=32, corner_radius=self.radius, command=self.open_env_setup)
        self.btn_env.pack(pady=4, padx=20, fill="x")

        ctk.CTkFrame(self.control_panel, height=1, fg_color=self.border_color).pack(fill="x", padx=20, pady=20)

        self.action_panel = ctk.CTkScrollableFrame(self.control_panel, fg_color="transparent")
        self.action_panel.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        menu_data = {
            "Group Call": ["ReGroup", "PreArranged Group", "Chat Group"],
            "Private Call": ["Private PTT", "Private PTV", "Without Floor Control", "MCVideo Push", "MCVideo Pull", "LAL"],
            "IM": ["일반 메시지", "최대용량 메시지", "첨부 메시지 사진", "동영상", "기타문서"]
        }

        for category, items in menu_data.items():
            ctk.CTkLabel(self.action_panel, text=category.upper(), font=("Pretendard", 11, "bold"), text_color=self.text_sub, anchor="w").pack(fill="x", pady=(15, 5), padx=10)
            for item in items:
                btn = ctk.CTkButton(
                    self.action_panel, text=f"  {item}", font=("Pretendard", 13), 
                    fg_color="transparent", text_color=self.text_main, hover_color=self.btn_hover_secondary, 
                    anchor="w", height=32, corner_radius=self.radius,
                    command=lambda c=category, i=item: self.execute_action(c, i)
                )
                btn.pack(fill="x", pady=1, padx=4)


        # ==========================================
        # [우측 영역] 메인 콘텐츠 대시보드
        # ==========================================
        self.right_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.right_panel.pack(side="right", expand=True, fill="both", padx=(0, 16), pady=16)

        # --- 상단 헤더 영역 ---
        self.top_header = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.top_header.pack(fill="x", pady=(0, 16))

        self.auto_btn_frame = ctk.CTkFrame(self.top_header, fg_color="transparent")
        self.auto_btn_frame.pack(side="left", fill="y", padx=(0, 16))
        
        # 자동화 실행 버튼 (초록색 포인트)
        self.btn_run_scenario = ctk.CTkButton(self.auto_btn_frame, text="▶ 시나리오 실행", font=("Pretendard", 13, "bold"), fg_color=self.accent_green, hover_color=self.accent_green_hover, text_color="#FFFFFF", width=150, height=34, corner_radius=self.radius, command=self.run_automation)
        self.btn_run_scenario.pack(pady=(0, 4))
        
        self.btn_stop_scenario = ctk.CTkButton(self.auto_btn_frame, text="⏹ 진행 중지", font=("Pretendard", 13, "bold"), fg_color="transparent", border_width=1, border_color=self.danger_color, text_color=self.danger_color, hover_color="#FEE2E2", width=150, height=34, corner_radius=self.radius, command=self.stop_automation)
        self.btn_stop_scenario.pack(pady=4)
        
        self.btn_report = ctk.CTkButton(self.auto_btn_frame, text="📊 QA 리포트", font=("Pretendard", 13, "bold"), fg_color=self.btn_bg_secondary, text_color=self.text_main, hover_color=self.btn_hover_secondary, width=150, height=34, corner_radius=self.radius, command=self.generate_report)
        self.btn_report.pack(pady=(4, 0))

        # 정보 블록 카드
        self.info_card = ctk.CTkFrame(self.top_header, fg_color=self.panel_bg, corner_radius=self.radius, border_width=1, border_color=self.border_color)
        self.info_card.pack(side="left", expand=True, fill="both")

        self.info_row1 = ctk.CTkFrame(self.info_card, fg_color="transparent")
        self.info_row1.pack(expand=True, fill="both", padx=24, pady=(16, 4))
        
        self.lbl_uuid = ctk.CTkLabel(self.info_row1, text="UUID: 대기 중", font=("Consolas", 12), text_color=self.text_sub)
        self.lbl_uuid.pack(side="left", expand=True)
        self.lbl_os = ctk.CTkLabel(self.info_row1, text="OS: -", font=("Pretendard", 13), text_color=self.text_main)
        self.lbl_os.pack(side="left", expand=True)
        self.lbl_sdk = ctk.CTkLabel(self.info_row1, text="API: -", font=("Pretendard", 13), text_color=self.text_main)
        self.lbl_sdk.pack(side="left", expand=True)
        self.lbl_hw = ctk.CTkLabel(self.info_row1, text="HW: -", font=("Pretendard", 13), text_color=self.text_main)
        self.lbl_hw.pack(side="left", expand=True)

        self.info_row2 = ctk.CTkFrame(self.info_card, fg_color="transparent")
        self.info_row2.pack(expand=True, fill="both", padx=24, pady=(4, 16))
        
        self.lbl_version = ctk.CTkLabel(self.info_row2, text="앱 버전: 대기 중", font=("Pretendard", 14, "bold"), text_color=self.text_main)
        self.lbl_version.pack(side="left", expand=True)
        self.lbl_battery = ctk.CTkLabel(self.info_row2, text="🔋 배터리: -", font=("Pretendard", 13, "bold"), text_color=self.accent_green) 
        self.lbl_battery.pack(side="left", expand=True)
        self.lbl_network = ctk.CTkLabel(self.info_row2, text="📶 네트워크: -", font=("Pretendard", 13, "bold"), text_color=self.brand_blue) 
        self.lbl_network.pack(side="left", expand=True)


        # ==========================================
        # [메인 콘텐츠 영역] 미러링(좌) / 로그(우) 분할
        # ==========================================
        self.main_content = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.main_content.pack(expand=True, fill="both")

        # --- [좌측] 미러링 영역 ---
        self.mirror_section = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.mirror_section.pack(side="left", expand=True, fill="both", padx=(0, 16))

        self.mirror_top_bar = ctk.CTkFrame(self.mirror_section, height=44, fg_color=self.panel_bg, corner_radius=self.radius, border_width=1, border_color=self.border_color)
        self.mirror_top_bar.pack(fill="x", side="top", pady=(0, 8))
        
        ctk.CTkLabel(self.mirror_top_bar, text="Device Preview", font=("Pretendard", 12, "bold"), text_color=self.text_sub).pack(side="left", padx=16)
        
        self.btn_record = ctk.CTkButton(self.mirror_top_bar, text="🎥 녹화", font=("Pretendard", 12), fg_color="transparent", text_color=self.text_main, hover_color=self.btn_hover_secondary, width=60, height=28, corner_radius=self.radius, command=self.toggle_record)
        self.btn_record.pack(side="right", padx=10, pady=8)
        self.btn_capture = ctk.CTkButton(self.mirror_top_bar, text="📸 캡쳐", font=("Pretendard", 12), fg_color="transparent", text_color=self.text_main, hover_color=self.btn_hover_secondary, width=60, height=28, corner_radius=self.radius, command=self.capture_screen)
        self.btn_capture.pack(side="right", padx=0, pady=8)

        # 미러링 영역 (화면이 꺼졌을 때를 위해 차분한 다크 네이비톤)
        self.mirror_container = ctk.CTkFrame(self.mirror_section, fg_color="#1E293B", corner_radius=self.radius) 
        self.mirror_container.pack(expand=True, fill="both", pady=(0, 8))
        self.lbl_placeholder = ctk.CTkLabel(self.mirror_container, text="대기 중...", font=("Pretendard", 14), text_color="#94A3B8")
        self.lbl_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        self.nav_bar = ctk.CTkFrame(self.mirror_section, height=52, fg_color=self.panel_bg, corner_radius=self.radius, border_width=1, border_color=self.border_color)
        self.nav_bar.pack(fill="x", side="bottom")
        
        self.nav_inner = ctk.CTkFrame(self.nav_bar, fg_color="transparent")
        self.nav_inner.pack(expand=True)
        
        ctk.CTkButton(self.nav_inner, text="Ⅲ", width=60, height=36, font=("Arial", 16, "bold"), fg_color="transparent", text_color=self.text_sub, hover_color=self.btn_hover_secondary, corner_radius=self.radius, command=lambda: self.press_key(187)).pack(side="left", padx=10, pady=8)
        ctk.CTkButton(self.nav_inner, text="⬤", width=60, height=36, font=("Arial", 16), fg_color="transparent", text_color=self.text_sub, hover_color=self.btn_hover_secondary, corner_radius=self.radius, command=lambda: self.press_key(3)).pack(side="left", padx=10, pady=8)
        ctk.CTkButton(self.nav_inner, text="◀", width=60, height=36, font=("Arial", 16), fg_color="transparent", text_color=self.text_sub, hover_color=self.btn_hover_secondary, corner_radius=self.radius, command=lambda: self.press_key(4)).pack(side="left", padx=10, pady=8)


        # --- [우측] 터미널/로그 영역 ---
        self.log_section = ctk.CTkFrame(self.main_content, width=440, fg_color=self.panel_bg, corner_radius=self.radius, border_width=1, border_color=self.border_color)
        self.log_section.pack(side="right", fill="y")
        self.log_section.pack_propagate(False)

        self.log_ctrl_frame = ctk.CTkFrame(self.log_section, fg_color="transparent")
        self.log_ctrl_frame.pack(fill="x", padx=16, pady=16)
        
        self.btn_toggle_log = ctk.CTkButton(self.log_ctrl_frame, text="LOG ON", font=("Pretendard", 12, "bold"), fg_color=self.btn_bg_secondary, text_color=self.text_main, hover_color=self.btn_hover_secondary, height=34, corner_radius=self.radius, command=self.toggle_log)
        self.btn_toggle_log.pack(side="left", expand=True, fill="x", padx=(0, 6))
        
        self.btn_toggle_pcap = ctk.CTkButton(self.log_ctrl_frame, text="PCAP ON", font=("Pretendard", 12, "bold"), fg_color=self.btn_bg_secondary, text_color=self.text_main, hover_color=self.btn_hover_secondary, height=34, corner_radius=self.radius, command=self.toggle_pcap)
        self.btn_toggle_pcap.pack(side="right", expand=True, fill="x", padx=(6, 0))

        # 로그 검색 바 (아주 밝은 배경으로 분리)
        self.log_search_frame = ctk.CTkFrame(self.log_section, fg_color="transparent")
        self.log_search_frame.pack(fill="x", padx=16, pady=(0, 10))
        
        self.entry_search = ctk.CTkEntry(self.log_search_frame, placeholder_text="🔍 검색 필터 (예: INVITE, Exception)", font=("Pretendard", 13), height=34, fg_color="#F9FAFB", border_color=self.border_color, text_color=self.text_main, corner_radius=self.radius)
        self.entry_search.pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        self.chk_error = ctk.CTkCheckBox(self.log_search_frame, text="Error Only", font=("Pretendard", 12, "bold"), text_color=self.danger_color, fg_color=self.danger_color, hover_color=self.danger_hover, border_width=1, corner_radius=4, width=80)
        self.chk_error.pack(side="right")

        # 텍스트 박스는 시인성을 위해 아주 옅은 회색 배경 처리
        ctk.CTkLabel(self.log_section, text="System Logcat", font=("Pretendard", 12, "bold"), text_color=self.text_sub, anchor="w").pack(fill="x", padx=16, pady=(4, 0))
        self.txt_log = ctk.CTkTextbox(self.log_section, font=("Consolas", 12), fg_color="#F9FAFB", text_color=self.text_main, border_width=1, border_color=self.border_color, corner_radius=self.radius)
        self.txt_log.pack(expand=True, fill="both", padx=16, pady=(2, 10))
        self.txt_log.insert("1.0", "로그 수집 대기 중...\n")

        ctk.CTkLabel(self.log_section, text="PCAP Dump", font=("Pretendard", 12, "bold"), text_color=self.text_sub, anchor="w").pack(fill="x", padx=16, pady=(4, 0))
        self.txt_pcap = ctk.CTkTextbox(self.log_section, font=("Consolas", 12), fg_color="#F9FAFB", text_color=self.text_main, border_width=1, border_color=self.border_color, corner_radius=self.radius)
        self.txt_pcap.pack(expand=True, fill="both", padx=16, pady=(2, 16))
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
            model = adb_logic.get_model_name(self.current_uuid)
            os_version = adb_logic.get_os_version(self.current_uuid)
            sdk_version = adb_logic.get_sdk_version(self.current_uuid)
            hw_version = adb_logic.get_hw_version(self.current_uuid)
            version_name = adb_logic.get_everytalk_version(self.current_uuid)
            
            project_name = "EveryTalk Global" 
            battery_status = "95%"
            network_status = "LTE (SKT)" 

            self.label.configure(text=f"연결됨: {model}", text_color=self.accent_green) 
            
            self.lbl_uuid.configure(text=f"UUID: {self.current_uuid}", text_color=self.text_main)
            self.lbl_os.configure(text=f"OS: Android {os_version}")
            self.lbl_sdk.configure(text=f"API: {sdk_version}")
            self.lbl_hw.configure(text=f"HW: {hw_version}")
            self.lbl_version.configure(text=f"앱 버전: {version_name}")
            self.lbl_battery.configure(text=f"🔋 배터리: {battery_status}", text_color=self.accent_green)
            self.lbl_network.configure(text=f"📶 {network_status}", text_color=self.brand_blue)
            self.lbl_project.configure(text=f"프로젝트: {project_name}")
            
            self.btn_mirror.configure(state="normal", fg_color=self.brand_blue, text_color="#FFFFFF", hover_color=self.brand_blue_hover)
        else:
            self.current_uuid = None
            self.label.configure(text="연결된 단말 없음", text_color=self.text_sub)
            self.lbl_uuid.configure(text="UUID: 없음", text_color=self.text_sub)
            self.lbl_os.configure(text="OS: -")
            self.lbl_sdk.configure(text="API: -")
            self.lbl_hw.configure(text="HW: -")
            self.lbl_version.configure(text="앱 버전: -")
            self.lbl_battery.configure(text="🔋 배터리: -", text_color=self.text_main)
            self.lbl_network.configure(text="📶 네트워크: -", text_color=self.text_main)
            self.lbl_project.configure(text="프로젝트: 대기 중")
            self.btn_mirror.configure(state="disabled", fg_color=self.btn_bg_secondary, text_color=self.text_sub)

    def run_mirror(self):
        if self.current_uuid:
            self.lbl_placeholder.place_forget()
            self.update_idletasks()
            width = self.mirror_container.winfo_width()
            height = self.mirror_container.winfo_height()
            if width <= 1 or height <= 1:
                width, height = 400, 600
            parent_hwnd = self.mirror_container.winfo_id()
            adb_logic.start_mirroring_embedded(self.current_uuid, parent_hwnd, width, height)

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
        file_path = filedialog.askopenfilename(title="APK 파일 선택", filetypes=[("APK", "*.apk"), ("All", "*.*")])
        if file_path:
            adb_logic.install_apk(self.current_uuid, file_path)

    def open_env_setup(self):
        print("⚙️ 테스트 환경 설정 창을 엽니다.")

    def capture_screen(self):
        if not self.current_uuid:
            return
        print("📸 화면 캡쳐를 실행합니다.")

    def toggle_record(self):
        if not self.current_uuid:
            return
        print("🎥 동영상 녹화를 시작/종료합니다.")

    def run_automation(self):
        if not self.current_uuid:
            print("⚠️ 기기가 연결되지 않았습니다.")
            return
        print("🚀 [자동화 시작] 시나리오를 연속 실행합니다...")
        
    def stop_automation(self):
        print("⏹ [자동화 중지] 시나리오를 강제 중지합니다.")
        
    def generate_report(self):
        print("📊 [리포트 생성] 테스트 로그를 취합합니다.")

    def toggle_log(self):
        if not self.is_log_on:
            self.btn_toggle_log.configure(text="■ LOG OFF", fg_color="#FEE2E2", border_width=1, border_color=self.danger_color, text_color=self.danger_color, hover_color="#FECACA")
            self.txt_log.insert("end", "[System] 실시간 로그 수집 시작...\n")
            self.txt_log.see("end")
            self.is_log_on = True
        else:
            self.btn_toggle_log.configure(text="LOG ON", fg_color=self.btn_bg_secondary, border_width=0, text_color=self.text_main, hover_color=self.btn_hover_secondary)
            self.txt_log.insert("end", "[System] 로그 수집 중지됨.\n")
            self.txt_log.see("end")
            self.is_log_on = False

    def toggle_pcap(self):
        if not self.is_pcap_on:
            self.btn_toggle_pcap.configure(text="■ PCAP OFF", fg_color="#FEE2E2", border_width=1, border_color=self.danger_color, text_color=self.danger_color, hover_color="#FECACA")
            self.txt_pcap.insert("end", "[Network] 패킷 덤프 시작 (tcpdump)...\n")
            self.txt_pcap.see("end")
            self.is_pcap_on = True
        else:
            self.btn_toggle_pcap.configure(text="PCAP ON", fg_color=self.btn_bg_secondary, border_width=0, text_color=self.text_main, hover_color=self.btn_hover_secondary)
            self.txt_pcap.insert("end", "[Network] 패킷 덤프 중지됨.\n")
            self.txt_pcap.see("end")
            self.is_pcap_on = False