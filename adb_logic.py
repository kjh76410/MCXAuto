import subprocess
import os
import time
import ctypes
import threading
import re

def get_devices():
    try:
        res = subprocess.check_output(["adb", "devices"]).decode()
        return [line.split('\t')[0] for line in res.strip().split('\n') if '\tdevice' in line]
    except:
        return []

def get_model_name(uuid):
    try:
        return subprocess.check_output(['adb', '-s', uuid, 'shell', 'getprop', 'ro.product.model']).decode().strip()
    except:
        return "Unknown"

def start_mirroring_embedded(uuid, parent_hwnd, width, height):
    scrcpy_path = r"C:\scrcpy\scrcpy.exe" 
    
    if not os.path.exists(scrcpy_path):
        print("scrcpy.exe 파일을 찾을 수 없습니다. C드라이브에 scrcpy 폴더가 있는지 확인해주세요!")
        return

    window_title = f"embed_mirror_{uuid}"
    
    cmd = [
        scrcpy_path, 
        "-s", uuid, 
        "--window-title", window_title,
        "--stay-awake"
    ]
    
    subprocess.Popen(cmd)

    def swallow_window_worker():
        user32 = ctypes.windll.user32
        hwnd = 0
        
        for _ in range(50):
            time.sleep(0.1)
            hwnd = user32.FindWindowW(None, window_title)
            if hwnd:
                break
                
        if hwnd:
            GWL_STYLE = -16
            WS_CHILD = 0x40000000
            WS_CAPTION = 0x00C00000
            WS_THICKFRAME = 0x00040000
            
            style = user32.GetWindowLongW(hwnd, GWL_STYLE)
            style &= ~WS_CAPTION
            style &= ~WS_THICKFRAME
            style |= WS_CHILD
            
            user32.SetWindowLongW(hwnd, GWL_STYLE, style)
            user32.SetParent(hwnd, parent_hwnd)
            user32.MoveWindow(hwnd, 0, 0, width, height, True)
            user32.UpdateWindow(hwnd)
        else:
            print("미러링 윈도우 핸들을 찾지 못했습니다.")

    threading.Thread(target=swallow_window_worker, daemon=True).start()

def send_keyevent(uuid, keycode):
    """
    안드로이드 하드웨어 키보드 이벤트를 전송합니다.
    (3: Home, 4: Back, 187: App Switch/Recent)
    """
    try:
        subprocess.Popen(["adb", "-s", uuid, "shell", "input", "keyevent", str(keycode)])
    except Exception as e:
        print(f"Keyevent Error: {e}")

# ==========================================
# 앱 설치 및 데이터 지우기 기능 추가됨!
# ==========================================
def install_apk(uuid, apk_path):
    """PC에 있는 APK 파일을 단말기에 설치합니다."""
    try:
        print(f"설치 진행 중: {apk_path}")
        subprocess.Popen(["adb", "-s", uuid, "install", "-r", apk_path])
    except Exception as e:
        print(f"APK Install Error: {e}")

def clear_app_data(uuid, package_name):
    """지정한 패키지의 앱 데이터를 초기화합니다."""
    try:
        print(f"데이터 지우기 진행 중: {package_name}")
        subprocess.Popen(["adb", "-s", uuid, "shell", "pm", "clear", package_name])
    except Exception as e:
        print(f"Clear Data Error: {e}")

def get_current_package(uuid):
    """1. 현재 화면에 띄워진 앱의 패키지명을 알아냅니다."""
    try:
        # 안드로이드 시스템에서 현재 포커스된 창 정보 가져오기
        cmd = f'adb -s {uuid} shell dumpsys window | findstr mCurrentFocus'
        output = subprocess.check_output(cmd, shell=True).decode().strip()
        
        # 정규식으로 패키지명만 쏙 빼내기 (예: u0 com.kakao.talk/...)
        match = re.search(r'u0 ([a-zA-Z0-9_\.]+)/', output)
        if match:
            return match.group(1)
        return "알 수 없음"
    except Exception as e:
        print(f"패키지 확인 오류: {e}")
        return "알 수 없음"


def get_everytalk_version(uuid):
    """com.EveryTalk.Global 앱의 버전을 가져옵니다. (중복 버전 방어 코드 추가)"""
    try:
        cmd = ["adb", "-s", uuid, "shell", "dumpsys", "package", "com.EveryTalk.Global"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
        output = result.stdout
        
        # 찾은 버전명들을 담을 빈 리스트
        versions = [] 
        
        for line in output.splitlines():
            if "versionName=" in line:
                # 'versionName='을 없애고, 양옆의 공백도 지워서 리스트에 추가
                clean_version = line.strip().replace("versionName=", "")
                versions.append(clean_version)
                
        if versions:
            # 리스트에 담긴 버전 중 가장 첫 번째(최상단) 버전만 반환!
            return versions[0] 
            
        return "설치 안 됨"
    except Exception as e:
        print(f"버전 확인 에러: {e}")
        return "버전 확인 불가"