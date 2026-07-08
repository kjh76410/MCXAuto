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
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
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

    
def ensure_pcapdroid_installed(uuid, apk_path="PCAPdroid.apk"):
    """PCAPdroid 설치 여부를 확인하고, 없으면 자동 설치합니다."""
    package_name = "com.emanuelef.remote_capture"
    
    check_cmd = f"adb -s {uuid} shell pm list packages {package_name}"
    result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
    
    if package_name in result.stdout:
        print("✅ PCAPdroid가 이미 설치되어 있습니다. (설치 패스!)")
        return True
    else:
        print("⚠️ PCAPdroid 미설치 상태입니다. 폰에 자동 설치를 진행합니다...")
        
        install_cmd = f"adb -s {uuid} install -r {apk_path}"
        install_result = subprocess.run(install_cmd, shell=True, capture_output=True, text=True)
        
        if "Success" in install_result.stdout:
            print("✅ PCAPdroid 설치 완료!")
            # 🚨 원흉이었던 setup_pcapdroid_settings(...) 코드 삭제 완료!
            return True
        else:
            print(f"❌ 설치 실패: {install_result.stderr}")
            return False

def start_pcapdroid(uuid):
    """PCAPdroid를 실행하여 캡처를 시작합니다."""
    # 1. 앱이 깔려있는지 확인 (없으면 설치됨)
    if not ensure_pcapdroid_installed(uuid):
        print("❌ 앱 설치/확인 실패로 캡처를 시작할 수 없습니다.")
        return False
        
    # 🌟 2. 캡처 시작 전, 설정이 올바른지 무조건 1회 점검! (이미 되어있으면 바로 패스함)
    setup_pcapdroid_settings(uuid)
        
    # 3. 백그라운드 캡처 시작
    try:
        print("📡 PCAP 캡처 시작 (백그라운드)...")
        cmd = f"adb -s {uuid} shell am start -n com.emanuelef.remote_capture/.activities.CaptureCtrl -a com.emanuelef.remote_capture.action.START"
        subprocess.run(cmd, shell=True, check=True)
        return True
    except Exception as e:
        print(f"❌ PCAP 시작 실패: {e}")
        return False

def stop_pcapdroid(uuid):
    """PCAPdroid 캡처를 종료합니다."""
    try:
        print("🛑 PCAP 캡처 종료 중...")
        # 캡처 종료 명령어
        cmd = f"adb -s {uuid} shell am start -n com.emanuelef.remote_capture/.activities.CaptureCtrl -a com.emanuelef.remote_capture.action.STOP"
        subprocess.run(cmd, shell=True, check=True)
        print("✅ 캡처가 중지되었습니다. (파일은 폰의 Download 폴더에 저장됨)")
        return True
    except Exception as e:
        print(f"❌ PCAP 종료 실패: {e}")
        return False
    
def setup_pcapdroid_settings(uuid):
    d = u2.connect(uuid)
    
    try:
        print("⚙️ PCAPdroid 설정 상태를 점검합니다...")
        d.app_start("com.emanuelef.remote_capture")
        time.sleep(2)
        
        # 🌟 [0] 최초 설치 시 뜨는 튜토리얼(Welcome) 화면 스킵
        if d(text="SKIP").exists:
            print("- 최초 실행 튜토리얼 감지! [SKIP] 버튼을 클릭합니다.")
            d(text="SKIP").click()
            time.sleep(1)
        elif d(text="Skip").exists:
            print("- 최초 실행 튜토리얼 감지! [Skip] 버튼을 클릭합니다.")
            d(text="Skip").click()
            time.sleep(1)
            
        # 메인 화면 로딩 대기
        if not d(text="Ready").wait(timeout=10):
            print("❌ PCAPdroid 메인 화면 로딩 실패")
            return

        # ----------------------------------------------------
        # 1. 덤프 모드 세팅 (No dump -> PCAP file)
        # ----------------------------------------------------
        if d(text="No dump").exists:
            d(text="No dump").click()
            time.sleep(1)
            if d(text="PCAP file").exists:
                d(text="PCAP file").click()
                time.sleep(1)

        # ----------------------------------------------------
        # 2. Target apps 스마트 점검 (메인 화면에서 바로 확인!)
        # ----------------------------------------------------
        # 스크린샷처럼 메인 화면에 "com.EveryTalk.Global" 글씨가 이미 있다면?
        if d(textContains="com.EveryTalk.Global").exists or d(textContains="MCX Client").exists:
            print("- ✅ 메인 화면에서 [EveryTalk] 타겟 앱 설정을 확인했습니다.")
            
            # 메인 화면에 있는 토글 스위치가 켜져 있는지 확인
            main_toggle = d(resourceId="com.emanuelef.remote_capture:id/app_filter_switch")
            if main_toggle.exists:
                is_main_on = main_toggle.info.get('checked')
                if not is_main_on: # 만약 꺼져있다면
                    print("- 메인 화면 토글이 OFF 상태입니다. ON으로 켭니다.")
                    main_toggle.click()
                    time.sleep(1)
                else:
                    print("- 메인 화면 토글도 이미 ON 상태입니다. (상세 셋팅 완벽 패스!)")
                    
        else:
            # 메인 화면에 앱 이름이 없다면 상세 설정으로 딥-다이브 진입!
            print("- 타겟 앱이 지정되지 않았습니다. 상세 설정 화면으로 진입합니다.")
            d(text="Target apps").click()
            time.sleep(2) 
            
            # [1] 우측 상단 3닷 메뉴 클릭 & 시스템 앱 활성화 점검
            if d(description="More options").exists:
                d(description="More options").click()
                time.sleep(1)
                
                sys_menu = d(text="Show system apps")
                if sys_menu.exists:
                    checkbox = d(className="android.widget.CheckBox")
                    is_checked = checkbox.info.get('checked') if checkbox.exists else sys_menu.info.get('checked')
                        
                    if not is_checked:
                        print("- [Show system apps] 활성화합니다.")
                        sys_menu.click()
                        time.sleep(1.5)
                    else:
                        print("- [Show system apps] 이미 체크되어 있습니다! (유지)")
                        d.press("back")
                        time.sleep(1)

            # [2] 검색 버튼 클릭 및 앱 검색 (소문자 everytalk)
            search_btn = d(resourceId="com.emanuelef.remote_capture:id/search_button")
            if search_btn.exists:
                search_btn.click()
                time.sleep(1.5)
                
                search_box = d(className="android.widget.EditText")
                if search_box.exists:
                    search_box.set_text("everytalk")
                else:
                    d.send_keys("everytalk")
                    
                time.sleep(2)
                
            # [3] 검색된 앱 토글 켜기
            toggle_btn = d(resourceId="com.emanuelef.remote_capture:id/toggle_btn")
            if toggle_btn.exists:
                is_on = toggle_btn.info.get('checked')
                if not is_on:
                    print("- [EveryTalk] 토글을 ON으로 변경합니다!")
                    toggle_btn.click()
                    time.sleep(1)
                else:
                    print("- [EveryTalk] 토글이 이미 ON 상태입니다.")
                    
            # [4] 메인 화면 복귀 루프
            print("- 셋팅 완료! 메인 화면으로 돌아갑니다.")
            while not d(resourceId="com.emanuelef.remote_capture:id/action_start").exists:
                d.press("back")
                time.sleep(1)
                
        # ----------------------------------------------------
        # 3. 캡처 시작 (상단 Play 버튼 클릭)
        # ----------------------------------------------------
        play_btn = d(resourceId="com.emanuelef.remote_capture:id/action_start")
        if play_btn.exists:
            print("- ▶️ 상단 Play 버튼을 클릭하여 캡처를 시작합니다!")
            play_btn.click()
            
            # 🌟 [업그레이드] 최대 2번 뜨는 팝업 스마트 처리
            # (처음 실행이면 2번 누르고, 두 번째 실행이면 바로 break로 빠져나감)
            for i in range(2):
                time.sleep(1.5) # 팝업창 뜰 시간 살짝 대기
                
                if d(text="OK").exists:
                    print(f"- 권한/안내 팝업 감지 ({i+1}/2) : [OK] 클릭")
                    d(text="OK").click()
                elif d(text="확인").exists:
                    print(f"- 권한/안내 팝업 감지 ({i+1}/2) : [확인] 클릭")
                    d(text="확인").click()
                else:
                    # 화면에 더 이상 OK나 확인 버튼이 없다면 반복문 즉시 탈출!
                    break 
                    
            print("✅ PCAPdroid 캡처가 정상적으로 실행되었습니다!")
        else:
            print("❌ Play 버튼을 찾지 못했습니다.")

    except Exception as e:
        print(f"❌ 설정 점검 및 실행 중 오류 발생: {e}")


def start_device_pcap(uuid):
    """단말기 다이얼러를 통해 히든 메뉴에 진입하여 PCAP 캡처를 시작합니다.
    이미 실행 중(STOP 버튼이 보임)이면 STOP 후 다시 START 및 OK 팝업까지 처리합니다."""
    d = u2.connect(uuid)
    
    try:
        print("⚙️ 단말 PCAP 상태 점검 및 진입 시작...")
        
        # 1. 다이얼러 앱 강제 실행
        d.app_start("org.codeaurora.dialer")
        time.sleep(2) 
        
        if d(resourceIdMatches=".*fab.*").exists:
            d(resourceIdMatches=".*fab.*").click()
            time.sleep(1)
            
        # 2. 다이얼 코드 입력 (**9##)
        print("- 다이얼 코드 [**9##] 자동 타이핑 중...")
        d.press(17) # *
        d.press(17) # *
        d.press(16) # 9
        d.press(18) # #
        d.press(18) # #
        time.sleep(2) # 히든 메뉴 화면 뜰 때까지 대기
        
        # 🌟 3. 현재 상태 스마트 체크 및 덮어쓰기 분기안내
        # 만약 화면에 'PCAP DUMP STOP'이 보인다면 이미 실행 중인 상태입니다!
        if d(text="PCAP DUMP STOP").exists:
            print("- ⚠️ 이미 PCAP 캡처가 실행 중입니다. [STOP ➡️ START] 재시작을 진행합니다.")
            d(text="PCAP DUMP STOP").click()
            time.sleep(1.5) # 꺼질 때까지 대기
            
            # 혹시 STOP 버튼 누른 후에도 확인/OK 팝업이 뜨는 기종이라면 클릭 처리 (방어 코드)
            if d(text="OK").exists: d(text="OK").click()
            elif d(text="확인").exists: d(text="확인").click()
            time.sleep(1)

        # 🌟 4. PCAP DUMP START 실행 및 후속 OK 팝업 처리
        if d(text="PCAP DUMP START").exists:
            print("- [PCAP DUMP START] 버튼을 클릭합니다.")
            d(text="PCAP DUMP START").click()
            time.sleep(1.5) # START 클릭 후 뜨는 안내 팝업 대기
            
            # 🚀 핵심: START 클릭 직후 뜨는 OK/확인 팝업 자동 클릭!
            if d(text="OK").exists:
                print("- 팝업 감지: [OK] 클릭 완료")
                d(text="OK").click()
            elif d(text="확인").exists:
                print("- 팝업 감지: [확인] 클릭 완료")
                d(text="확인").click()
                
            print("✅ 단말자체 PCAP 캡처가 성공적으로 시작되었습니다!")
            time.sleep(1)
            d.press("home") # 홈 화면으로 복귀
            return True
        else:
            print("❌ 'PCAP DUMP START' 버튼을 찾지 못했습니다. 화면을 확인해 주세요.")
            return False

    except Exception as e:
        print(f"❌ 단말 PCAP 실행 중 오류 발생: {e}")
        return False


def stop_device_pcap(uuid):
    """단말기 히든 메뉴에 다시 진입하여 PCAP 캡처를 종료합니다."""
    d = u2.connect(uuid)
    
    try:
        print("⚙️ 단말 PCAP 종료를 시도합니다...")
        
        # 종료 버튼이 이미 화면에 떠 있는지 먼저 확인 (안 떠있으면 다시 다이얼러 켬)
        if not d(text="PCAP DUMP STOP").exists:
            d.app_start("org.codeaurora.dialer")
            time.sleep(1.5)
            if d(resourceIdMatches=".*fab.*").exists:
                d(resourceIdMatches=".*fab.*").click()
                time.sleep(1)
            
            # 다시 **9## 입력
            d.press(17); d.press(17); d.press(16); d.press(18); d.press(18)
            time.sleep(2)
            
        if d(text="PCAP DUMP STOP").exists:
            d(text="PCAP DUMP STOP").click()
            print("✅ 단말 PCAP 캡처가 중지되었습니다!")
            time.sleep(1)
            d.press("home")
            return True
        else:
            print("❌ 'PCAP DUMP STOP' 버튼을 찾지 못했습니다.")
            return False

    except Exception as e:
        print(f"❌ 단말 PCAP 종료 중 오류 발생: {e}")
        return False