import os
import time
import random
import subprocess # 💡 [핵심] 이거 없으면 ADB 명령어를 아예 못 날립니다!
import winsound

# 발언(Talk) 중 PC 스피커로 재생할 음성 파일 (assets/audio 폴더에 넣어주세요)
VOICE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "audio",
    "ptt_voice.wav",
)

# IM 메시지 발신 시 무작위로 골라 쓰는 테스트 문구
TEST_MESSAGE_POOL = [
    "테스트 중입니다.",
    "테스트 메시지입니다.",
    "메시지 발신 테스트입니다.",
    "정상 수신 확인 테스트입니다.",
    "통신 품질 테스트 중입니다.",
    "QA 자동화 테스트 메시지입니다.",
]

class PsLteLm75Handler:
    def __init__(self):
        pass

    def run(self, d, env):
        """
        재난망 LM75 모델(PS-LTE) 환경설정을 자동으로 수행합니다.
        (3-dot 메뉴를 거쳐서 진입하는 방식)
        """
        print("🚨 재난망 LM75(PS-LTE) 단말 환경 설정을 시작합니다...")

        try:
            # 1. 앱을 화면 맨 앞으로 부르기 (기존 상태 유지, 로그아웃 안 됨!)
            print("📱 앱을 화면에 띄웁니다.")
            d.app_start("com.EveryTalk.Global")
            time.sleep(2) 
            
            # ==========================================
            # 💡 [새로운 로직] 3-dot 메뉴가 보일 때까지 '뒤로가기' 연타!
            # ==========================================
            print("🔙 메인 화면을 찾기 위해 상태를 점검합니다.")
            
            for i in range(5): 
                three_dot_btn = d(resourceId="com.EveryTalk.Global:id/phone_cmd_more")
                
                if three_dot_btn.exists:
                    print("✅ 메인 화면(ContactActivity) 도착 완료!")
                    break 
                else:
                    print(f"  - 다른 화면에 있습니다. 뒤로가기를 누릅니다. ({i+1}/5)")
                    d.press("back")
                    time.sleep(1) 
            else:
                print("⚠️ 메인 화면을 찾지 못했습니다. 앱이 꼬인 것 같으니 초기화면 진입을 확인해주세요.")
                return 
            
            # ==========================================
            # 💡 [우측 상단 3-dot 메뉴 클릭]
            # ==========================================
            print("👆 3-dot(더보기) 메뉴를 엽니다.")
            three_dot_btn = d(resourceId="com.EveryTalk.Global:id/phone_cmd_more") 
            
            if three_dot_btn.exists:
                three_dot_btn.click()
                time.sleep(1)
            else:
                print("⚠️ 3-dot 메뉴 버튼을 찾을 수 없습니다.")
                return

            # ==========================================
            # 💡 [드롭다운에서 '설정' 버튼 클릭]
            # ==========================================
            print("⚙️ '설정' 메뉴로 진입합니다.")
            setup_menu = d(className="android.widget.TextView", text="설정")

            if setup_menu.exists:
                setup_menu.click()
                time.sleep(1)
            else:
                print("⚠️ 3-dot 메뉴 안에서 '설정' 버튼을 찾을 수 없습니다.")
                return

            # ==========================================
            # 💡 [엔지니어 설정 진입 및 IP SEC OFF]
            # ==========================================
            engineer_menu = d(resourceId="com.EveryTalk.Global:id/list_item_name", textContains="엔지니어")
            
            if not engineer_menu.exists:
                print("🔒 엔지니어 설정 메뉴가 숨겨져 있습니다. 해제를 시도합니다.")
                version_btn = d(resourceId="com.EveryTalk.Global:id/opt_ver")
                for _ in range(5):
                    version_btn.click()
                    time.sleep(0.1)
                
                d(resourceId="com.EveryTalk.Global:id/pass_edit").set_text("1231")
                d(resourceId="com.EveryTalk.Global:id/sel_ok").click()
                time.sleep(1) 
            
            print("🛠️ 엔지니어 설정 메뉴로 진입합니다.")
            engineer_menu.click()
            time.sleep(1)

            print("🔍 IP SEC ENABLED 항목을 찾는 중...")
            d(scrollable=True).scroll.to(text="IP SEC ENABLED")
            time.sleep(0.5)
            
            ipsec_text = d(text="IP SEC ENABLED")
            ipsec_switch = ipsec_text.right(resourceId="android:id/switch_widget")
            
            if ipsec_switch.exists:
                is_checked = ipsec_switch.info.get("checked")
                
                if is_checked:
                    print("⚡ IP SEC ENABLED가 ON 상태입니다. OFF로 끕니다.")
                    ipsec_text.click() 
                    time.sleep(1.5) 
                    
                    d.click(100, 100) 
                    time.sleep(0.5)

                    save_btn = d(resourceId="com.EveryTalk.Global:id/btn_save")
                    if save_btn.exists:
                        save_btn.click()
                        print("💾 재난망 설정 저장 완료!")
                        time.sleep(2.0)
                        
                else:
                    print("✅ IP SEC ENABLED가 이미 OFF 상태입니다. 설정을 취소하고 나갑니다.")
                    
                    cancel_btn = d(textContains="취소")
                    if not cancel_btn.exists:
                        cancel_btn = d(textContains="Cancel") 
                    
                    if cancel_btn.exists:
                        cancel_btn.click()
                        print("🔙 취소 버튼 클릭 완료!")
                    else:
                        print("⚠️ 취소 버튼을 찾지 못해 '뒤로가기' 키를 대신 누릅니다.")
                        d.press("back")
                    
                    time.sleep(2.0) 
            else:
                print("⚠️ IP SEC ENABLED 스위치를 화면에서 찾을 수 없습니다.")

        except Exception as e:
            print(f"❌ LM75 환경 설정 중 치명적 오류 발생: {e}")
            raise e

    # ==========================================
    # 📞 호 발신용 함수
    # ==========================================
    def make_call(self, d, target_info, call_mode="PTT", log_console=None):
        """
        call_mode (PTT, PTV, E-PTT, E-PTV)에 따라 알맞은 Broadcast Intent를 전송합니다.
        E-PTT/E-PTV는 비상통화를 곧바로 거는 Intent가 없어서, 먼저 일반 PTT/PTV로 호를
        연결한 뒤 action.mcptt.req.groupcall.emergency를 보내 비상통화로 전환합니다.
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
            print_log(f"💻 ADB 실행: {cmd}") # 무슨 명령어를 치는지 확인용
            
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print_log(f"⚠️ ADB 실행 에러: {result.stderr}")

        is_video = call_mode in ("PTV", "E-PTV")
        is_emergency = call_mode in ("E-PTT", "E-PTV")

        print_log(f"\n[Call] 🚨 PS-LTE 백그라운드 발신 시작 (대상: {target_info} / 모드: {call_mode})")

        try:
            # ==========================================
            # 🟢 1. 통화 발신 (비상 모드도 우선 일반 PTT/PTV로 호를 겁니다)
            # ==========================================
            if is_video:
                print_log(f"📹 영상호(PTV) 발신 중...")
                run_adb(f"am broadcast -a action.mcptt.req.groupvideo.dial --es groupname {target_info}")
            else:
                print_log(f"📞 음성호(PTT) 발신 중...")
                run_adb(f"am broadcast -a action.mcptt.req.groupvoice.call --es groupname {target_info}")

            time.sleep(3.0)

            # ==========================================
            # 🚨 1-1. 비상 모드(E-PTT/E-PTV): 호 발신 시 자동 획득된 발언권을
            #        먼저 해제한 뒤에야 비상통화 전환이 정상적으로 걸립니다.
            # ==========================================
            if is_emergency:
                print_log(f"🔓 [{call_mode}] 호 발신 시 획득된 발언권을 해제합니다.")
                run_adb("am broadcast -a action.mcptt.req.groupcall.talkright.release")
                time.sleep(1.0)

                print_log(f"🚨 [{call_mode}] 비상통화로 전환합니다.")
                run_adb("am broadcast -a action.mcptt.req.groupcall.emergency")
                time.sleep(1.0)

            # ==========================================
            # 🎤 2. 발언권/전송권 제어
            # ==========================================
            print_log(f"🎤 [{call_mode}] 발언권(Talk Right)을 요청합니다.")
            run_adb("am broadcast -a action.mcptt.req.groupcall.talkright.acquire")

            print_log("🗣️ 발언권 획득! 12초간 PC 스피커로 음성을 재생하며 송출을 유지합니다...")
            try:
                winsound.PlaySound(VOICE_FILE, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                print_log(f"⚠️ 음성 파일 재생 실패 ({VOICE_FILE}): {e}")
            time.sleep(12.0)
            winsound.PlaySound(None, winsound.SND_PURGE)

            print_log(f"🔇 [{call_mode}] 발언권을 반납합니다.")
            run_adb("am broadcast -a action.mcptt.req.groupcall.talkright.release")
            time.sleep(1.0)

            # ==========================================
            # 🛑 3. 통화 종료
            # ==========================================
            if is_video:
                print_log("🛑 영상호(PTV) 통화를 종료합니다 (Release).")
                run_adb("am broadcast -a action.mcptt.req.groupvideo.release")
            else:
                print_log("🛑 음성호(PTT) 통화를 종료합니다 (Deactivate).")
                run_adb("am broadcast -a action.mcptt.req.groupvoice.deactivatechannel")
            
            print_log(f"✅ '{target_info}' ({call_mode}) 호 발신 시나리오 완료!")

        except Exception as e:
            print_log(f"❌ '{target_info}' 발신 중 오류 발생: {e}")

    # ==========================================
    # 💬 IM 메시지 발신용 함수 (UIAutomator2 기반)
    # ==========================================
    def send_message(self, d, target_info, message_text=None, log_console=None):
        """
        target_info(그룹명)로 IM 메시지를 전송합니다.

        1. SMS 목록(SmsMainActivity)에 해당 그룹과의 대화가 이미 있으면 바로 열어서 입력.
        2. 없으면 Contact 목록(ContactActivity)에서 그룹을 찾아(필요 시 스크롤)
           더보기(btn_more) -> SMS 보내기(group_sms_send)로 새 메시지 화면을 열어서 입력.

        message_text를 지정하지 않으면 TEST_MESSAGE_POOL에서 무작위로 하나 골라 사용합니다.
        """
        if message_text is None:
            message_text = random.choice(TEST_MESSAGE_POOL)

        def print_log(msg):
            print(msg)
            if log_console:
                log_console.insert("end", f"{msg}\n")
                log_console.see("end")

        def go_home():
            # 💡 [핵심] SmsMainActivity/ContactActivity는 not exported라서 am start -n으로
            # 외부에서 강제로 못 띄웁니다(SecurityException). 그래서 뒤로가기로 홈 화면까지
            # 되돌아간 뒤, 홈 화면의 메뉴 버튼을 실제로 클릭해서 이동해야 합니다.
            home_marker = d(resourceId="com.EveryTalk.Global:id/layout_main_menu_sms")
            for i in range(5):
                if home_marker.exists:
                    return True
                print_log(f"🔙 홈 화면을 찾기 위해 뒤로가기를 누릅니다. ({i + 1}/5)")
                d.press("back")
                time.sleep(1.0)
            return home_marker.exists

        print_log(f"\n[Message] 💬 '{target_info}' 그룹에 메시지 전송을 시도합니다.")

        try:
            # 1. 앱을 켜고 홈 화면으로 되돌아간 뒤, "메시지" 메뉴를 클릭해서 SMS 목록으로 이동
            d.app_start("com.EveryTalk.Global", stop=False)
            time.sleep(1.5)

            if not go_home():
                print_log("❌ 홈 화면을 찾지 못해 메시지 화면으로 진입할 수 없습니다.")
                return

            d(resourceId="com.EveryTalk.Global:id/layout_main_menu_sms").click()
            time.sleep(2.0)

            sms_name_item = d(
                resourceId="com.EveryTalk.Global:id/sms_name", text=target_info
            )

            if sms_name_item.exists:
                # 1-A. 이미 대화가 있는 경우: 바로 열어서 입력
                print_log(f"✅ 메시지 목록에서 '{target_info}' 대화를 찾았습니다. 바로 엽니다.")
                sms_name_item.click()
                time.sleep(1.0)

                msg_input = d(resourceId="com.EveryTalk.Global:id/sms_view_msginputbox")
                msg_input.click()
                msg_input.set_text(message_text)
                print_log(f"✏️ 메시지 입력 완료: '{message_text}'")

                send_btn = d(resourceId="com.EveryTalk.Global:id/sms_view_msgsendbutton")
                send_btn.click()
                print_log("📤 전송 버튼을 눌렀습니다.")

            else:
                # 1-B. 대화가 없는 경우: 채널 목록(ContactActivity)에서 그룹을 찾아 새 메시지 생성
                print_log(f"🔍 메시지 목록에 없어 채널 목록에서 '{target_info}'를 찾습니다.")

                if not go_home():
                    print_log("❌ 홈 화면을 찾지 못해 채널 목록으로 진입할 수 없습니다.")
                    return

                d(resourceId="com.EveryTalk.Global:id/layout_main_menu_private").click()
                time.sleep(2.0)

                if not d(text=target_info).exists:
                    print_log(f"📜 화면에 안 보여서 스크롤하며 '{target_info}'를 찾습니다.")
                    d(scrollable=True).scroll.to(text=target_info)
                    time.sleep(0.5)

                group_item = d(text=target_info)
                if not group_item.exists:
                    print_log(f"❌ '{target_info}' 그룹을 채널 목록에서 찾지 못했습니다.")
                    return

                more_btn = group_item.right(
                    resourceId="com.EveryTalk.Global:id/btn_more"
                )
                if not more_btn.exists:
                    print_log(f"❌ '{target_info}'의 더보기(btn_more) 버튼을 찾지 못했습니다.")
                    return

                more_btn.click()
                time.sleep(0.5)

                send_sms_btn = d(resourceId="com.EveryTalk.Global:id/group_sms_send")
                if not send_sms_btn.exists:
                    print_log("❌ group_sms_send 버튼을 찾지 못했습니다.")
                    return

                send_sms_btn.click()
                time.sleep(1.0)

                new_msg_input = d(resourceId="com.EveryTalk.Global:id/sms_new_message")
                new_msg_input.click()
                new_msg_input.set_text(message_text)
                print_log(f"✏️ 새 메시지 입력 완료: '{message_text}'")

                new_send_btn = d(resourceId="com.EveryTalk.Global:id/sms_new_send_btn")
                new_send_btn.click()
                print_log("📤 전송 버튼을 눌렀습니다.")

            print_log(f"✅ '{target_info}' 메시지 전송 시나리오 완료!")

        except Exception as e:
            print_log(f"❌ '{target_info}' 메시지 전송 중 오류 발생: {e}")