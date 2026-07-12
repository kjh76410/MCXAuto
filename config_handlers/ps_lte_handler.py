import time
import subprocess


class PsLteHandler:
    def __init__(self):
        pass

    def run(self, d, env):
        """
        재난망(PS-LTE) 환경설정을 자동으로 수행합니다.
        :param d: uiautomator2 객체 (단말기 제어용)
        :param env: JSON에서 읽어온 설정 데이터
        """
        print("🚨 재난망(PS-LTE) 단말 환경 설정을 시작합니다...")

        try:
            # 1. 앱을 화면 맨 앞으로 부르기 (기존 상태 유지, 로그아웃 안 됨!)
            print("📱 앱을 화면에 띄웁니다.")
            d.app_start("com.EveryTalk.Global")
            time.sleep(2)

            # ==========================================
            # 💡 [새로운 로직] 3-dot 메뉴가 보일 때까지 '뒤로가기' 연타!
            # ==========================================
            print("🔙 메인 화면을 찾기 위해 상태를 점검합니다.")

            for i in range(5):  # 최대 5번까지만 뒤로가기 시도 (무한루프 방지)
                three_dot_btn = d(resourceId="com.EveryTalk.Global:id/phone_cmd_more")

                if three_dot_btn.exists:
                    print("✅ 메인 화면(ContactActivity) 도착 완료!")
                    break  # 찾았으면 반복문 탈출!
                else:
                    print(f"  - 다른 화면에 있습니다. 뒤로가기를 누릅니다. ({i+1}/5)")
                    d.press("back")
                    time.sleep(1)  # 화면이 넘어갈 시간 주기
            else:
                # 5번이나 눌렀는데도 못 찾았을 경우
                print(
                    "⚠️ 메인 화면을 찾지 못했습니다. 앱이 꼬인 것 같으니 초기화면 진입을 확인해주세요."
                )
                return

            setup_btn = d(resourceId="com.EveryTalk.Global:id/main_menu_setup")
            if setup_btn.exists:
                setup_btn.click()
                time.sleep(1)

            # 2. '엔지니어 설정' 메뉴가 이미 떠 있는지 확인
            # textContains를 쓰면 "엔지니어 설정" 글자가 약간 달라도 찰떡같이 찾습니다.
            engineer_menu = d(
                resourceId="com.EveryTalk.Global:id/list_item_name",
                textContains="엔지니어",
            )

            if not engineer_menu.exists:
                print("🔒 엔지니어 설정 메뉴가 숨겨져 있습니다. 해제를 시도합니다.")

                # 소프트웨어 버전명 5번 연속 탭 (for문으로 0.1초 간격으로 빠르게 다다다닥!)
                version_btn = d(resourceId="com.EveryTalk.Global:id/opt_ver")
                for _ in range(5):
                    version_btn.click()
                    time.sleep(0.1)

                # 비밀번호 1231 입력 후 확인 버튼
                d(resourceId="com.EveryTalk.Global:id/pass_edit").set_text("1231")
                d(resourceId="com.EveryTalk.Global:id/sel_ok").click()
                time.sleep(1)  # 메뉴가 나타날 때까지 대기

            # 3. 이제 무조건 엔지니어 메뉴가 있을 테니 클릭!
            print("🛠️ 엔지니어 설정 메뉴로 진입합니다.")
            engineer_menu.click()
            time.sleep(1)

            # 4. 스크롤을 살살 내려서 'IP SEC ENABLED' 글자 찾기
            print("🔍 IP SEC ENABLED 항목을 찾는 중...")
            d(scrollable=True).scroll.to(text="IP SEC ENABLED")
            time.sleep(0.5)

            # 5. IP SEC ENABLED 스위치 제어
            ipsec_text = d(text="IP SEC ENABLED")  # 글자 영역
            ipsec_switch = ipsec_text.right(
                resourceId="android:id/switch_widget"
            )  # 스위치 영역

            if ipsec_switch.exists:
                is_checked = ipsec_switch.info.get("checked")

                if is_checked:
                    print("⚡ IP SEC ENABLED가 ON 상태입니다. OFF로 끕니다.")
                    # 💡 [방어 1] 스위치 동그라미 말고, 안전하게 글자 영역(부모 레이아웃)을 클릭합니다.
                    ipsec_text.click()

                    # 💡 [방어 2] 앱 내부 변수가 업데이트되고 애니메이션이 끝날 때까지 충분히 기다립니다. (핵심)
                    time.sleep(1.5)
                else:
                    print("✅ IP SEC ENABLED가 이미 OFF 상태입니다. 건너뜁니다.")
            else:
                print("⚠️ IP SEC ENABLED 스위치를 화면에서 찾을 수 없습니다.")

            # 💡 [방어 3] 화면 빈 곳(맨 위쪽)을 살짝 눌러서 스위치 포커스를 뺍니다.
            d.click(100, 100)
            time.sleep(0.5)

            # 6. 저장 버튼 클릭
            save_btn = d(resourceId="com.EveryTalk.Global:id/btn_save")
            if save_btn.exists:
                save_btn.click()
                print("💾 재난망 설정 저장 완료!")

                # 💡 [방어 4] 저장이 완료되고 DB에 쓰일 때까지 기다려줍니다.
                time.sleep(2.0)
            else:
                print("⚠️ IP SEC ENABLED 스위치를 화면에서 찾을 수 없습니다.")

            # ==========================================
            # 💡 [로그 시작] CybertelLog 앱 띄워서 버튼 누르기
            # ==========================================
            from common_logger import start_device_logging

            # u2 객체(d)와 UI 로그창(self.txt_log)을 넘겨줍니다.
            start_device_logging(d, self.txt_log)
            # ==========================================

            self.txt_log.insert("end", "[System] 완료!\n")

        except Exception as e:
            print(f"❌ LM75 환경 설정 중 치명적 오류 발생: {e}")
            raise e

    # ==========================================
    # 📞 호 발신용 함수
    # ==========================================
    def make_call(self, d, target_info, call_mode="PTT", log_console=None):
        """
        call_mode (PTT 또는 PTV)에 따라 알맞은 Broadcast Intent를 전송합니다.
        """

        def print_log(msg):
            print(msg)
            if log_console:
                log_console.insert("end", f"{msg}\n")
                log_console.see("end")

        serial = d.serial
        print_log(f"🚨 현재 연결된 단말기 시리얼 번호: {serial}")

        # 💡 [중요] 에러가 나면 화면에 다 뱉어내도록 업그레이드된 함수!
        def run_adb(cmd):
            full_cmd = f"adb -s {serial} shell {cmd}"
            print_log(f"💻 ADB 실행: {cmd}")  # 무슨 명령어를 치는지 확인용

            result = subprocess.run(
                full_cmd, shell=True, capture_output=True, text=True
            )
            if result.returncode != 0:
                print_log(f"⚠️ ADB 실행 에러: {result.stderr}")

        print_log(
            f"\n[Call] 🚨 PS-LTE 백그라운드 발신 시작 (대상: {target_info} / 모드: {call_mode})"
        )

        try:
            # ==========================================
            # 🟢 1. 통화 발신 (모드에 따라 명령어 다름)
            # ==========================================
            if call_mode == "PTV":
                print_log(f"📹 영상호(PTV) 발신 중...")
                run_adb(
                    f"am broadcast -a action.mcptt.req.groupvideo.dial --es groupname {target_info}"
                )
            else:
                print_log(f"📞 음성호(PTT) 발신 중...")
                run_adb(
                    f"am broadcast -a action.mcptt.req.groupvoice.call --es groupname {target_info}"
                )

            time.sleep(3.0)

            # ==========================================
            # 🎤 2. 발언권/전송권 제어
            # ==========================================
            print_log(f"🎤 [{call_mode}] 발언권(Talk Right)을 요청합니다.")
            run_adb("am broadcast -a action.mcptt.req.groupcall.talkright.acquire")

            print_log("🗣️ 발언권 획득! 5초간 송출을 유지합니다...")
            time.sleep(5.0)

            print_log(f"🔇 [{call_mode}] 발언권을 반납합니다.")
            run_adb("am broadcast -a action.mcptt.req.groupcall.talkright.release")
            time.sleep(1.0)

            # ==========================================
            # 🛑 3. 통화 종료
            # ==========================================
            if call_mode == "PTV":
                print_log("🛑 영상호(PTV) 통화를 종료합니다 (Release).")
                run_adb("am broadcast -a action.mcptt.req.groupvideo.release")
            else:
                print_log("🛑 음성호(PTT) 통화를 종료합니다 (Deactivate).")
                run_adb("am broadcast -a action.mcptt.req.groupvoice.deactivatechannel")

            print_log(f"✅ '{target_info}' ({call_mode}) 호 발신 시나리오 완료!")

        except Exception as e:
            print_log(f"❌ '{target_info}' 발신 중 오류 발생: {e}")
