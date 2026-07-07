import subprocess
import os
import time


class NetworkManager:
    """
    단말기의 네트워크(WiFi, LTE) 및 배터리 상태를 조회하고 제어하는 매니저 클래스입니다.
    """

    @staticmethod
    def get_battery_level(uuid):
        """현재 배터리 잔량을 가져옵니다."""
        try:
            cmd = f"adb -s {uuid} shell dumpsys battery"
            result = subprocess.check_output(cmd, shell=True, text=True, encoding='utf-8', errors='ignore')
            
            for line in result.split('\n'):
                if "level:" in line:
                    return line.split(':')[1].strip() + "%"
            return "알 수 없음"
        except Exception as e:
            print(f"[NetworkManager] ⚠️ 배터리 정보 조회 실패: {e}")
            return "-"

    @staticmethod
    def get_network_status(uuid):
        """현재 활성화된 네트워크 상태(WiFi 또는 모바일 데이터+통신사)를 가져옵니다."""
        try:
            cmd = f"adb -s {uuid} shell ip route"
            result = subprocess.check_output(cmd, shell=True, text=True, encoding='utf-8', errors='ignore')
            
            if "wlan" in result:
                return "WiFi 연결됨"
            elif "rmnet" in result or "ccmni" in result:  # rmnet(퀄컴), ccmni(미디어텍)
                # 통신사 이름(SKT, KT, LGU+) 가져오기
                carrier_cmd = f"adb -s {uuid} shell getprop gsm.operator.alpha"
                carrier = subprocess.check_output(carrier_cmd, shell=True, text=True, encoding='utf-8', errors='ignore').strip()
                # 듀얼심인 경우 콤마로 구분되므로 첫 번째 통신사만 추출
                carrier = carrier.split(',')[0] if carrier else "데이터"
                return f"Mobile ({carrier})"
            else:
                return "네트워크 끊김"
        except Exception as e:
            print(f"[NetworkManager] ⚠️ 네트워크 상태 조회 실패: {e}")
            return "확인 불가"

    @staticmethod
    def set_wifi_state(uuid, state: bool):
        """
        WiFi를 켜거나 끕니다.
        - state: True(ON), False(OFF)
        """
        action = "enable" if state else "disable"
        os.system(f"adb -s {uuid} shell svc wifi {action}")
        print(f"[NetworkManager] ▶ WiFi {'ON' if state else 'OFF'} 명령어 전송 완료")

    @staticmethod
    def set_data_state(uuid, state: bool):
        """
        모바일 데이터(LTE/5G)를 켜거나 끕니다.
        - state: True(ON), False(OFF)
        """
        action = "enable" if state else "disable"
        os.system(f"adb -s {uuid} shell svc data {action}")
        print(f"[NetworkManager] ▶ LTE Data {'ON' if state else 'OFF'} 명령어 전송 완료")

    @staticmethod
    def connect_to_wifi(uuid, ssid, password=None):
        """
        지정된 SSID로 WiFi에 연결합니다. (안드로이드 10 이상 지원)
        화면을 직접 터치하는 방식 대신, 안드로이드 내부 시스템 명령어를 사용해 더 안정적입니다.
        """
        print(f"[NetworkManager] 🔗 '{ssid}' 연결 시도 중...")
        
        # 사용자가 눈으로 확인할 수 있게 WiFi 설정 창을 먼저 띄워줍니다.
        os.system(f"adb -s {uuid} shell am start -a android.settings.WIFI_SETTINGS")
        time.sleep(1) # 화면이 뜰 때까지 1초 대기
        
        # 비밀번호 유무에 따라 연결 명령어 분기
        if password:
            # WPA2(일반적인 비밀번호) 보안 연결
            cmd = f'adb -s {uuid} shell cmd wifi connect-network "{ssid}" wpa2 "{password}"'
        else:
            # 개방형(비밀번호 없음) 연결
            cmd = f'adb -s {uuid} shell cmd wifi connect-network "{ssid}" open'
            
        os.system(cmd)
        print("[NetworkManager] ▶ 연결 명령어 전송 완료 (단말기 화면에서 확인하세요)")