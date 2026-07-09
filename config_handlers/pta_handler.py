import time
import os

class PTAHandler:
    def run(self, d, env): # 여기서 d를 받아옵니다.
        print("🚀 PTA 자동화 시작!")
        
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
                d.press("back")
                time.sleep(0.5)
                d(text="OK").click()
                print("✅ PTA 자동화 100% 완료!")
            else:
                print("❌ 서버 설정 팝업을 찾을 수 없습니다!")

        except Exception as e:
            print(f"❌ 자동화 실패: {e}")


    def check_db(self, d):
        # 1. DB 경로 확인 (패키지명에 맞는 경로로 수정 필수)
        remote_path = "/data/data/com.EveryTalk.Global/databases/user.db"
        local_path = "extracted_user.db"
        
        print("📂 DB 파일 가져오는 중...")
        try:
            # DB 파일을 현재 PC 폴더로 복사
            d.pull(remote_path, local_path)
            print(f"✅ 성공! {local_path} 파일이 생성되었습니다.")
        except Exception as e:
            print(f"❌ 실패: 루팅 권한 문제거나 파일 경로가 틀렸을 수 있습니다. ({e})")