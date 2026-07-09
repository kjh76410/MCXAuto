import time


class CTB_POCHandler:
    def run(self, d, env):
        print("🚀 450connect 환경 설정 자동화 시작!")

        try:
            # 1. 서버 설정 버튼 클릭
            print("[Step 1] 서버 설정 진입...")
            setup_btn = d(resourceId="com.EveryTalk.Global:id/server_setup")

            if setup_btn.wait(timeout=5.0):
                setup_btn.click()
                time.sleep(1)  # 팝업 뜰 때까지 대기
            else:
                print("❌ 첫 화면에서 서버 설정 버튼을 찾을 수 없습니다.")
                return

            # 2. 서버 IP 입력창 찾고 지운 뒤 입력하기
            print("[Step 2] 기존 IP 지우고 새 IP 입력 중...")
            server_input = d(resourceId="com.EveryTalk.Global:id/auth_1_textedit")

            if server_input.wait(timeout=5.0):
                # 굳이 X 버튼 안 눌러도 clear_text()로 한 방에 지울 수 있습니다!
                server_input.clear_text()
                time.sleep(0.5)

                # 새 IP 입력
                # (나중에 env["server_ip"] 처럼 JSON 변수로 바꿀 수 있게 하드코딩 일단 해둘게요)
                server_input.set_text("211.118.224.205")

                # 키보드 내리기 (입력 후 키보드가 OK 버튼을 가리는 것 방지)
                d.press("back")
                time.sleep(0.5)
            else:
                print("❌ 서버 주소 입력창을 찾을 수 없습니다.")
                return

            # 3. OK 버튼 클릭
            print("[Step 3] OK 버튼 눌러서 저장...")
            ok_btn = d(resourceId="com.EveryTalk.Global:id/sel_ok")

            if ok_btn.exists:
                ok_btn.click()
                print("✅ 450connect 서버 설정 완료!")
            else:
                print("❌ OK 버튼을 찾을 수 없습니다.")

            self.device_log_command("logcat start")
            self.device_log_command("pcap start")

        except Exception as e:
            print(f"❌ 450connect 자동화 중 오류 발생: {e}")
