import customtkinter as ctk
import adb_logic
import os
import ctypes
import sys
from tkinter import filedialog
from file_manager import FileManager

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
        
        # [Modern SaaS Light Palette]
        self.bg_color = "#F3F4F6"
        self.sidebar_bg = "#FFFFFF"
        self.panel_bg = "#FFFFFF"
        self.border_color = "#E5E7EB"
        
        self.text_main = "#111827"
        self.text_sub = "#6B7280"
        
        self.brand_blue = "#2563EB"
        self.brand_blue_hover = "#1D4ED8"
        
        self.accent_green = "#10B981"
        self.accent_green_hover = "#059669"
        
        self.btn_bg_secondary = "#F3F4F6"
        self.btn_hover_secondary = "#E5E7EB"
        
        self.danger_color = "#EF4444"
        self.danger_hover = "#DC2626"
        
        self.configure(fg_color=self.bg_color) 
        self.current_uuid = None
        
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
        
        self.btn_connect = ctk.CTkButton(self.control_panel, text="🔄 기기 연결 및 화면 띄우기", font=("Pretendard", 13, "bold"), fg_color=self.brand_blue, hover_color=self.brand_blue_hover, text_color="#FFFFFF", height=42, corner_radius=self.radius, command=self.check_device)
        self.btn_connect.pack(pady=4, padx=20, fill="x")

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

        header_frame = ctk.CTkFrame(self.control_panel, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(10, 0))

        # 2. 제목 라벨 (왼쪽 배치)
        ctk.CTkLabel(header_frame, text="실시간 그룹 목록", font=("Pretendard", 14, "bold")).pack(side="left")

        # 3. 새로고침 버튼 (오른쪽 배치)
        # 버튼을 작게 만들어서 아이콘 느낌으로 배치합니다
        self.btn_refresh = ctk.CTkButton(
            header_frame, 
            text="🔄", 
            width=30, 
            fg_color="transparent", # 배경 투명하게
            hover_color="#E0E0E0",  # 마우스 올리면 색상 변경
            text_color=self.text_main,
            command=self.refresh_group_list # 함수 연결
        )
        self.btn_refresh.pack(side="right")

        # 4. 리스트 영역 (기존 코드 아래에 배치)
        self.group_list_frame = ctk.CTkScrollableFrame(self.control_panel, height=200)
        self.group_list_frame.pack(fill="x", padx=20, pady=5)

        # 기존 그룹 목록 리스트 아래에 추가
        self.my_id_label = ctk.CTkLabel(self.control_panel, text="내 Call ID: -", font=("Pretendard", 12, "bold"))
        self.my_id_label.pack(fill="x", padx=20, pady=(10, 5))

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
        
        # 👇👇👇 [변경점] 정보 1열 라벨 완벽 정리 👇👇👇
        self.lbl_uuid = ctk.CTkLabel(self.info_row1, text="UUID: 대기 중", font=("Consolas", 12), text_color=self.text_sub)
        self.lbl_uuid.pack(side="left", expand=True)
        
        self.lbl_model = ctk.CTkLabel(self.info_row1, text="모델: -", font=("Pretendard", 13), text_color=self.text_main)
        self.lbl_model.pack(side="left", expand=True)
        
        self.lbl_os_build = ctk.CTkLabel(self.info_row1, text="OS 버전: -", font=("Pretendard", 13), text_color=self.text_main)
        self.lbl_os_build.pack(side="left", expand=True)
        
        self.lbl_android_ver = ctk.CTkLabel(self.info_row1, text="Android 버전: -", font=("Pretendard", 13), text_color=self.text_main)
        self.lbl_android_ver.pack(side="left", expand=True)

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

        self.log_search_frame = ctk.CTkFrame(self.log_section, fg_color="transparent")
        self.log_search_frame.pack(fill="x", padx=16, pady=(0, 10))
        
        self.entry_search = ctk.CTkEntry(self.log_search_frame, placeholder_text="🔍 검색 필터 (예: INVITE, Exception)", font=("Pretendard", 13), height=34, fg_color="#F9FAFB", border_color=self.border_color, text_color=self.text_main, corner_radius=self.radius)
        self.entry_search.pack(side="left", expand=True, fill="x", padx=(0, 10))
        
        self.chk_error = ctk.CTkCheckBox(self.log_search_frame, text="Error Only", font=("Pretendard", 12, "bold"), text_color=self.danger_color, fg_color=self.danger_color, hover_color=self.danger_hover, border_width=1, corner_radius=4, width=80)
        self.chk_error.pack(side="right")

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
            
            # 👇👇👇 [변경점] 새로운 정보들 불러오기 👇👇👇
            model = adb_logic.get_model_name(self.current_uuid)
            android_version = adb_logic.get_os_version(self.current_uuid) # "12" 같은 안드로이드 버전
            
            # 방금 adb_logic에 추가한 함수를 호출합니다!
            try:
                os_build = adb_logic.get_build_image_version(self.current_uuid) 
            except AttributeError:
                os_build = "함수 누락됨"
                
            version_name = adb_logic.get_everytalk_version(self.current_uuid)
            
            project_name = "EveryTalk Global" 
            battery_status = "95%"
            network_status = "LTE (SKT)" 

            self.label.configure(text=f"연결됨: {model}", text_color=self.accent_green) 
            
            # 👇👇👇 UI 텍스트 업데이트 👇👇👇
            self.lbl_uuid.configure(text=f"UUID: {self.current_uuid}", text_color=self.text_main)
            self.lbl_model.configure(text=f"모델: {model}")
            self.lbl_os_build.configure(text=f"OS 버전: {os_build}")
            self.lbl_android_ver.configure(text=f"Android 버전: {android_version}")
            
            self.lbl_version.configure(text=f"앱 버전: {version_name}")
            self.lbl_battery.configure(text=f"🔋 배터리: {battery_status}", text_color=self.accent_green)
            self.lbl_network.configure(text=f"📶 {network_status}", text_color=self.brand_blue)
            self.lbl_project.configure(text=f"프로젝트: {project_name}")
            
            # 버튼 한 번에 화면 미러링까지 실행!
            self.run_mirror()

        else:
            self.current_uuid = None
            self.label.configure(text="연결된 단말 없음", text_color=self.text_sub)
            self.lbl_uuid.configure(text="UUID: 없음", text_color=self.text_sub)
            self.lbl_model.configure(text="모델: -")
            self.lbl_os_build.configure(text="OS 버전: -")
            self.lbl_android_ver.configure(text="Android 버전: -")
            self.lbl_version.configure(text="앱 버전: -")
            self.lbl_battery.configure(text="🔋 배터리: -", text_color=self.text_main)
            self.lbl_network.configure(text="📶 네트워크: -", text_color=self.text_main)
            self.lbl_project.configure(text="프로젝트: 대기 중")

    def refresh_group_list(self):
        if not self.current_uuid:
            print("[Debug] ❌ 기기가 연결되지 않았습니다.")
            return
        
        print("[Debug] 1. 파일 pull 시작...")
        path = FileManager.pull_profile_xml(self.current_uuid)
        
        # 파일이 PC 폴더에 생겼는지 확인
        if not os.path.exists(path):
            print(f"[Debug] ❌ 파일이 PC에 생성되지 않았습니다. 경로 확인: {os.path.abspath(path)}")
            return
        else:
            print(f"[Debug] ✅ 파일 존재 확인: {os.path.abspath(path)}")

        print("[Debug] 2. XML 파싱 시작...")
        groups = FileManager.parse_group_list(path)
        print(f"[Debug] ✅ 파싱 결과: {groups}") # 여기서 [] 라고 뜨는지, 아니면 그룹 목록이 뜨는지 확인!

        # 1. 새로 추가: 내 Call ID 가져오기
        my_id = FileManager.parse_my_call_id(path)
        
        # 2. 새로 추가: 라벨 텍스트 업데이트
        self.my_id_label.configure(text=f"내 Call ID: {my_id}")

        if not groups:
            print("[Debug] ⚠️ 결과가 비어있습니다. 파일 내용을 확인해보세요.")
            return

        # UI 갱신
        for widget in self.group_list_frame.winfo_children():
            widget.destroy()
            
        for g_info in groups:
            btn = ctk.CTkButton(self.group_list_frame, text=g_info, fg_color="transparent", 
                                text_color=self.text_main, hover_color=self.btn_hover_secondary,
                                anchor="w", height=30, command=lambda g=g_info: self.on_group_selected(g))
            btn.pack(fill="x", padx=10, pady=2)

    def on_group_selected(self, group_info):
        print(f"▶ 선택한 그룹: {group_info}")
        # 여기서 추후 그룹별 PTT 명령 등을 연결하시면 됩니다!

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