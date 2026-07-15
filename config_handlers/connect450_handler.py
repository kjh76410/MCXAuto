import time


class Connect450Handler:
    def run(self, d, env):
        print("🚀 450connect 환경 설정 자동화 시작!")

        try:
            # 1. 로그인 ID 입력창에 debug_lte_only 입력
            print("[Step 1] 로그인 ID에 debug_lte_only 입력 중...")
            login_id_field = d(resourceId="com.EveryTalk.Global:id/login_id")
            if login_id_field.wait(timeout=5.0):
                login_id_field.set_text("debug_lte_only")
                d.press("back")  # 입력 후 키보드 닫기
                time.sleep(0.5)
            else:
                print("❌ 로그인 ID 입력창을 찾을 수 없습니다.")
                return

            # 2. 로그인 버튼 선택
            print("[Step 2] 로그인 버튼 클릭...")
            login_btn = d(resourceId="com.EveryTalk.Global:id/login_btn")
            if login_btn.exists:
                login_btn.click()
                time.sleep(1.0)  # 버튼 누른 후 반응 시간 대기
            else:
                print("❌ 로그인 버튼을 찾을 수 없습니다.")
                return

            # 3. 서버 설정 버튼 클릭
            print("[Step 3] 서버 설정 진입...")
            setup_btn = d(resourceId="com.EveryTalk.Global:id/server_setup")
            if setup_btn.wait(timeout=5.0):
                setup_btn.click()
                time.sleep(1.0)  # 팝업 창이 완전히 뜰 때까지 대기
            else:
                print("❌ 서버 설정 버튼을 찾을 수 없습니다.")
                return

            # 4. 서버 IP 입력 (auth_1, auth_2 모두 초기화)
            print("[Step 4] 기존 IP 지우고 새 IP 입력 중...")
            server_input = d(resourceId="com.EveryTalk.Global:id/auth_1_textedit")
            server_input_2 = d(
                resourceId="com.EveryTalk.Global:id/auth_2_textedit"
            )  # 두 번째 입력창 찾기

            if server_input.exists:
                # 첫 번째 입력창 지우기
                server_input.clear_text()
                time.sleep(0.5)

                # 두 번째 입력창이 존재하면 같이 지우기
                if server_input_2.exists:
                    print("ℹ️ auth_2 입력창 발견! 함께 지웁니다.")
                    server_input_2.clear_text()
                    time.sleep(0.5)

                # 첫 번째 입력창에 새 IP 입력
                server_input.set_text("192.168.11.113")
                d.press("back")  # 키보드 가림 방지
                time.sleep(0.5)
            else:
                print("ℹ️ 서버 주소 입력창이 없습니다. (다음 단계로 진행)")

            # 5. LTE 체크박스 상태 확인 및 제어
            print("[Step 5] LTE 체크박스 상태 확인 중...")
            lte_checkbox = d(resourceId="com.EveryTalk.Global:id/checkbox_lte")

            if lte_checkbox.exists:
                # .info.get('checked')를 통해 실제 체크 여부(True/False)를 판단합니다.
                is_checked = lte_checkbox.info.get("checked", False)

                if is_checked:
                    print("체크박스가 선택되어 있으므로 클릭하여 해제합니다.")
                    lte_checkbox.click()
                    time.sleep(0.5)
                else:
                    print("체크박스가 이미 해제되어 있으므로 그대로 둡니다.")
            else:
                print("❌ LTE 체크박스 요소를 찾을 수 없습니다.")
                return

            # 6. OK 버튼 클릭하여 최종 저장
            print("[Step 6] OK 버튼 눌러서 저장...")
            ok_btn = d(resourceId="com.EveryTalk.Global:id/sel_ok")

            if ok_btn.exists:
                ok_btn.click()
                print("✅ 450connect 전체 환경 설정 및 제어 완료!")
            else:
                print("❌ OK 버튼을 찾을 수 없습니다.")

            self.device_log_command()

        except Exception as e:
            print(f"❌ 450connect 자동화 중 오류 발생: {e}")

    # ==========================================
    # 🚨 비상통화(Emergency/Imminent Peril) 발신용 함수
    # ==========================================
    def make_emergency_call(self, d, imminent=False, log_console=None):
        """
        메인 화면(com.cybertel.mcptt.ui.main.EveryTalkMain)의 main_menu_em_key를 눌러
        비상통화를 발신합니다. EmergencyAlert 팝업이 뜨면 imminent 여부에 따라
        btnEmgYes 또는 btnEmgImminent를 눌러 확정합니다. (대상은 WAS에 사전설정된
        고정 그룹이라 그룹명을 화면에서 찾을 필요가 없습니다.)
        """

        def print_log(msg):
            print(msg)
            if log_console:
                log_console.insert("end", f"{msg}\n")
                log_console.see("end")

        def go_home():
            # 💡 [핵심] EveryTalkMain 메인 화면의 채널명 표시(enter_ch_name)가 보일 때까지
            # 뒤로가기를 반복해서, 다른 화면에 있어도 항상 메인 화면부터 시나리오를 시작합니다.
            home_marker = d(resourceId="com.EveryTalk.Global:id/enter_ch_name")
            for i in range(5):
                if home_marker.exists:
                    return True
                print_log(f"🔙 메인 화면(EveryTalkMain)을 찾기 위해 뒤로가기를 누릅니다. ({i + 1}/5)")
                d.press("back")
                time.sleep(1.0)
            return home_marker.exists

        mode_label = "Imminent Peril" if imminent else "Emergency"
        print_log(f"\n[Call] 🚨 {mode_label} 발신을 시작합니다.")

        try:
            d.app_start("com.EveryTalk.Global", stop=False)
            time.sleep(1.5)

            if not go_home():
                print_log("❌ 메인 화면(EveryTalkMain)을 찾지 못해 발신을 진행할 수 없습니다.")
                return

            em_key = d(resourceId="com.EveryTalk.Global:id/main_menu_em_key")
            if not em_key.wait(timeout=5.0):
                print_log("❌ main_menu_em_key 버튼을 찾을 수 없습니다.")
                return
            em_key.click()

            confirm_id = (
                "com.EveryTalk.Global:id/btnEmgImminent"
                if imminent
                else "com.EveryTalk.Global:id/btnEmgYes"
            )
            confirm_btn = d(resourceId=confirm_id)
            if not confirm_btn.wait(timeout=5.0):
                print_log("❌ EmergencyAlert 확인 버튼을 찾을 수 없습니다.")
                return
            confirm_btn.click()

            print_log(f"✅ {mode_label} 발신 시나리오 완료!")

        except Exception as e:
            print_log(f"❌ {mode_label} 발신 중 오류 발생: {e}")
