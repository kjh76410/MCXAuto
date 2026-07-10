import time
import subprocess # 💡 [핵심] 이거 없으면 ADB 명령어를 아예 못 날립니다!

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
            print_log(f"💻 ADB 실행: {cmd}") # 무슨 명령어를 치는지 확인용
            
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print_log(f"⚠️ ADB 실행 에러: {result.stderr}")

        print_log(f"\n[Call] 🚨 PS-LTE 백그라운드 발신 시작 (대상: {target_info} / 모드: {call_mode})")
        
        try:
            # ==========================================
            # 🟢 1. 통화 발신 (모드에 따라 명령어 다름)
            # ==========================================
            if call_mode == "PTV":
                print_log(f"📹 영상호(PTV) 발신 중...")
                run_adb(f"am broadcast -a action.mcptt.req.groupvideo.dial --es groupname {target_info}")
            else:
                print_log(f"📞 음성호(PTT) 발신 중...")
                run_adb(f"am broadcast -a action.mcptt.req.groupvoice.call --es groupname {target_info}")
            
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