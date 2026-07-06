import subprocess

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

# scrcpy 실행 함수 추가
def start_mirroring(uuid):
    # 아까 옮겨둔 폴더의 실행파일 경로를 정확히 지정합니다.
    scrcpy_path = r"C:\scrcpy\scrcpy.exe" 
    
    if os.path.exists(scrcpy_path):
        try:
            # -s 옵션으로 기기 UUID 전달
            subprocess.Popen([scrcpy_path, "-s", uuid])
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("scrcpy.exe 파일을 찾을 수 없습니다. 경로를 확인하세요!")