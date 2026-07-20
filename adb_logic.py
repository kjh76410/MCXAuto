import os
import time
import ctypes
import threading
import re
import subprocess
import platform
import shutil
import uiautomator2 as u2

# PATH에 여러 adb.exe(SDK platform-tools, scrcpy 번들 등)가 섞여 있으면 서로 다른 버전이
# adb 서버(5037 포트) 소유권을 두고 계속 재시작 전쟁을 벌여 기기 인식이 멈춥니다.
# shutil.which("adb")로 PATH가 실제로 고르는 것과 동일한 adb.exe를 골라 앱 전체(scrcpy 포함)가
# 항상 같은 바이너리만 쓰도록 고정합니다.
ADB_PATH = shutil.which("adb") or "adb"


def get_devices():
    try:
        res = subprocess.check_output(["adb", "devices"]).decode()
        return [
            line.split("\t")[0]
            for line in res.strip().split("\n")
            if "\tdevice" in line
        ]
    except:
        return []


def kill_adb_server():
    """프로그램 종료 시 adb 서버를 내려서, 다음 실행 때 깨끗한 서버로 새로 시작하게 합니다.
    응답을 기다리면(subprocess.run) adb가 멈춰있을 때 창 닫기 자체가 멎어버리므로,
    Popen으로 요청만 던지고 완료를 기다리지 않습니다(fire-and-forget)."""
    try:
        subprocess.Popen(
            ["adb", "kill-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"⚠️ adb 서버 종료 요청 실패: {e}")


def get_screen_resolution(uuid):
    """기기의 실제 화면 해상도를 (width, height) 튜플로 반환합니다.
    회전(orientation)에 따라 wm size의 override/physical 표기가 달라질 수 있어
    가장 마지막에 등장하는 해상도(override가 있으면 override)를 사용합니다."""
    try:
        output = subprocess.check_output(["adb", "-s", uuid, "shell", "wm", "size"]).decode()
        matches = re.findall(r"(\d+)x(\d+)", output)
        if matches:
            w, h = matches[-1]
            return int(w), int(h)
    except Exception:
        pass
    return None


def get_model_name(uuid):
    try:
        return (
            subprocess.check_output(
                ["adb", "-s", uuid, "shell", "getprop", "ro.product.model"]
            )
            .decode()
            .strip()
        )
    except:
        return "Unknown"


def start_mirroring_embedded(uuid, parent_hwnd, width, height):
    """미러링 프로세스를 실행하고 윈도우 스왈로우 스레드를 시작하는 함수"""
    try:
        # 창 제목을 기기 UUID로 고유하게 설정
        window_title = f"Mirror_{uuid}"

        cmd = [
            r"C:\scrcpy\scrcpy.exe",
            "-s",
            uuid,
            "--window-title",
            window_title,
            "--window-width",
            str(width),
            "--window-height",
            str(height),
            "--window-borderless",
            "--no-audio",
        ]

        # 1. scrcpy 실행
        # 🌟 scrcpy는 PATH와 무관하게 자기 폴더의 adb.exe(버전이 다를 수 있음)를 먼저 씁니다.
        # 이 앱의 나머지 코드는 PATH상의 adb(ADB_PATH)를 쓰기 때문에, 서로 다른 두 adb가
        # 같은 서버(5037 포트) 소유권을 두고 계속 재시작시키면서 기기 인식이 멈추는 문제가
        # 있었습니다. scrcpy는 --adb 같은 CLI 옵션이 아니라 ADB 환경변수로 경로를 받으므로
        # 이 프로세스에만 환경변수를 얹어서 항상 같은 adb.exe/서버를 쓰도록 고정합니다.
        env = os.environ.copy()
        env["ADB"] = ADB_PATH
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)

        # 2. 창 낚아채기 스레드 실행 (크기 정보 width, height도 같이 넘겨줍니다!)
        thread = threading.Thread(
            target=swallow_window_worker,
            args=(window_title, parent_hwnd, width, height),
            daemon=True,
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
        WS_CLIPCHILDREN = (
            0x02000000  # ✨ [핵심] 자식 창 영역은 배경색으로 덮어쓰지 않음!
        )

        # 2. 부모 프레임(Tkinter)에 방어막(WS_CLIPCHILDREN) 씌우기
        parent_style = user32.GetWindowLongW(parent_hwnd, GWL_STYLE)
        user32.SetWindowLongW(parent_hwnd, GWL_STYLE, parent_style | WS_CLIPCHILDREN)

        # 3. scrcpy 창을 자식 속성으로 변경
        current_style = user32.GetWindowLongW(scrcpy_hwnd, GWL_STYLE)
        user32.SetWindowLongW(
            scrcpy_hwnd, GWL_STYLE, current_style | WS_CHILD | WS_VISIBLE
        )

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
        subprocess.Popen(
            ["adb", "-s", uuid, "shell", "input", "keyevent", str(keycode)]
        )
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
        cmd = f"adb -s {uuid} shell dumpsys window | findstr mCurrentFocus"
        output = subprocess.check_output(cmd, shell=True).decode().strip()

        # 정규식으로 패키지명만 쏙 빼내기 (예: u0 com.kakao.talk/...)
        match = re.search(r"u0 ([a-zA-Z0-9_\.]+)/", output)
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

        result = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
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
        result = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")

        # 앞뒤 공백이나 줄바꿈을 지우고 깔끔하게 반환 (예: "13", "14")
        return result.stdout.strip()
    except Exception as e:
        print(f"OS 버전 확인 에러: {e}")
        return "알 수 없음"


def get_hw_version(uuid):
    """단말기의 실제 하드웨어 버전(예: MP11B)을 가져옵니다."""
    try:
        # 1. 메인 보드 버전 속성 탐색
        cmd = ["adb", "-s", uuid, "shell", "getprop", "ro.product.board_ver"]
        result = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        hw_val = result.stdout.strip()

        # 2. 값이 비어있다면 대안 속성인 ro.boot.hardware.revision 탐색
        if not hw_val:
            cmd = ["adb", "-s", uuid, "shell", "getprop", "ro.boot.hardware.revision"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, errors="ignore"
            )
            hw_val = result.stdout.strip()

        return hw_val if hw_val else "Unknown HW"

    except Exception as e:
        print(f"HW 버전 확인 에러: {e}")
        return "알 수 없음"


def get_sdk_version(uuid):
    """단말기의 안드로이드 SDK(API) 버전을 가져옵니다."""
    try:
        cmd = ["adb", "-s", uuid, "shell", "getprop", "ro.build.version.sdk"]
        result = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        return result.stdout.strip()
    except Exception as e:
        print(f"SDK 버전 확인 에러: {e}")
        return "알 수 없음"


def get_build_image_version(uuid):
    try:
        # 단말기에서 incremental 빌드 버전 추출
        cmd = f"adb -s {uuid} shell getprop ro.build.version.incremental"
        return subprocess.check_output(
            cmd, shell=True, text=True, encoding="utf-8", errors="ignore"
        ).strip()
    except Exception:
        return "-"


def get_battery_level(uuid):
    """실제 배터리 잔량을 가져옵니다."""
    try:
        cmd = f"adb -s {uuid} shell dumpsys battery"
        result = subprocess.check_output(
            cmd, shell=True, text=True, encoding="utf-8", errors="ignore"
        )

        for line in result.split("\n"):
            if "level:" in line:
                return line.split(":")[1].strip() + "%"
        return "알 수 없음"
    except Exception:
        return "-"


def get_network_status(uuid):
    """현재 활성화된 네트워크 상태(WiFi SSID 또는 LTE/5G)를 가져옵니다."""
    import subprocess
    import re
    
    try:
        # 1. 안드로이드 라우팅 테이블을 확인하여 주 통신망 확인
        cmd = f"adb -s {uuid} shell ip route"
        result = subprocess.check_output(cmd, shell=True, text=True, errors="ignore")

        if "wlan" in result:
            # 💡 [WiFi] 연결된 경우 SSID 추출 (기존 로직 유지)
            status_cmd = f"adb -s {uuid} shell cmd wifi status"
            status_res = subprocess.run(status_cmd, shell=True, capture_output=True, text=True, errors="ignore").stdout
            match = re.search(r'connected to\s*"([^"]+)"', status_res)

            if not match:
                dump_cmd = f'adb -s {uuid} shell "dumpsys wifi | grep mWifiInfo"'
                dump_res = subprocess.run(dump_cmd, shell=True, capture_output=True, text=True, errors="ignore").stdout
                match = re.search(r'SSID:\s*"([^"]+)"', dump_res)

            if match and match.group(1) and match.group(1) != "<unknown ssid>":
                return f"WiFi ({match.group(1)})"
            else:
                return "WiFi (연결됨)"

        # 💡 [핵심 수정] 삼성(pdp), 기타 통신칩셋(clat, seth, wwan 등)의 인터페이스 이름 모두 포함!
        elif any(iface in result for iface in ["rmnet", "ccmni", "pdp", "seth", "clat", "wwan"]):
            
            # 통신사 이름(SKT, KT, LGU+) 가져오기
            carrier_cmd = f"adb -s {uuid} shell getprop gsm.operator.alpha"
            carrier = subprocess.check_output(carrier_cmd, shell=True, text=True, errors="ignore").strip()
            carrier = carrier.split(",")[0] if carrier else ""

            # 💡 [추가] 실제 네트워크 타입(LTE, NR(5G) 등) 알아내기
            net_type_cmd = f"adb -s {uuid} shell getprop gsm.network.type"
            net_type_res = subprocess.check_output(net_type_cmd, shell=True, text=True, errors="ignore").strip()
            net_type = net_type_res.split(",")[0] if net_type_res else ""
            
            # 보기 좋게 이름 변환 (NR은 안드로이드 시스템에서 5G를 의미함)
            if "NR" in net_type:
                display_type = "5G"
            elif "LTE" in net_type:
                display_type = "LTE"
            else:
                display_type = "Mobile Data" # 3G 이거나 판별 불가할 때

            if carrier:
                return f"{display_type} ({carrier})"
            else:
                return display_type

        else:
            # 💡 [최후의 보루] ip route에 잡히지 않는 특이한 단말기를 위한 추가 검증
            check_data_cmd = f'adb -s {uuid} shell "dumpsys telephony.registry | grep mDataConnectionState"'
            data_state = subprocess.check_output(check_data_cmd, shell=True, text=True, errors="ignore")
            
            if "mDataConnectionState=2" in data_state: # 2는 모바일 데이터 CONNECTED를 의미합니다.
                 return "LTE/5G (연결됨)"
                 
            return "네트워크 끊김"

    except Exception as e:
        print(f"네트워크 상태 확인 에러: {e}")
        return "확인 불가"


def unlock_screen(uuid):
    import subprocess
    import time

    print(f"🔓 [{uuid}] 화면 잠금 해제 시도 중...")
    try:
        # 1. 화면 켜기 (Wake up)
        subprocess.run(f"adb -s {uuid} shell input keyevent 224", shell=True)
        # ⏳ 화면이 켜지고 시스템이 반응할 시간을 넉넉히 1초로 늘려줍니다.
        time.sleep(1.0)

        # 2. 1차 시도: 마법의 해제 키 (메뉴 버튼)
        # 안드로이드 버전에 따라 이 키만 보내도 스와이프 잠금이 바로 풀립니다.
        subprocess.run(f"adb -s {uuid} shell input keyevent 82", shell=True)
        time.sleep(0.5)

        # 3. 2차 시도: 중앙 좌표 스와이프 (1차 시도가 안 먹혔을 때를 대비)
        # 가로 500, 세로 1000(중간쯤)에서 가로 500, 세로 200(위쪽)으로 200ms 동안 조금 빠르게 밀어 올립니다!
        subprocess.run(
            f"adb -s {uuid} shell input swipe 500 1000 500 200 200", shell=True
        )
        time.sleep(0.5)

        print("✅ 잠금 해제 스크립트 실행 완료!")
        return True
    except Exception as e:
        print(f"❌ 잠금 해제 실패: {e}")
        return False


def take_screenshot(uuid, save_path):
    """단말기 화면을 캡쳐하여 PC의 지정된 경로에 저장합니다."""
    try:
        # 1. 폰 내부에 임시로 캡쳐 파일 생성
        remote_temp_path = "/sdcard/screen_temp.png"
        subprocess.run(
            ["adb", "-s", uuid, "shell", "screencap", "-p", remote_temp_path],
            check=True,
        )

        # 2. 폰에 있는 캡쳐 파일을 PC(save_path)로 당겨오기 (pull)
        subprocess.run(
            ["adb", "-s", uuid, "pull", remote_temp_path, save_path], check=True
        )

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
    return (
        subprocess.Popen(["adb", "-s", uuid, "logcat", "-v", "threadtime"], stdout=f),
        f,
    )


# 2. 패킷 캡처(Tcpdump) 시작 함수 (루팅 기기 전용)
def start_tcpdump_process(uuid, pcap_path):
    # su -c 가 있어야 루팅 권한으로 tcpdump 실행 가능
    # /sdcard에 먼저 저장 후 pull 하는 방식이 안정적입니다.
    remote_path = "/sdcard/dump.pcap"

    # 먼저 기존 파일 삭제
    subprocess.run(["adb", "-s", uuid, "shell", "su", "-c", f"rm {remote_path}"])

    # 캡처 시작
    proc = subprocess.Popen(
        [
            "adb",
            "-s",
            uuid,
            "shell",
            "su",
            "-c",
            f"tcpdump -i any -p -s 0 -w {remote_path}",
        ]
    )
    return proc, remote_path


# 3. 프로세스 종료 및 파일 가져오기
def stop_process(proc, uuid=None, remote_path=None, local_path=None):
    proc.terminate()  # 프로세스 종료
    # PCAP의 경우 폰에 저장된 파일을 PC로 당겨오기
    if uuid and remote_path and local_path:
        time.sleep(1)  # 종료 대기
        subprocess.run(["adb", "-s", uuid, "pull", remote_path, local_path])


def launch_app(uuid, package):
    """앱의 메인 화면을 실행합니다."""
    try:
        # force-stop
        subprocess.run(
            ["adb", "-s", uuid, "shell", "am", "force-stop", package], check=True
        )
        time.sleep(1)

        # 메인 패키지 실행 (monkey 명령어는 메인 액티비티를 알아서 찾아 실행합니다)
        subprocess.run(
            [
                "adb",
                "-s",
                uuid,
                "shell",
                "monkey",
                "-p",
                package,
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ],
            check=True,
        )
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


def push_server_config(uuid, ip, port):
    """PC에 임시 파일을 만들고 폰의 /sdcard/ 경로로 파일을 쏩니다."""
    try:
        # 1. PC에 임시 설정파일(config.ini) 생성
        with open("config.ini", "w") as f:
            f.write(f"server_ip={ip}\nserver_port={port}")

        # 2. 폰으로 전송 (폰의 내부 저장소 루트에 넣음)
        subprocess.run(
            ["adb", "-s", uuid, "push", "config.ini", "/sdcard/config.ini"], check=True
        )

        # 3. 임시 파일 삭제
        os.remove("config.ini")
        print(f"✅ 서버 설정 전송 완료! (IP: {ip}:{port})")
        return True
    except Exception as e:
        print(f"❌ 설정 파일 전송 실패: {e}")
        return False


def connect_wifi(uuid, ssid, password):
    print(f"📡 [wpa_cli] WiFi 연결 시도: {ssid}")

    try:
        # 1. 새 네트워크 ID 생성 (예: 1, 2, 3...)
        cmd_add = f'adb -s {uuid} shell "wpa_cli -i wlan0 add_network"'
        res_add = subprocess.run(cmd_add, shell=True, capture_output=True, text=True)
        net_id = res_add.stdout.strip()

        # 숫자가 정상적으로 반환되었는지 확인
        if not net_id.isdigit():
            # wpa_cli가 실패했을 경우를 대비한 백업 (기존 cmd wifi 명령어 형태 보완)
            print("⚠️ wpa_cli 미지원 단말, 보완된 cmd wifi 명령어로 재시도...")
            cmd_fallback = f'adb -s {uuid} shell cmd wifi connect-network "{ssid}" wpa2 "{password}"'
            res_fallback = subprocess.run(
                cmd_fallback, shell=True, capture_output=True, text=True
            )
            return res_fallback.returncode == 0

        # 2. SSID 설정
        subprocess.run(
            f'adb -s {uuid} shell "wpa_cli -i wlan0 set_network {net_id} ssid \\"\\"{ssid}\\"\\""',
            shell=True,
        )

        # 3. 비밀번호 설정 (WPA2 기준)
        subprocess.run(
            f'adb -s {uuid} shell "wpa_cli -i wlan0 set_network {net_id} psk \\"\\"{password}\\"\\""',
            shell=True,
        )

        # 4. 네트워크 활성화 및 선택
        subprocess.run(
            f'adb -s {uuid} shell "wpa_cli -i wlan0 select_network {net_id}"',
            shell=True,
        )
        subprocess.run(
            f'adb -s {uuid} shell "wpa_cli -i wlan0 enable_network {net_id}"',
            shell=True,
        )
        subprocess.run(
            f'adb -s {uuid} shell "wpa_cli -i wlan0 reassociate"', shell=True
        )

        print(f"✅ WiFi {ssid} 연결 명령 전송 완료")
        return True

    except Exception as e:
        print(f"❌ WiFi 연결 중 예외 발생: {e}")
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
        id_field.set_text(env["mc_id"])
        d.press("back")
        time.sleep(0.5)

        # 3. PW 입력 및 키보드 닫기
        pw_field = d(resourceId="com.EveryTalk.Global:id/login_pw")
        pw_field.set_text(env["mc_pw"])
        d.press("back")
        time.sleep(0.5)

        # 4. 로그인 클릭
        d(resourceId="com.EveryTalk.Global:id/login_btn").click()

        # 5. 서버 설정 팝업 처리
        print("서버 설정 팝업 처리 중...")
        server_field = d(resourceId="com.EveryTalk.Global:id/auth_1_textedit")

        if server_field.wait(timeout=10):
            server_field.set_text(env["server_ip"])
            d.press("back")  # IP 입력 후 키보드 닫기 (이거 필수!)
            time.sleep(0.5)

            # OK 버튼 클릭 (만약 ID가 따로 있다면 resourceId를 쓰시고, 없으면 text로 찾으세요)
            # 만약 OK 버튼 ID를 아신다면: d(resourceId="com.EveryTalk.Global:id/OK버튼ID").click()
            d(text="OK").click()
            print("✅ PTA 자동화 100% 완료!")
        else:
            print("❌ 서버 설정 팝업을 찾을 수 없습니다!")

    except Exception as e:
        print(f"❌ 자동화 실패: {e}")


def ensure_pcapdroid_installed(uuid, apk_path="PCAPdroid.apk", log=print):
    """PCAPdroid 설치 여부를 확인하고, 없으면 자동 설치합니다."""
    package_name = "com.emanuelef.remote_capture"

    check_cmd = f"adb -s {uuid} shell pm list packages {package_name}"
    result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)

    if package_name in result.stdout:
        log("✅ PCAPdroid가 이미 설치되어 있습니다. (설치 패스!)")
        return True
    else:
        log("⚠️ PCAPdroid 미설치 상태입니다. 폰에 자동 설치를 진행합니다...")

        install_cmd = f"adb -s {uuid} install -r {apk_path}"
        install_result = subprocess.run(
            install_cmd, shell=True, capture_output=True, text=True
        )

        if "Success" in install_result.stdout:
            log("✅ PCAPdroid 설치 완료!")
            return True
        else:
            log(f"❌ 설치 실패: {install_result.stderr}")
            return False


def launch_pcapdroid(uuid, log=print):
    """PCAPdroid 앱을 실행해서 메인 화면까지 띄웁니다 (온보딩/권한 팝업 자동 처리).
    설정 변경이나 캡처 시작 없이 앱을 실행 상태로만 만들어 둡니다."""
    try:
        d = u2.connect(uuid)
    except Exception as e:
        log(f"❌ PCAPdroid 실행 중 기기 연결 실패: {e}")
        return False

    if _wait_pcapdroid_main_screen(d):
        log("✅ PCAPdroid 실행 완료!")
        return True

    log("❌ PCAPdroid 메인 화면 로딩 실패")
    return False


def start_pcapdroid(uuid, log=print):
    """PCAPdroid를 실행하여 캡처를 시작합니다."""
    # 1. 앱이 깔려있는지 확인 (없으면 설치됨)
    if not ensure_pcapdroid_installed(uuid, log=log):
        log("❌ 앱 설치/확인 실패로 캡처를 시작할 수 없습니다.")
        return False

    # 🌟 2. 캡처 시작 전, 설정이 올바른지 무조건 1회 점검! (이미 되어있으면 바로 패스함)
    if not setup_pcapdroid_settings(uuid, log=log):
        log("❌ PCAPdroid 설정 점검 실패로 캡처를 시작할 수 없습니다.")
        return False

    # 3. 백그라운드 캡처 시작
    try:
        log("📡 PCAP 캡처 시작 (백그라운드)...")
        cmd = f"adb -s {uuid} shell am start -n com.emanuelef.remote_capture/.activities.CaptureCtrl -a com.emanuelef.remote_capture.action.START"
        subprocess.run(cmd, shell=True, check=True)
        return True
    except Exception as e:
        log(f"❌ PCAP 시작 실패: {e}")
        return False


def stop_pcapdroid(uuid, log=print):
    """PCAPdroid 캡처를 종료합니다.

    예전엔 CaptureCtrl 액티비티에 action.STOP 인텐트만 보냈는데, 이 원격 제어 인텐트는
    실측 결과 매번 'PCAPdroid control request' 승인 팝업을 띄우고(_send_pcapdroid_action
    독스트링 참고) 아무도 눌러주지 않으면 그대로 무시됩니다. 그러면 캡처가 실제로는 계속
    실행 중인 채로 남고, 캡처 중엔 설정(⚙️) 버튼이 비활성화되어 있어서 이후 덤프 모드를
    PCAP file → TCP exporter로 바꾸려는 시도가 계속 실패하는 문제로 이어졌습니다.
    그래서 Play 버튼 시작과 동일하게, 화면의 실제 Stop 버튼을 좌표 탭으로 눌러 확실하게
    멈춥니다."""
    try:
        d = u2.connect(uuid)
        log("🛑 PCAP 캡처 종료 중...")

        if not _wait_pcapdroid_main_screen(d):
            log("❌ PCAPdroid 메인 화면 로딩 실패")
            return False

        btn = d(resourceId="com.emanuelef.remote_capture:id/action_stop")
        if not btn.exists:
            log("- 이미 캡처가 중지된 상태입니다. (스킵)")
            return True

        info = btn.info
        cx = (info["bounds"]["left"] + info["bounds"]["right"]) // 2
        cy = (info["bounds"]["top"] + info["bounds"]["bottom"]) // 2
        d.click(cx, cy)
        time.sleep(1)

        log("✅ 캡처가 중지되었습니다. (파일은 폰의 Download 폴더에 저장됨)")
        return True
    except Exception as e:
        log(f"❌ PCAP 종료 실패: {e}")
        return False


def pull_latest_pcapdroid_file(uuid, local_dir):
    """폰의 Download 폴더에서 가장 최근에 생성된 PCAPdroid 캡처 파일을 local_dir로 pull합니다.
    PCAPdroid는 "PCAPdroid_14_Jul_18_23_23"처럼 확장자 없이 저장하므로 .pcap 확장자로
    필터링하지 않고 파일명 접두사(PCAPdroid_)로 찾습니다.
    """
    try:
        # 캡처 종료 직후엔 파일이 아직 flush 중일 수 있어 살짝 대기합니다.
        time.sleep(1.5)

        result = subprocess.run(
            [
                "adb",
                "-s",
                uuid,
                "shell",
                # 최신 PCAPdroid는 Download/PCAPdroid/ 하위 폴더에 저장하고,
                # 구버전은 Download/ 바로 밑에 저장하므로 둘 다 뒤져서 최신 파일을 찾습니다.
                "ls -t /sdcard/Download/PCAPdroid_* /sdcard/Download/PCAPdroid/PCAPdroid_* 2>/dev/null | head -n 1",
            ],
            capture_output=True,
            text=True,
        )
        remote_path = result.stdout.strip()
        if not remote_path:
            print("❌ 폰의 Download 폴더에서 pcap 파일을 찾지 못했습니다.")
            return None

        os.makedirs(local_dir, exist_ok=True)
        remote_name = os.path.basename(remote_path)
        # 확장자가 없는 파일명(PCAPdroid 기본 형식)이면 로컬에는 .pcap을 붙여서 저장합니다
        # (tshark는 확장자와 무관하게 동작하지만, 나중에 수동으로 Wireshark로 열기 편하도록).
        if "." not in remote_name:
            remote_name += ".pcap"
        local_path = os.path.join(local_dir, remote_name)
        subprocess.run(
            ["adb", "-s", uuid, "pull", remote_path, local_path],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        print(f"✅ pcap 파일을 가져왔습니다: {local_path}")
        return local_path
    except Exception as e:
        print(f"❌ pcap pull 중 오류 발생: {e}")
        return None


def find_tshark():
    """tshark 실행 파일 경로를 찾습니다 (PATH -> Wireshark 기본 설치 경로 순)."""
    exe = shutil.which("tshark")
    if exe:
        return exe

    default_path = r"C:\Program Files\Wireshark\tshark.exe"
    if os.path.exists(default_path):
        return default_path

    return None


SIP_TSHARK_FIELDS = [
    "frame.time_relative",
    "ip.src",
    "ip.dst",
    "sip.Request-Line",
    "sip.Status-Line",
    "sip.Call-ID",
]


def _sip_event_from_fields(parts, fields=SIP_TSHARK_FIELDS):
    """tshark -T fields 한 줄(탭 구분)을 SIP 이벤트 dict로 변환합니다.
    오프라인 pcap 분석과 실시간 스트리밍 분석이 이 로직을 함께 사용합니다.
    이벤트가 아니면(SIP 요청/응답 라인이 아니면) None을 반환합니다.
    """
    while len(parts) < len(fields):
        parts.append("")
    _time_rel, src, dst, request_line, status_line, call_id = parts[:6]
    request_line = request_line.strip()
    status_line = status_line.strip()

    if request_line:
        method = request_line.split(" ")[0]
        return {
            "is_response": False,
            "title": method,
            "detail": f"{src} → {dst} | {request_line} (Call-ID: {call_id})",
        }
    elif status_line:
        return {
            "is_response": True,
            "title": status_line,
            "detail": f"{src} → {dst} | Call-ID: {call_id}",
        }
    return None


def parse_sip_flow_from_pcap(pcap_path):
    """pcap 파일에서 tshark로 SIP 메시지만 뽑아 순서대로 이벤트 리스트를 반환합니다.
    각 이벤트: {"is_response": bool, "title": str, "detail": str}
    """
    tshark_path = find_tshark()
    if not tshark_path:
        print("❌ tshark를 찾을 수 없습니다. Wireshark(tshark)가 설치되어 있는지 확인해주세요.")
        return []

    cmd = [tshark_path, "-r", pcap_path, "-Y", "sip", "-T", "fields"]
    for f in SIP_TSHARK_FIELDS:
        cmd += ["-e", f]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except Exception as e:
        print(f"❌ tshark 실행 중 오류 발생: {e}")
        return []

    events = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        ev = _sip_event_from_fields(line.split("\t"))
        if ev:
            events.append(ev)

    return events


def _dismiss_pcapdroid_onboarding(d, timeout=5):
    """PCAPdroid 최초 실행 시 뜨는 OnBoardingActivity 튜토리얼 화면을 스킵합니다.
    resourceId(com.emanuelef.remote_capture:id/skip)로 우선 탐지하고,
    구버전/텍스트만 있는 경우를 대비해 텍스트 매칭도 백업으로 시도합니다."""
    skip_btn = d(resourceId="com.emanuelef.remote_capture:id/skip")
    if skip_btn.wait(timeout=timeout):
        print("- 최초 실행 튜토리얼(OnBoarding) 감지! [skip] 버튼을 클릭합니다.")
        skip_btn.click()
        time.sleep(1)
        return True

    for skip_text in ("SKIP", "Skip"):
        if d(text=skip_text).exists:
            print(f"- 최초 실행 튜토리얼 감지! [{skip_text}] 버튼을 클릭합니다.")
            d(text=skip_text).click()
            time.sleep(1)
            return True

    return False


def _grant_pcapdroid_permission_popups(d, timeout=5, max_attempts=3):
    """OnBoarding 직후 뜨는 시스템 권한 요청(GrantPermissionsActivity) 팝업을 허용합니다.
    알림/VPN 등 여러 개가 연달아 뜰 수 있어 최대 max_attempts번 반복 처리합니다."""
    allow_btn = d(resourceId="com.android.packageinstaller:id/permission_allow_button")
    granted = False
    for _ in range(max_attempts):
        if not allow_btn.wait(timeout=timeout):
            break
        print("- 시스템 권한 요청 팝업 감지! [허용] 버튼을 클릭합니다.")
        allow_btn.click()
        time.sleep(1)
        granted = True
    return granted


def _ensure_pcapdroid_target_apps(d):
    """Target apps에 EveryTalk이 켜져 있는지 점검하고, 아니면 켭니다.
    메인 화면만으로 이미 설정 완료 상태(스위치 ON + EveryTalk 선택됨)면 화면 이동 없이 바로 통과합니다."""
    app_filter_switch = d(
        resourceId="com.emanuelef.remote_capture:id/app_filter_switch"
    )

    # [0] 메인 화면만으로 이미 설정 완료 상태인지 판단 (스위치 ON + EveryTalk 선택됨)
    already_configured = app_filter_switch.exists and app_filter_switch.info.get(
        "checked"
    ) and d(
        resourceId="com.emanuelef.remote_capture:id/description",
        textContains="com.EveryTalk.Global",
    ).exists

    if already_configured:
        print("- ✅ 메인 화면에서 [EveryTalk] 타겟 앱 설정을 이미 확인했습니다. (화면 이동 패스!)")
        return

    # [1] app_filter_switch가 꺼져있으면 켠다
    if app_filter_switch.exists and not app_filter_switch.info.get("checked"):
        print("- Target apps 필터 스위치가 OFF 상태입니다. ON으로 켭니다.")
        app_filter_switch.click()
        time.sleep(1)

    # [2] Target apps 상세 화면(AppFilterActivity)으로 진입
    print("- Target apps 상세 화면으로 진입합니다.")
    d(text="Target apps").click()
    time.sleep(2)

    # [3] 리스트에 EveryTalk이 이미 보이면 검색 없이 바로 토글로 넘어간다
    everytalk_visible = d(
        resourceId="com.emanuelef.remote_capture:id/app_name",
        textContains="EveryTalk",
    ).exists

    if not everytalk_visible:
        print("- 목록에서 [EveryTalk]을 찾지 못했습니다. 시스템 앱 표시 후 검색합니다.")

        # [3-1] 3닷 메뉴(옵션 더보기) → 시스템 앱 표시 체크박스 켜기
        more_options_btn = d(description="옵션 더보기")
        if not more_options_btn.exists:
            more_options_btn = d(description="More options")

        if more_options_btn.exists:
            more_options_btn.click()
            time.sleep(1)

            checkbox = d(resourceId="com.emanuelef.remote_capture:id/checkbox")
            if not checkbox.exists:
                checkbox = d(className="android.widget.CheckBox")

            if checkbox.exists and not checkbox.info.get("checked"):
                print("- [Show system apps] 활성화합니다.")
                checkbox.click()
                time.sleep(1.5)
            elif checkbox.exists:
                print("- [Show system apps] 이미 체크되어 있습니다! (유지)")
                d.press("back")
                time.sleep(1)

        # [3-2] 검색 버튼 클릭 및 앱 검색 (소문자 everytalk)
        search_btn = d(resourceId="com.emanuelef.remote_capture:id/search")
        if not search_btn.exists:
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

    # [5] 검색된 앱 토글 켜기
    toggle_btn = d(resourceId="com.emanuelef.remote_capture:id/toggle_btn")
    if toggle_btn.exists:
        is_on = toggle_btn.info.get("checked")
        if not is_on:
            print("- [EveryTalk] 토글을 ON으로 변경합니다!")
            toggle_btn.click()
            time.sleep(1)
        else:
            print("- [EveryTalk] 토글이 이미 ON 상태입니다.")
    else:
        print("- ❌ [EveryTalk] 토글 버튼을 찾지 못했습니다.")

    # [6] 메인 화면 복귀 루프
    print("- 셋팅 완료! 메인 화면으로 돌아갑니다.")
    while not d(resourceId="com.emanuelef.remote_capture:id/action_start").exists:
        d.press("back")
        time.sleep(1)


def setup_pcapdroid_settings(uuid, log=print):
    try:
        d = u2.connect(uuid)
    except Exception as e:
        log(f"❌ PCAPdroid 설정 점검 중 기기 연결 실패: {e}")
        return False

    try:
        log("⚙️ PCAPdroid 설정 상태를 점검합니다...")

        if not _wait_pcapdroid_main_screen(d):
            log("❌ PCAPdroid 메인 화면 로딩 실패")
            return False

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
        # 2. Target apps 스마트 점검
        # ----------------------------------------------------
        _ensure_pcapdroid_target_apps(d)

        # ----------------------------------------------------
        # 3. 캡처 시작 (상단 Play 버튼 클릭)
        # ----------------------------------------------------
        play_btn = d(resourceId="com.emanuelef.remote_capture:id/action_start")
        if play_btn.exists:
            log("- ▶️ 상단 Play 버튼을 클릭하여 캡처를 시작합니다!")
            play_btn.click()

            # 🌟 [업그레이드] 최대 2번 뜨는 팝업 스마트 처리
            # (처음 실행이면 2번 누르고, 두 번째 실행이면 바로 break로 빠져나감)
            for i in range(2):
                time.sleep(1.5)  # 팝업창 뜰 시간 살짝 대기

                if d(text="OK").exists:
                    log(f"- 권한/안내 팝업 감지 ({i+1}/2) : [OK] 클릭")
                    d(text="OK").click()
                elif d(text="확인").exists:
                    log(f"- 권한/안내 팝업 감지 ({i+1}/2) : [확인] 클릭")
                    d(text="확인").click()
                else:
                    # 화면에 더 이상 OK나 확인 버튼이 없다면 반복문 즉시 탈출!
                    break

            log("✅ PCAPdroid 캡처가 정상적으로 실행되었습니다!")

            # ----------------------------------------------------
            # 4. EveryTalk 앱 실행
            # ----------------------------------------------------
            log("- 📱 EveryTalk 앱을 실행합니다...")
            d.app_start("com.EveryTalk.Global")
            time.sleep(2)
            return True
        else:
            log("❌ Play 버튼을 찾지 못했습니다.")
            return False

    except Exception as e:
        log(f"❌ 설정 점검 및 실행 중 오류 발생: {e}")
        return False


def _send_pcapdroid_action(uuid, action):
    """PCAPdroid의 CaptureCtrl 액티비티에 START/STOP 인텐트를 보냅니다.
    실측 결과 이 원격 제어 인텐트는 매번 'PCAPdroid control request' 승인 팝업이 뜨고
    이전 액티비티 인스턴스를 재사용해 무시되는 경우가 있어 신뢰도가 낮았습니다.
    그래서 실제 캡처 시작은 _tap_pcapdroid_play_button()을 쓰고, 이 함수는 STOP을
    보수적으로 한 번 더 시도해보는 best-effort 용도로만 남겨둡니다."""
    try:
        cmd = f"adb -s {uuid} shell am start -n com.emanuelef.remote_capture/.activities.CaptureCtrl -a com.emanuelef.remote_capture.action.{action}"
        subprocess.run(cmd, shell=True, check=True)
        return True
    except Exception as e:
        print(f"❌ PCAPdroid {action} 인텐트 실패: {e}")
        return False


def _tap_pcapdroid_play_button(uuid):
    """PCAPdroid 메인 화면의 Play 버튼을 눌러 캡처를 시작합니다.
    uiautomator2 객체의 click()이 이 앱에서는 종종 씹혀서(클릭이 실제로 전달 안 됨),
    실측으로 확인된 '버튼 중심 좌표를 직접 탭'하는 방식만 안정적으로 캡처를 시작시켰습니다."""
    try:
        d = u2.connect(uuid)
        if not _wait_pcapdroid_main_screen(d):
            print("❌ PCAPdroid 메인 화면 로딩 실패")
            return False

        btn = d(resourceId="com.emanuelef.remote_capture:id/action_start")
        if not btn.exists:
            print("❌ PCAPdroid Play 버튼을 찾지 못했습니다.")
            return False

        info = btn.info
        cx = (info["bounds"]["left"] + info["bounds"]["right"]) // 2
        cy = (info["bounds"]["top"] + info["bounds"]["bottom"]) // 2
        d.click(cx, cy)

        # VPN 권한 재확인 팝업이 뜨는 기종을 대비한 방어 코드
        for _ in range(3):
            time.sleep(1)
            if d(resourceId="com.emanuelef.remote_capture:id/allow_btn").exists:
                d(resourceId="com.emanuelef.remote_capture:id/allow_btn").click()
            elif d(text="OK").exists:
                d(text="OK").click()
            elif d(text="확인").exists:
                d(text="확인").click()

        return True
    except Exception as e:
        print(f"❌ PCAPdroid Play 버튼 탭 실패: {e}")
        return False


def _select_pcapdroid_dump_mode(d, mode_text, timeout=8):
    """메인 화면의 덤프 모드 스피너를 열어 지정한 모드로 전환합니다.
    스피너를 직접 클릭하기 때문에 현재 모드가 무엇이든 상관없이 동작합니다."""
    spinner = d(resourceId="com.emanuelef.remote_capture:id/dump_mode_spinner")
    if not spinner.wait(timeout=timeout):
        return False
    spinner.click()
    time.sleep(1)
    target = d(text=mode_text)
    if not target.wait(timeout=timeout):
        return False
    target.click()
    time.sleep(1)
    return True


def _wait_pcapdroid_main_screen(d, timeout=20):
    """PCAPdroid 메인 화면(EveryTalkMain 아님, PCAPdroid 자체 메인)이 떴는지 확인합니다.
    'Ready' 텍스트는 캡처가 꺼져있을 때만 뜨므로, 직전 세션이 캡처를 켠 채로 남아있으면
    영원히 못 찾고 타임아웃납니다. 캡처 상태와 무관하게 항상 존재하는 설정(⚙️) 버튼도
    함께 확인해서 캡처 진행 중에도 메인 화면 로딩으로 인식하도록 합니다.

    최초 설치 직후에는 OnBoarding 튜토리얼/권한 팝업이 렌더링되는 타이밍이 기기마다
    들쭉날쭉해서, 시작할 때 딱 한 번만 스킵을 시도하면 늦게 뜬 튜토리얼을 놓치고 그대로
    멈춰버립니다. 그래서 메인 화면이 보일 때까지 매 반복마다 스킵/허용을 계속 재시도합니다."""
    d.app_start("com.emanuelef.remote_capture")
    time.sleep(2)

    settings_btn = d(resourceId="com.emanuelef.remote_capture:id/action_settings")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if d(text="Ready").exists or settings_btn.exists:
            return True
        _dismiss_pcapdroid_onboarding(d, timeout=1)
        _grant_pcapdroid_permission_popups(d, timeout=1)
        time.sleep(0.3)
    return False


def _confirm_pcapdroid_dialog(d, timeout=5):
    """PCAPdroid 설정 다이얼로그(SettingsActivity)의 확인 버튼(android:id/button1)을 클릭합니다."""
    btn = d(resourceId="android:id/button1")
    if btn.wait(timeout=timeout):
        btn.click()
        time.sleep(1)
        return True
    return False


def configure_pcapdroid_tcp_exporter(uuid, host="127.0.0.1", port=15123, log=print):
    """PCAPdroid의 덤프 모드를 'TCP exporter'로 바꾸고 Collector IP/Port를 설정합니다.
    이 모드는 pcap-over-ip로 캡처 내용을 실시간 스트리밍해주는 PCAPdroid 공식 기능입니다."""
    try:
        d = u2.connect(uuid)

        if not _wait_pcapdroid_main_screen(d):
            log("❌ PCAPdroid 메인 화면 로딩 실패 (기기 화면이 잠겨 있지 않은지 확인해 주세요)")
            return False

        settings_btn = d(resourceId="com.emanuelef.remote_capture:id/action_settings")
        if not settings_btn.exists:
            log("❌ PCAPdroid 설정 버튼을 찾지 못했습니다.")
            return False
        settings_btn.click()
        time.sleep(1)

        if not d(text="Collector IP address").wait(timeout=5):
            log("❌ Collector IP address 설정 항목을 찾지 못했습니다.")
            d.press("back")
            return False

        # Collector IP address: 이미 host와 같으면 눌러서 재설정하지 않고 스킵
        ip_summary = d(text="Collector IP address").sibling(
            resourceId="android:id/summary"
        )
        if ip_summary.exists and ip_summary.get_text() == host:
            log(f"- Collector IP address가 이미 {host}로 설정되어 있습니다. (스킵)")
        else:
            d(text="Collector IP address").click()
            time.sleep(1)
            ip_field = d(className="android.widget.EditText")
            ip_field.wait(timeout=5)
            if ip_field.get_text() != host:
                ip_field.set_text(host)
            if not _confirm_pcapdroid_dialog(d):
                log("❌ Collector IP address 확인 버튼을 찾지 못했습니다.")
                d.press("back")
                return False

        # Collector port: 이미 port와 같으면 눌러서 재설정하지 않고 스킵
        port_summary = d(text="Collector port").sibling(
            resourceId="android:id/summary"
        )
        if port_summary.exists and port_summary.get_text() == str(port):
            log(f"- Collector port가 이미 {port}로 설정되어 있습니다. (스킵)")
        else:
            d(text="Collector port").click()
            time.sleep(1)
            port_field = d(className="android.widget.EditText")
            port_field.wait(timeout=5)
            if port_field.get_text() != str(port):
                port_field.set_text(str(port))
            if not _confirm_pcapdroid_dialog(d):
                log("❌ Collector port 확인 버튼을 찾지 못했습니다.")
                d.press("back")
                return False

        d.press("back")
        time.sleep(1)

        # 메인 화면 dump_mode_spinner가 이미 TCP exporter면 드롭다운 전환은 스킵
        spinner_title = d(
            resourceId="com.emanuelef.remote_capture:id/dump_mode_spinner"
        ).child(resourceId="com.emanuelef.remote_capture:id/title")
        if spinner_title.exists and spinner_title.get_text() == "TCP exporter":
            log("- Dump mode가 이미 TCP exporter입니다. (스킵)")
        else:
            if not _select_pcapdroid_dump_mode(d, "TCP exporter"):
                log("❌ TCP exporter 모드로 전환하지 못했습니다.")
                return False

        log(f"✅ PCAPdroid를 TCP exporter 모드로 전환했습니다 (수신지: {host}:{port})")

        # Target apps 점검 (EveryTalk 켜져 있는지 확인)
        _ensure_pcapdroid_target_apps(d)

        # 상단 Play 버튼 클릭 (일반 click()이 종종 씹혀서 좌표 탭 방식 사용)
        if not _tap_pcapdroid_play_button(uuid):
            log("❌ PCAPdroid Play 버튼을 누르지 못했습니다.")
            return False

        log("- 📱 EveryTalk 앱을 실행합니다...")
        d.app_start("com.EveryTalk.Global")

        return True
    except Exception as e:
        log(f"❌ TCP exporter 모드 설정 중 오류: {e}")
        return False


def switch_pcapdroid_to_pcap_file_mode(uuid, log=print):
    """실시간 스트리밍(TCP exporter)에서 수동 파일 캡처(PCAP file) 모드로 되돌립니다."""
    try:
        d = u2.connect(uuid)
        if not _wait_pcapdroid_main_screen(d):
            log("❌ PCAPdroid 메인 화면 로딩 실패")
            return False
        if not _select_pcapdroid_dump_mode(d, "PCAP file"):
            log("❌ PCAP file 모드로 복원하지 못했습니다.")
            return False
        log("✅ PCAPdroid를 PCAP file 모드로 복원했습니다.")
        return True
    except Exception as e:
        log(f"❌ PCAP file 모드 복원 중 오류: {e}")
        return False


def run_realtime_sip_stream(uuid, on_event, stop_event, state, host="127.0.0.1", port=15123, log=print):
    """PCAPdroid를 TCP exporter 모드로 캡처를 시작해 pcap-over-ip 스트림을 실시간으로
    tshark에 흘려보내고, SIP 메시지가 나올 때마다 on_event(dict)를 호출합니다.

    stop_event가 set되면(또는 스트림이 끊기면) 캡처를 멈추고 정리한 뒤 반환합니다.
    state 딕셔너리에 소켓/프로세스 핸들을 채워두므로, 호출 측에서 stop_event를 set한
    직후 state 안의 객체들을 닫아버리면 블로킹 중인 accept/readline을 즉시 풀 수 있습니다.
    """
    import socket

    tshark_path = find_tshark()
    if not tshark_path:
        log("❌ tshark를 찾을 수 없어 실시간 SIP Flow를 시작할 수 없습니다.")
        return

    if not ensure_pcapdroid_installed(uuid, log=log):
        return

    subprocess.run(["adb", "-s", uuid, "reverse", f"tcp:{port}", f"tcp:{port}"])

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)
    server.settimeout(1.0)
    state["server"] = server

    if stop_event.is_set():
        server.close()
        subprocess.run(["adb", "-s", uuid, "reverse", "--remove", f"tcp:{port}"])
        return

    # 리스너를 먼저 띄운 뒤 PCAPdroid 설정+Play+EveryTalk 실행까지 진행
    # (Play를 먼저 누르면 수신 대기 중인 소켓이 없어 TCP exporter 연결이 즉시 실패함)
    if not configure_pcapdroid_tcp_exporter(uuid, host, port, log=log):
        server.close()
        subprocess.run(["adb", "-s", uuid, "reverse", "--remove", f"tcp:{port}"])
        return
    log("📡 실시간 SIP Flow 스트리밍 대기 중 (PCAPdroid → TCP exporter)...")

    conn = None
    tshark_proc = None
    try:
        while not stop_event.is_set() and conn is None:
            try:
                conn, _ = server.accept()
                state["conn"] = conn
            except socket.timeout:
                continue
            except OSError:
                break

        if conn is None:
            log("⏹ 실시간 SIP Flow 스트리밍이 연결 없이 중단되었습니다 (PCAPdroid가 TCP exporter로 접속하지 않음).")
            return

        cmd = [tshark_path, "-r", "-", "-l", "-Y", "sip", "-T", "fields"]
        for f in SIP_TSHARK_FIELDS:
            cmd += ["-e", f]

        tshark_proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        state["proc"] = tshark_proc

        def feeder():
            try:
                conn.settimeout(1.0)
                while not stop_event.is_set():
                    try:
                        data = conn.recv(65536)
                    except socket.timeout:
                        continue
                    except OSError:
                        break
                    if not data:
                        break
                    tshark_proc.stdin.write(data)
                    tshark_proc.stdin.flush()
            except Exception:
                pass
            finally:
                try:
                    tshark_proc.stdin.close()
                except Exception:
                    pass

        threading.Thread(target=feeder, daemon=True).start()
        log("✅ 실시간 SIP Flow 스트리밍 시작!")

        while not stop_event.is_set():
            raw = tshark_proc.stdout.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace")
            if not line.strip():
                continue
            ev = _sip_event_from_fields(line.split("\t"))
            if ev:
                on_event(ev)
    finally:
        try:
            if tshark_proc:
                tshark_proc.terminate()
        except Exception:
            pass
        try:
            if conn:
                conn.close()
        except Exception:
            pass
        # 익스포터 연결이 끊기면 PCAPdroid가 캡처를 자체적으로 멈추는 걸 실측으로 확인했지만,
        # 혹시 안 멈추는 경우를 대비해 원격 제어 인텐트로 STOP을 한 번 더 시도해봅니다 (best-effort).
        _send_pcapdroid_action(uuid, "STOP")
        try:
            server.close()
        except Exception:
            pass
        subprocess.run(["adb", "-s", uuid, "reverse", "--remove", f"tcp:{port}"])
        print("🛑 실시간 SIP Flow 스트리밍 종료.")


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
        d.press(17)  # *
        d.press(17)  # *
        d.press(16)  # 9
        d.press(18)  # #
        d.press(18)  # #
        time.sleep(2)  # 히든 메뉴 화면 뜰 때까지 대기

        # 🌟 3. 현재 상태 스마트 체크 및 덮어쓰기 분기안내
        # 만약 화면에 'PCAP DUMP STOP'이 보인다면 이미 실행 중인 상태입니다!
        if d(text="PCAP DUMP STOP").exists:
            print(
                "- ⚠️ 이미 PCAP 캡처가 실행 중입니다. [STOP ➡️ START] 재시작을 진행합니다."
            )
            d(text="PCAP DUMP STOP").click()
            time.sleep(1.5)  # 꺼질 때까지 대기

            # 혹시 STOP 버튼 누른 후에도 확인/OK 팝업이 뜨는 기종이라면 클릭 처리 (방어 코드)
            if d(text="OK").exists:
                d(text="OK").click()
            elif d(text="확인").exists:
                d(text="확인").click()
            time.sleep(1)

        # 🌟 4. PCAP DUMP START 실행 및 후속 OK 팝업 처리
        if d(text="PCAP DUMP START").exists:
            print("- [PCAP DUMP START] 버튼을 클릭합니다.")
            d(text="PCAP DUMP START").click()
            time.sleep(1.5)  # START 클릭 후 뜨는 안내 팝업 대기

            # 🚀 핵심: START 클릭 직후 뜨는 OK/확인 팝업 자동 클릭!
            if d(text="OK").exists:
                print("- 팝업 감지: [OK] 클릭 완료")
                d(text="OK").click()
            elif d(text="확인").exists:
                print("- 팝업 감지: [확인] 클릭 완료")
                d(text="확인").click()

            print("✅ 단말자체 PCAP 캡처가 성공적으로 시작되었습니다!")
            time.sleep(1)
            d.press("home")  # 홈 화면으로 복귀
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
            d.press(17)
            d.press(17)
            d.press(16)
            d.press(18)
            d.press(18)
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
