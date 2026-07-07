import os
import time
import ctypes
import threading
import re
import subprocess
import platform
import uiautomator2 as u2

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
    """미러링 프로세스를 실행하고 윈도우 스왈로우 스레드를 시작하는 함수"""
    try:
        # 창 제목을 기기 UUID로 고유하게 설정
        window_title = f"Mirror_{uuid}"
        
        cmd = [
            r"C:\scrcpy\scrcpy.exe",
            "-s", uuid,
            "--window-title", window_title, 
            "--window-width", str(width),
            "--window-height", str(height),
            "--window-borderless",
            "--no-audio"
        ]
        
        # 1. scrcpy 실행
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # 2. 창 낚아채기 스레드 실행 (크기 정보 width, height도 같이 넘겨줍니다!)
        thread = threading.Thread(
            target=swallow_window_worker, 
            args=(window_title, parent_hwnd, width, height), 
            daemon=True
        )
        thread.start()
        
    except Exception as e:
        print(f"⚠️ 미러링 실행 중 오류 발생: {e}")

def swallow_window_worker(window_title, parent_hwnd, width, height):
    """scrcpy 창이 뜨기를 기다렸다가 Tkinter 프레임 안으로 집어넣는 함수"""
    user32 = ctypes.windll.user32
    scrcpy_hwnd = 0

    # 1. 창이 뜰 때까지 대기
    for _ in range(50):
        scrcpy_hwnd = user32.FindWindowW(None, window_title)
        if scrcpy_hwnd:
            break
        time.sleep(0.1)

    if scrcpy_hwnd:
        # 🌟 렌더링 준비 시간 확보
        time.sleep(0.5) 
        
        GWL_STYLE = -16
        WS_CHILD = 0x40000000
        WS_VISIBLE = 0x10000000
        WS_CLIPCHILDREN = 0x02000000  # ✨ [핵심] 자식 창 영역은 배경색으로 덮어쓰지 않음!

        # 2. 부모 프레임(Tkinter)에 방어막(WS_CLIPCHILDREN) 씌우기
        parent_style = user32.GetWindowLongW(parent_hwnd, GWL_STYLE)
        user32.SetWindowLongW(parent_hwnd, GWL_STYLE, parent_style | WS_CLIPCHILDREN)

        # 3. scrcpy 창을 자식 속성으로 변경
        current_style = user32.GetWindowLongW(scrcpy_hwnd, GWL_STYLE)
        user32.SetWindowLongW(scrcpy_hwnd, GWL_STYLE, current_style | WS_CHILD | WS_VISIBLE)

        # 4. 부모 프레임 안으로 가두기
        user32.SetParent(scrcpy_hwnd, parent_hwnd)

        # 5. 크기 맞추고 강제 새로고침
        user32.SetWindowPos(scrcpy_hwnd, 0, 0, 0, width, height, 0x0040 | 0x0020)

        print(f"[System] ✅ 미러링 창 삽입 및 새로고침 완료! (HWND: {scrcpy_hwnd})")
    else:
        print(f"⚠️ [오류] '{window_title}' 창을 찾지 못해서 밖으로 튀어나왔습니다 ㅠ")

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


def get_os_version(uuid):
    """단말기의 안드로이드 OS 버전을 가져옵니다."""
    try:
        # 단말기 시스템 정보(getprop)에서 OS 버전 번호만 딱 빼오는 명령어
        cmd = ["adb", "-s", uuid, "shell", "getprop", "ro.build.version.release"]
        result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
        
        # 앞뒤 공백이나 줄바꿈을 지우고 깔끔하게 반환 (예: "13", "14")
        return result.stdout.strip()
    except Exception as e:
        print(f"OS 버전 확인 에러: {e}")
        return "알 수 없음"


def get_hw_version(uuid):
    """단말기의 하드웨어(HW) 플랫폼 버전을 가져옵니다."""
    try:
        # 단말기 시스템 속성에서 하드웨어 플랫폼 명칭을 추출합니다.
        cmd = ["adb", "-s", uuid, "shell", "getprop", "ro.board.platform"]
        result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
        
        # 값이 비어있다면 대안 속성인 ro.boot.hardware를 탐색합니다.
        hw_val = result.stdout.strip()
        if not hw_val:
            cmd = ["adb", "-s", uuid, "shell", "getprop", "ro.boot.hardware"]
            result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
            hw_val = result.stdout.strip()
            
        return hw_val if hw_val else "Unknown HW"
    except Exception as e:
        print(f"HW 버전 확인 에러: {e}")
        return "알 수 없음"


def get_sdk_version(uuid):
    """단말기의 안드로이드 SDK(API) 버전을 가져옵니다."""
    try:
        cmd = ["adb", "-s", uuid, "shell", "getprop", "ro.build.version.sdk"]
        result = subprocess.run(cmd, capture_output=True, text=True, errors='ignore')
        return result.stdout.strip()
    except Exception as e:
        print(f"SDK 버전 확인 에러: {e}")
        return "알 수 없음"
    
def get_build_image_version(uuid):
    try:
        # 단말기에서 incremental 빌드 버전 추출
        cmd = f"adb -s {uuid} shell getprop ro.build.version.incremental"
        return subprocess.check_output(cmd, shell=True, text=True, encoding='utf-8', errors='ignore').strip()
    except Exception:
        return "-"
    
def get_battery_level(uuid):
    """실제 배터리 잔량을 가져옵니다."""
    try:
        cmd = f"adb -s {uuid} shell dumpsys battery"
        result = subprocess.check_output(cmd, shell=True, text=True, encoding='utf-8', errors='ignore')
        
        for line in result.split('\n'):
            if "level:" in line:
                return line.split(':')[1].strip() + "%"
        return "알 수 없음"
    except Exception:
        return "-"

def get_network_status(uuid):
    """현재 활성화된 네트워크 상태(WiFi 또는 모바일 데이터+통신사)를 가져옵니다."""
    try:
        # 안드로이드 라우팅 테이블을 확인하여 주 통신망 확인
        cmd = f"adb -s {uuid} shell ip route"
        result = subprocess.check_output(cmd, shell=True, text=True, encoding='utf-8', errors='ignore')
        
        if "wlan" in result:
            return "WiFi 연결됨"
        elif "rmnet" in result or "ccmni" in result:  # rmnet(퀄컴), ccmni(미디어텍) 모바일 데이터
            # 통신사 이름(SKT, KT, LGU+) 가져오기
            carrier_cmd = f"adb -s {uuid} shell getprop gsm.operator.alpha"
            carrier = subprocess.check_output(carrier_cmd, shell=True, text=True, encoding='utf-8', errors='ignore').strip()
            # 듀얼심인 경우 콤마로 구분되므로 첫 번째 통신사만 추출
            carrier = carrier.split(',')[0] if carrier else "데이터"
            return f"Mobile ({carrier})"
        else:
            return "네트워크 끊김"
    except Exception:
        return "확인 불가"
    
def set_wifi_state(uuid, state):
    """state: 'enable' 또는 'disable'"""
    if state == 'enable':
        os.system(f"adb -s {uuid} shell svc wifi enable")
    else:
        os.system(f"adb -s {uuid} shell svc wifi disable")

def connect_saved_wifi(uuid, ssid):
    """저장된 WiFi 네트워크에 연결 시도"""
    # 안드로이드 설정에 해당 SSID를 활성화하라는 신호를 보냄
    cmd = f"adb -s {uuid} shell cmd wifi connect-network {ssid} open" 
    # (주의: 네트워크가 이미 저장되어 있어야 함)
    os.system(cmd)

def connect_to_specific_wifi(uuid, ssid, password):
    """
    설정창을 열고 SSID와 비밀번호를 입력하여 연결하는 자동화 함수
    """
    # 1. WiFi 설정 화면 진입
    os.system(f"adb -s {uuid} shell am start -a android.settings.WIFI_SETTINGS")
    time.sleep(1)
    
    # 2. '네트워크 추가' 메뉴로 이동 (보통 검색이나 메뉴 버튼 제어 필요)
    # 기기마다 다르지만 보통 아래 좌표 클릭 또는 키 이벤트로 제어
    os.system(f"adb -s {uuid} shell input text {ssid}") # SSID 입력
    time.sleep(0.5)
    os.system(f"adb -s {uuid} shell input keyevent 66") # 엔터(연결)
    time.sleep(0.5)
    os.system(f"adb -s {uuid} shell input text {password}") # PWD 입력
    time.sleep(0.5)
    os.system(f"adb -s {uuid} shell input keyevent 66") # 연결 완료

def take_screenshot(uuid, save_path):
    """단말기 화면을 캡쳐하여 PC의 지정된 경로에 저장합니다."""
    try:
        # 1. 폰 내부에 임시로 캡쳐 파일 생성
        remote_temp_path = "/sdcard/screen_temp.png"
        subprocess.run(["adb", "-s", uuid, "shell", "screencap", "-p", remote_temp_path], check=True)
        
        # 2. 폰에 있는 캡쳐 파일을 PC(save_path)로 당겨오기 (pull)
        subprocess.run(["adb", "-s", uuid, "pull", remote_temp_path, save_path], check=True)
        
        # 3. 폰에 남아있는 임시 파일 삭제 (용량 확보)
        subprocess.run(["adb", "-s", uuid, "shell", "rm", remote_temp_path])
        
        return True
    except Exception as e:
        print(f"캡쳐 에러: {e}")
        return False

# 1. 로그(Logcat) 수집 시작 함수
def start_log_process(uuid, log_path):
    # -v threadtime: 날짜, 시간, 스레드 정보까지 포함한 상세 로그
    # > 는 파이썬이 처리하므로 Popen의 stdout에 파일을 직접 넘깁니다.
    f = open(log_path, "w", encoding="utf-8")
    return subprocess.Popen(["adb", "-s", uuid, "logcat", "-v", "threadtime"], stdout=f), f

# 2. 패킷 캡처(Tcpdump) 시작 함수 (루팅 기기 전용)
def start_tcpdump_process(uuid, pcap_path):
    # su -c 가 있어야 루팅 권한으로 tcpdump 실행 가능
    # /sdcard에 먼저 저장 후 pull 하는 방식이 안정적입니다.
    remote_path = "/sdcard/dump.pcap"
    
    # 먼저 기존 파일 삭제
    subprocess.run(["adb", "-s", uuid, "shell", "su", "-c", f"rm {remote_path}"])
    
    # 캡처 시작
    proc = subprocess.Popen(["adb", "-s", uuid, "shell", "su", "-c", f"tcpdump -i any -p -s 0 -w {remote_path}"])
    return proc, remote_path

# 3. 프로세스 종료 및 파일 가져오기
def stop_process(proc, uuid=None, remote_path=None, local_path=None):
    proc.terminate() # 프로세스 종료
    # PCAP의 경우 폰에 저장된 파일을 PC로 당겨오기
    if uuid and remote_path and local_path:
        time.sleep(1) # 종료 대기
        subprocess.run(["adb", "-s", uuid, "pull", remote_path, local_path])

def launch_app(uuid, package):
    """앱의 메인 화면을 실행합니다."""
    try:
        # force-stop
        subprocess.run(["adb", "-s", uuid, "shell", "am", "force-stop", package], check=True)
        time.sleep(1)
        
        # 메인 패키지 실행 (monkey 명령어는 메인 액티비티를 알아서 찾아 실행합니다)
        subprocess.run(["adb", "-s", uuid, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"], check=True)
        print(f"✅ {package} 실행 완료!")
    except Exception as e:
        print(f"❌ 앱 실행 실패: {e}")


# [adb_logic.py] 추가
def set_server_config(uuid, ip, port):
    """안드로이드 내부에 서버 정보를 담은 파일을 생성해서 밀어넣기"""
    # 1. PC에 임시 설정파일 생성
    with open("config.ini", "w") as f:
        f.write(f"server_ip={ip}\nserver_port={port}")
    
    # 2. 폰으로 전송 (예: /sdcard/Android/data/... 경로)
    subprocess.run(["adb", "-s", uuid, "push", "config.ini", "/sdcard/config.ini"])
    
    # 3. 앱이 이 파일을 읽도록 알림(필요시)
    print("✅ 서버 설정 파일 전송 완료!")

def connect_wifi_via_settings(uuid, ssid, password):
    """설정창을 열어 WiFi를 검색하고 연결하는 함수"""
    try:
        # 1. WiFi 설정 창 열기
        os.system(f"adb -s {uuid} shell am start -a android.settings.WIFI_SETTINGS")
        time.sleep(2) # 설정 창이 로딩될 시간을 충분히 줍니다.

        # 2. '네트워크 추가' 또는 '검색' 등은 기기마다 달라서, 
        # 가장 범용적인 '입력' 방식으로 SSID를 찾게 합니다.
        
        # SSID 입력 (기기마다 다를 수 있으나 보통 검색창에 입력됨)
        os.system(f"adb -s {uuid} shell input text {ssid}")
        time.sleep(1)
        
        # 3. 연결 시도 (키 이벤트: 엔터)
        os.system(f"adb -s {uuid} shell input keyevent 66") 
        time.sleep(1)
        
        # 4. 비밀번호 입력
        os.system(f"adb -s {uuid} shell input text {password}")
        time.sleep(1)
        
        # 5. 연결 버튼(엔터)
        os.system(f"adb -s {uuid} shell input keyevent 66")
        
        print(f"✅ {ssid} 연결 시도 완료!")
    except Exception as e:
        print(f"❌ WiFi 연결 실패: {e}")

def push_server_config(uuid, ip, port):
    """PC에 임시 파일을 만들고 폰의 /sdcard/ 경로로 파일을 쏩니다."""
    try:
        # 1. PC에 임시 설정파일(config.ini) 생성
        with open("config.ini", "w") as f:
            f.write(f"server_ip={ip}\nserver_port={port}")
        
        # 2. 폰으로 전송 (폰의 내부 저장소 루트에 넣음)
        subprocess.run(["adb", "-s", uuid, "push", "config.ini", "/sdcard/config.ini"], check=True)
        
        # 3. 임시 파일 삭제
        os.remove("config.ini")
        print(f"✅ 서버 설정 전송 완료! (IP: {ip}:{port})")
        return True
    except Exception as e:
        print(f"❌ 설정 파일 전송 실패: {e}")
        return False

def adb_tap(uuid, x, y):
    # 좌표는 정수형으로 변환합니다.
    os.system(f"adb -s {uuid} shell input tap {int(x)} {int(y)}")

def adb_back(uuid):
    # 뒤로가기 버튼(Keyevent 4)으로 키보드 내리기
    os.system(f"adb -s {uuid} shell input keyevent 4")

def adb_type(uuid, text):
    # 따옴표로 감싸서 특수문자(# 등) 입력 가능하게 처리
    os.system(f"adb -s {uuid} shell input text '{text}'")

def automate_pta_login_u2(uuid, env):
    d = u2.connect(uuid)
    
    try:
        # 1. 앱 실행
        print("🚀 앱 실행 중...")
        d.app_start("com.EveryTalk.Global")
        
        # 2. ID 입력 및 키보드 닫기
        id_field = d(resourceId="com.EveryTalk.Global:id/login_id")
        id_field.wait(timeout=10)
        id_field.set_text(env['mc_id'])
        d.press("back") 
        time.sleep(0.5)
        
        # 3. PW 입력 및 키보드 닫기
        pw_field = d(resourceId="com.EveryTalk.Global:id/login_pw")
        pw_field.set_text(env['mc_pw'])
        d.press("back")
        time.sleep(0.5)
        
        # 4. 로그인 클릭
        d(resourceId="com.EveryTalk.Global:id/login_btn").click()
        
        # 5. 서버 설정 팝업 처리
        print("서버 설정 팝업 처리 중...")
        server_field = d(resourceId="com.EveryTalk.Global:id/auth_1_textedit")
        
        if server_field.wait(timeout=10):
            server_field.set_text(env['server_ip'])
            d.press("back") # IP 입력 후 키보드 닫기 (이거 필수!)
            time.sleep(0.5)
            
            # OK 버튼 클릭 (만약 ID가 따로 있다면 resourceId를 쓰시고, 없으면 text로 찾으세요)
            # 만약 OK 버튼 ID를 아신다면: d(resourceId="com.EveryTalk.Global:id/OK버튼ID").click()
            d(text="OK").click() 
            print("✅ PTA 자동화 100% 완료!")
        else:
            print("❌ 서버 설정 팝업을 찾을 수 없습니다!")
            
    except Exception as e:
        print(f"❌ 자동화 실패: {e}")