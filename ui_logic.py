import customtkinter as ctk
import adb_logic
from tkinter import filedialog

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("QA Automation Dashboard")
        self.geometry("1100x750") # 메뉴가 많아져서 창 크기를 살짝 더 키웠습니다.
        self.configure(fg_color="#f8fafc") 
        
        self.current_uuid = None
        
        # ==========================================
        # [좌측 영역] 컨트롤 패널 카드
        # ==========================================
        self.control_panel = ctk.CTkFrame(self, width=320, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#e2e8f0")
        self.control_panel.pack(side="left", fill="y", padx=20, pady=20)
        self.control_panel.pack_propagate(False) 
        
        # 1. 상단: 상태 및 연결 버튼
        self.lbl_title = ctk.CTkLabel(self.control_panel, text="⚡ DASHBOARD", font=("Pretendard", 20, "bold"), text_color="#4f46e5")
        self.lbl_title.pack(pady=(30, 20))
        
        self.label = ctk.CTkLabel(self.control_panel, text="단말을 연결해주세요.", font=("Pretendard", 14, "bold"), text_color="#1e293b")
        self.label.pack(pady=(0, 5))
        
        self.lbl_uuid = ctk.CTkLabel(self.control_panel, text="UUID: 없음", font=("Consolas", 11), text_color="#64748b")
        self.lbl_uuid.pack(pady=(0, 20))

        self.lbl_version = ctk.CTkLabel(self.control_panel, text="앱 버전: 알 수 없음", font=("Pretendard", 12, "bold"), text_color="#ea580c")
        self.lbl_version.pack(pady=(0, 20))

        
        self.btn_connect = ctk.CTkButton(self.control_panel, text="🔄 기기 연결 확인", font=("Pretendard", 13, "bold"), fg_color="#4f46e5", hover_color="#4338ca", height=40, command=self.check_device)
        self.btn_connect.pack(pady=5, padx=20, fill="x")
        
        self.btn_mirror = ctk.CTkButton(self.control_panel, text="📱 화면 띄우기", font=("Pretendard", 13, "bold"), fg_color="#10b981", hover_color="#059669", height=40, state="disabled", command=self.run_mirror)
        self.btn_mirror.pack(pady=5, padx=20, fill="x")

    # 버튼들을 눈에 띄게 파란색 계열(#3b82f6)로 설정했습니다.
        self.btn_ptt = ctk.CTkButton(self.control_panel, text="▶ PTT APP", font=("Pretendard", 12, "bold"), fg_color="#3b82f6", hover_color="#2563eb", height=35, command=lambda: self.launch_app("PTT APP"))
        self.btn_ptt.pack(pady=(15, 3), padx=20, fill="x")
        
        self.btn_voip = ctk.CTkButton(self.control_panel, text="▶ VoIP PTT", font=("Pretendard", 12, "bold"), fg_color="#3b82f6", hover_color="#2563eb", height=35, command=lambda: self.launch_app("VoIP PTT"))
        self.btn_voip.pack(pady=3, padx=20, fill="x")
        
        self.btn_dmr = ctk.CTkButton(self.control_panel, text="▶ DMR APP", font=("Pretendard", 12, "bold"), fg_color="#3b82f6", hover_color="#2563eb", height=35, command=lambda: self.launch_app("DMR APP"))
        self.btn_dmr.pack(pady=(3, 5), padx=20, fill="x")

# 버튼 2개를 나란히 묶어줄 가로 프레임
        self.util_frame = ctk.CTkFrame(self.control_panel, fg_color="transparent")
        self.util_frame.pack(pady=(5, 10), padx=20, fill="x")
        
        # 데이터 지우기 버튼 (빨간색 계열)
        self.btn_clear_data = ctk.CTkButton(self.util_frame, text="🗑 데이터 지우기", font=("Pretendard", 12, "bold"), fg_color="#ef4444", hover_color="#dc2626", height=32, command=self.run_clear_data)
        self.btn_clear_data.pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        # 앱 설치 버튼 (주황색 계열)
        self.btn_install = ctk.CTkButton(self.util_frame, text="📦 앱 설치", font=("Pretendard", 12, "bold"), fg_color="#f59e0b", hover_color="#d97706", height=32, command=self.run_install_app)
        self.btn_install.pack(side="right", expand=True, fill="x", padx=(5, 0))



        # 구분선
        ctk.CTkFrame(self.control_panel, height=2, fg_color="#f1f5f9").pack(fill="x", padx=20, pady=15)

        # 2. 하단: 테스트 액션 스크롤 메뉴 (요청하신 메뉴 추가)
        self.action_panel = ctk.CTkScrollableFrame(self.control_panel, fg_color="transparent")
        self.action_panel.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # 메뉴 구성 데이터
        menu_data = {
            "📞 Group Call": ["ReGroup", "PreArranged Group", "Chat Group"],
            "👤 Private Call": ["Private PTT", "Private PTV", "Without Floor Control", "MCVideo Push", "MCVideo Pull", "LAL"],
            "💬 IM": ["일반 메시지", "최대용량 메시지", "첨부 메시지 사진", "동영상", "기타문서"]
        }

        # 메뉴 동적 생성 로직
        for category, items in menu_data.items():
            # 카테고리 제목
            ctk.CTkLabel(self.action_panel, text=category, font=("Pretendard", 14, "bold"), text_color="#1e293b", anchor="w").pack(fill="x", pady=(15, 5), padx=5)
            # 하위 버튼들
            for item in items:
                # 클릭 시 어떤 테스트를 실행할지 알 수 있게 람다 함수로 묶음
                btn = ctk.CTkButton(
                    self.action_panel, text=f"  - {item}", font=("Pretendard", 12), 
                    fg_color="#f8fafc", text_color="#475569", hover_color="#e2e8f0", 
                    anchor="w", height=32,
                    command=lambda c=category, i=item: self.execute_action(c, i)
                )
                btn.pack(fill="x", pady=2, padx=10)


        # ==========================================
        # [우측 영역] 미러링 & 네비게이션 바
        # ==========================================
        self.right_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.right_panel.pack(side="right", expand=True, fill="both", padx=(0, 20), pady=20)

        # 1. 미러링 화면 컨테이너
        self.mirror_container = ctk.CTkFrame(self.right_panel, fg_color="#1e293b", corner_radius=14)
        self.mirror_container.pack(expand=True, fill="both", pady=(0, 15))
        
        self.lbl_placeholder = ctk.CTkLabel(self.mirror_container, text="대기 중...", font=("Pretendard", 14), text_color="#94a3b8")
        self.lbl_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # 2. 안드로이드 하단 소프트키 네비게이션 바
        self.nav_bar = ctk.CTkFrame(self.right_panel, height=60, fg_color="#ffffff", corner_radius=14, border_width=1, border_color="#e2e8f0")
        self.nav_bar.pack(fill="x", side="bottom")
        
        # 버튼들을 가운데 정렬하기 위한 내부 프레임
        self.nav_inner = ctk.CTkFrame(self.nav_bar, fg_color="transparent")
        self.nav_inner.pack(expand=True)

        # Recent(187), Home(3), Back(4)
        ctk.CTkButton(self.nav_inner, text="Ⅲ", width=60, height=40, font=("Arial", 16, "bold"), fg_color="transparent", text_color="#475569", hover_color="#f1f5f9", command=lambda: self.press_key(187)).pack(side="left", padx=15, pady=10)
        ctk.CTkButton(self.nav_inner, text="⬤", width=60, height=40, font=("Arial", 16), fg_color="transparent", text_color="#475569", hover_color="#f1f5f9", command=lambda: self.press_key(3)).pack(side="left", padx=15, pady=10)
        ctk.CTkButton(self.nav_inner, text="◀", width=60, height=40, font=("Arial", 16), fg_color="transparent", text_color="#475569", hover_color="#f1f5f9", command=lambda: self.press_key(4)).pack(side="left", padx=15, pady=10)

    # ==========================================
    # 기능 동작 메서드들
    # ==========================================
    def check_device(self):
        devices = adb_logic.get_devices()
        if devices:
            self.current_uuid = devices[0]
            model = adb_logic.get_model_name(self.current_uuid)

            version_name = adb_logic.get_everytalk_version(self.current_uuid)

            self.label.configure(text=f"연결됨: {model}")
            self.lbl_uuid.configure(text=f"UUID: {self.current_uuid}")

            self.lbl_version.configure(text=f"앱 버전: {version_name}")

            self.btn_mirror.configure(state="normal")
        else:
            self.current_uuid = None
            self.label.configure(text="연결된 단말 없음")
            self.lbl_uuid.configure(text="UUID: 없음")

            self.lbl_version.configure(text="앱 버전: 알 수 없음")

            self.btn_mirror.configure(state="disabled")

    def run_mirror(self):
        if self.current_uuid:
            self.lbl_placeholder.place_forget()
            self.update_idletasks()
            width = self.mirror_container.winfo_width()
            height = self.mirror_container.winfo_height()
            
            if width <= 1 or height <= 1:
                width, height = 610, 610
                
            parent_hwnd = self.mirror_container.winfo_id()
            adb_logic.start_mirroring_embedded(self.current_uuid, parent_hwnd, width, height)

    def press_key(self, keycode):
        """하단 네비게이션 바 클릭 시 ADB로 키 전송"""
        if self.current_uuid:
            adb_logic.send_keyevent(self.current_uuid, keycode)
        else:
            print("기기가 연결되어 있지 않습니다.")

    def execute_action(self, category, item):
        """좌측 사이드바 테스트 항목 클릭 시 실행될 동작"""
        print(f"▶ 테스트 실행 요청: [{category}] -> {item}")
        # 나중에 여기에 Appium 연동 코드나 Python 테스트 스크립트 실행 코드를 연결하시면 됩니다!
        # 예: subprocess.Popen(["python", "tests/group_call_regroup.py", "--uuid", self.current_uuid])

    # ui_logic.py 의 맨 아래쪽에 추가
    def launch_app(self, app_name):
        print(f"[{app_name}] 실행 명령이 클릭되었습니다!")
        # 나중에 여기에 진짜 앱 패키지명(com.xxx.xxx)을 넣어서 
        # adb_logic.py 를 통해 앱을 켜는 로직을 연결할 수 있습니다.

    # --- ui_logic.py 맨 아래 (기존 함수들 밑에) 추가 ---

    def run_clear_data(self):
        if not self.current_uuid:
            print("⚠️ 단말이 연결되어 있지 않습니다.")
            return
            
        # 임시로 PTT APP의 패키지명(예시)을 넣었습니다. 진짜 패키지명으로 나중에 바꾸시면 됩니다!
        target_package = "com.test.pttapp" 
        adb_logic.clear_app_data(self.current_uuid, target_package)
        print(f"✅ [{target_package}] 데이터 지우기 명령을 보냈습니다.")

    def run_install_app(self):
        if not self.current_uuid:
            print("⚠️ 단말이 연결되어 있지 않습니다.")
            return

        # 윈도우 파일 탐색기를 열어 .apk 파일만 선택하게 합니다.
        file_path = filedialog.askopenfilename(
            title="설치할 APK 파일 선택",
            filetypes=[("APK Files", "*.apk"), ("All Files", "*.*")]
        )
        
        if file_path:
            adb_logic.install_apk(self.current_uuid, file_path)
            print(f"✅ APK 설치 명령을 보냈습니다: {file_path}")