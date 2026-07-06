import customtkinter as ctk
from logic import adb_service
from ui import styles
import subprocess

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("QA Automation Tool")
        self.geometry("400x450") # 조금 길게 늘림
        self.configure(fg_color=styles.THEME["bg_color"])
        
        self.current_uuid = None # 현재 선택된 기기 UUID 저장용

        # 타이틀
        self.lbl_title = ctk.CTkLabel(self, text="⚡ QA DashBoard", 
                                      font=styles.THEME["font_title"], text_color=styles.THEME["text_main"])
        self.lbl_title.pack(pady=20)
        
        # 기기 정보 라벨
        self.lbl_uuid = ctk.CTkLabel(self, text="연결된 기기: 없음", font=("Consolas", 12))
        self.lbl_uuid.pack(pady=10)
        
        # 버튼 영역
        self.btn_connect = ctk.CTkButton(self, text="기기 연결 확인", fg_color=styles.THEME["primary"], command=self.check_device)
        self.btn_connect.pack(pady=10, padx=50, fill="x")
        
        self.btn_mirror = ctk.CTkButton(self, text="📱 화면 미러링", fg_color="#10b981", state="disabled", command=self.run_mirror)
        self.btn_mirror.pack(pady=10, padx=50, fill="x")

    def check_device(self):
        devices = adb_service.get_devices()
        if devices:
            self.current_uuid = devices[0]
            self.lbl_uuid.configure(text=f"UUID: {self.current_uuid}")
            self.btn_mirror.configure(state="normal") # 버튼 활성화
        else:
            self.lbl_uuid.configure(text="연결된 기기 없음")
            self.btn_mirror.configure(state="disabled")

    def run_mirror(self):
        if self.current_uuid:
            adb_service.start_mirroring(self.current_uuid)