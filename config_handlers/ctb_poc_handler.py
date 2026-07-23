import time
import random

# IM 메시지 발신 시 무작위로 골라 쓰는 테스트 문구
TEST_MESSAGE_POOL = [
    "테스트 중입니다.",
    "테스트 메시지입니다.",
    "메시지 전송,",
    "123 테스트",
    "테스트 중입니다.",
    "메시지입니다.",
    "가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하가나다라마바사아자차카타파하ab",
    r"""[TEST MESSAGE - 종합 문자열 테스트]
    1. 기본 문자 테스트: ABC abc 123 가나다라마바사
    2. 특수문자 테스트: @#$%^&*()_+-=[]{};:'",.<>/?\|`
    3. 줄바꿈 및 탭 테스트:
        - 첫 번째 줄
        - 두 번째 줄
        - 세 번째 줄

[JSON 형식 테스트]
    {
        "id": 1001,
        "name": "홍길동",
        "email": "test@example.com",
        "active": true
    }

[시간 및 날짜 테스트]
    현재 시각: 2025-10-23 11:30:45
    타임스탬프: 1734955845

[언어 혼합 테스트]
    Korean: 안녕하세요
    English: Hello
    日本語: テストです
    中文: 测试中

[파일 경로 / URL 테스트]
    C:\Users\Tester\Documents\test.txt
    https://example.com/api/v1/data?user=test&id=123

[결과 요약]
    Status: SUCCESS ✅
    ErrorCode: 0
    Duration: 1523ms""",
]


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

    # ==========================================
    # 📞 호 발신용 함수 (UI 자동화 기반)
    # ==========================================
    def make_call(self, d, target_info, call_mode="PTT", log_console=None):
        """
        target_info(그룹명)로 PTT/PTV 호를 발신하고 12초간 발언한 뒤 해제합니다.

        0. 항상 메인 화면(com.cybertel.mcptt.ui.main.EveryTalkMain)에서 시작합니다.
           다른 화면에 있으면 뒤로가기를 눌러 메인 화면까지 되돌아갑니다.
        1. 메인 화면(enter_ch_name)이 이미 target_info 채널이면 채널 전환 없이 바로 발언.
        2. 아니면 main_menu_private -> ContactActivity에서 target_info 그룹을 찾습니다
           (필요 시 아래에서 위로 스와이프). group_session_divider_text 기준으로:
           - Active 밑에 있으면 이미 연결된 채널이므로, 메인 화면으로 돌아가 좌->우로
             스와이프한 뒤 name_layout을 눌러 채널만 선택합니다 (새로 호 연결 안 함).
           - NonActive 밑에 있으면 btn_more -> group_call_send/group_video_send로
             새로 호를 연결합니다.
        3. enter_ch_name이 target_info와 일치하는지 확인합니다. 실패하면 1회 재시도하고,
           그래도 실패하면 PTT를 누르지 않고 중단합니다. 성공하면 main_menu_ptt_key로
           12초간 발언하고 해제합니다.
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

        def try_connect():
            """target_info 채널로 전환을 한 번 시도하고, enter_ch_name으로 연결 성공 여부(bool)를 반환합니다."""
            current_ch = d(resourceId="com.EveryTalk.Global:id/enter_ch_name")

            if current_ch.exists and current_ch.get_text() == target_info:
                print_log(f"✅ 이미 '{target_info}' 채널에 있습니다. 채널 전환 없이 발언합니다.")
                return True

            print_log(f"🔀 현재 채널이 다릅니다. '{target_info}' 그룹으로 전환합니다.")

            private_btn = d(resourceId="com.EveryTalk.Global:id/main_menu_private")
            if not private_btn.wait(timeout=5.0):
                print_log("❌ main_menu_private 버튼을 찾을 수 없습니다.")
                return False
            private_btn.click()
            time.sleep(1.5)

            group_item = d(
                resourceId="com.EveryTalk.Global:id/group_name", text=target_info
            )
            if not group_item.exists:
                print_log(
                    f"📜 화면에 안 보여서 아래에서 위로 스와이프하며 '{target_info}'를 찾습니다."
                )
                w, h = d.window_size()
                for _ in range(5):
                    if group_item.exists:
                        break
                    d.swipe(w * 0.5, h * 0.8, w * 0.5, h * 0.2, duration=0.3)
                    time.sleep(0.5)

            if not group_item.exists:
                print_log(f"❌ '{target_info}' 그룹을 목록에서 찾지 못했습니다.")
                return False

            # group_session_divider_text가 Active/NonActive로 목록을 구분합니다.
            # Active 목록은 항상 최상단에 표시되므로, 위쪽에 구분선이 없다면(None)
            # 스크롤해서 내려온 NonActive 구간이라는 뜻입니다.
            divider = group_item.up(
                resourceId="com.EveryTalk.Global:id/group_session_divider_text"
            )
            if divider is not None and divider.exists:
                session_type = divider.get_text()
            else:
                session_type = "NonActive"
            print_log(f"ℹ️ '{target_info}' 세션 상태: {session_type}")

            if session_type == "Active":
                print_log("✅ 이미 연결된(Active) 채널입니다. 메인 화면에서 채널만 선택합니다.")
                if not go_home():
                    print_log("❌ 메인 화면(EveryTalkMain)을 찾지 못했습니다.")
                    return False

                w, h = d.window_size()
                d.swipe(w * 0.2, h * 0.5, w * 0.8, h * 0.5, duration=0.3)
                time.sleep(0.5)

                name_layout = d(resourceId="com.EveryTalk.Global:id/name_layout")
                if not name_layout.wait(timeout=5.0):
                    print_log("❌ name_layout을 찾을 수 없습니다.")
                    return False
                name_layout.click()
                time.sleep(1.0)
            else:
                more_btn = group_item.right(resourceId="com.EveryTalk.Global:id/btn_more")
                if not more_btn.exists:
                    print_log(f"❌ '{target_info}'의 더보기(btn_more) 버튼을 찾지 못했습니다.")
                    return False
                more_btn.click()
                time.sleep(0.5)

                if call_mode == "PTV":
                    send_btn = d(resourceId="com.EveryTalk.Global:id/group_video_send")
                else:
                    send_btn = d(resourceId="com.EveryTalk.Global:id/group_call_send")

                if not send_btn.exists:
                    print_log(f"❌ {call_mode} 발신 버튼을 찾지 못했습니다.")
                    return False
                send_btn.click()
                print_log(f"📞 '{target_info}' ({call_mode}) 호 연결을 시도합니다.")
                time.sleep(2.0)

            # 💡 [핵심] 잘못 눌려서 연결이 안 됐는데 PTT부터 누르는 사고를 막기 위해,
            # 메인 화면 채널명(enter_ch_name)이 실제로 target_info와 같은지 확인합니다.
            final_ch = d(resourceId="com.EveryTalk.Global:id/enter_ch_name")
            if final_ch.wait(timeout=5.0) and final_ch.get_text() == target_info:
                return True

            actual = final_ch.get_text() if final_ch.exists else "(화면에 없음)"
            print_log(f"⚠️ '{target_info}' 채널 연결을 확인하지 못했습니다 (현재 채널: '{actual}').")
            return False

        print_log(f"\n[Call] 📞 '{target_info}' ({call_mode}) 발신을 시작합니다.")

        try:
            d.app_start("com.EveryTalk.Global", stop=False)
            time.sleep(1.5)

            if not go_home():
                print_log("❌ 메인 화면(EveryTalkMain)을 찾지 못해 발신을 진행할 수 없습니다.")
                return

            # 채널 전환 확인 실패 시 1회 재시도합니다 (최초 시도 + 재시도 1회 = 총 2회).
            connected = False
            for attempt in range(1, 3):
                if attempt > 1:
                    print_log(f"🔁 '{target_info}' 채널 연결 재시도 중... ({attempt}/2)")
                    if not go_home():
                        print_log("❌ 메인 화면(EveryTalkMain)을 찾지 못해 재시도할 수 없습니다.")
                        return
                connected = try_connect()
                if connected:
                    break

            if not connected:
                print_log(
                    f"❌ '{target_info}' 채널 연결에 실패했습니다 (재시도 포함 총 2회). PTT를 누르지 않고 중단합니다."
                )
                return

            print_log(f"✅ '{target_info}' 채널 연결을 확인했습니다.")

            ptt_key = d(resourceId="com.EveryTalk.Global:id/main_menu_ptt_key")
            if not ptt_key.wait(timeout=5.0):
                print_log("❌ main_menu_ptt_key 버튼을 찾을 수 없습니다.")
                return

            print_log("🎤 발언권을 요청합니다 (PTT 키 누름).")
            ptt_key.click()

            print_log("🗣️ 12초간 발언을 유지합니다...")
            time.sleep(12.0)

            print_log("🔇 발언권을 반납합니다 (PTT 키 다시 누름).")
            ptt_key.click()

            print_log(f"✅ '{target_info}' ({call_mode}) 호 발신 시나리오 완료!")

        except Exception as e:
            print_log(f"❌ '{target_info}' 발신 중 오류 발생: {e}")

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

    # ==========================================
    # 💬 IM 메시지 발신용 함수 (UIAutomator2 기반)
    # ==========================================
    def send_message(self, d, target_info, message_text=None, repeat=1, log_console=None):
        """
        target_info(그룹명)로 IM 메시지를 전송합니다.

        1. 대화방 목록(ConversationRoomActivity)의 conversation_name과 그룹명이
           일치하는 대화가 이미 있으면 바로 열기.
        2. 없으면 Contact 목록(ContactActivity)에서 그룹을 찾아(필요 시 스크롤)
           더보기(btn_more) -> SMS 보내기(group_sms_send)로 새 대화를 엽니다.
        3. 어느 경로든 결국 도착하는 ConversationRoomActivity 화면(입력창
           conversation_view_msginputbox / 전송버튼 conversation_view_msgsendbutton)에서
           입력 -> 전송을 repeat 횟수만큼 반복합니다.

        message_text를 지정하지 않으면 매번 TEST_MESSAGE_POOL에서 무작위로 골라 사용합니다.
        """
        repeat = max(1, repeat)

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

        print_log(f"\n[Message] 💬 '{target_info}' 그룹에 메시지 전송을 시도합니다. (총 {repeat}회)")

        try:
            # 1. 앱을 켜고 홈 화면으로 되돌아간 뒤, "메시지" 메뉴를 클릭해서 SMS 목록으로 이동
            d.app_start("com.EveryTalk.Global", stop=False)
            time.sleep(1.5)

            if not go_home():
                print_log("❌ 홈 화면을 찾지 못해 메시지 화면으로 진입할 수 없습니다.")
                return

            d(resourceId="com.EveryTalk.Global:id/layout_main_menu_sms").click()
            time.sleep(2.0)

            # ConversationRoomActivity(대화방 목록) 화면의 각 항목 이름은 conversation_name입니다.
            conversation_item = d(
                resourceId="com.EveryTalk.Global:id/conversation_name", text=target_info
            )

            if conversation_item.exists:
                # 1-A. 이미 대화가 있는 경우: 바로 열기 (ConversationRoomActivity)
                print_log(f"✅ 메시지 목록에서 '{target_info}' 대화를 찾았습니다. 바로 엽니다.")
                conversation_item.click()
                time.sleep(1.0)
            else:
                # 1-B. 대화가 없는 경우: 채널 목록(ContactActivity)에서 그룹을 찾아 새 대화 생성
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
                # group_sms_send 클릭 후에도 결국 같은 ConversationRoomActivity 화면으로
                # 진입하므로, 신규/기존 대화 구분 없이 아래에서 동일한 입력창/전송버튼을 씁니다.

            # 2. ConversationRoomActivity 화면: 메시지란 선택 -> 입력 -> 전송을 repeat 횟수만큼 반복
            msg_input = d(resourceId="com.EveryTalk.Global:id/conversation_view_msginputbox")
            if not msg_input.wait(timeout=5.0):
                print_log(
                    "❌ 대화창 메시지 입력창(conversation_view_msginputbox)을 찾을 수 없습니다."
                )
                return
            send_btn = d(
                resourceId="com.EveryTalk.Global:id/conversation_view_msgsendbutton"
            )

            sent_count = 0
            for _ in range(repeat):
                base_text = message_text or random.choice(TEST_MESSAGE_POOL)
                text = f"{base_text} ({sent_count + 1}/{repeat})"
                msg_input.click()
                msg_input.set_text(text)
                send_btn.click()
                sent_count += 1
                print_log(f"📤 [{sent_count}/{repeat}] 전송: '{text}'")
                time.sleep(1.0)

            print_log(f"✅ '{target_info}' 메시지 전송 시나리오 완료! (총 {sent_count}회)")

        except Exception as e:
            print_log(f"❌ '{target_info}' 메시지 전송 중 오류 발생: {e}")
