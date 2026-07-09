import pymysql
import json
import re
import os

def load_config():
    """같은 폴더의 project_config.json 파일을 읽어오는 함수"""
    config_file = 'project_config.json'
    if not os.path.exists(config_file):
        print(f"❌ 에러: {config_file} 파일이 존재하지 않습니다!")
        return None
        
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    # 1. JSON 설정 파일 로드
    config_data = load_config()
    if not config_data:
        return

    projects = config_data.get("projects", [])
    
    print("=========================================")
    print("      Dynamic Project DB Extractor       ")
    print("=========================================")
    
    # JSON 파일에 적힌 프로젝트 목록을 보고 자동으로 메뉴 생성!
    for i, proj in enumerate(projects):
        print(f"{i + 1}. {proj['project_name']} (키워드: {proj['keyword']})")
    print("=========================================")
    
    try:
        choice = int(input(f"👉 실행할 프로젝트 번호를 입력하세요 (1~{len(projects)}): ").strip())
        selected_project = projects[choice - 1]
    except (ValueError, IndexError):
        print("❌ 잘못된 번호를 선택하셨습니다. 프로그램을 종료합니다.")
        return

    # 선택된 프로젝트의 정보와 DB 설정 추출
    p_name = selected_project["project_name"]
    db_info = selected_project["db_config"]

    # 플레이스홀더 방어막 코드
    if "여기에" in db_info["host"]:
        print(f"❌ 에러: {p_name} 프로젝트의 실제 DB 접속 정보가 JSON 파일에 입력되지 않았습니다!")
        return

    print(f"\n🌐 [{p_name}] 서버 DB에 동적 접속을 시도합니다...")

    try:
        # 2. JSON에서 끌고 온 정보로 다이렉트 DB 연결!
        conn = pymysql.connect(
            host=db_info["host"],
            user=db_info["user"],
            password=db_info["password"],
            db=db_info["db"],
            charset='utf8mb4'
        )
        
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 유저 ID(sip URI)와 기본 이름 정보 긁어오기
        query = "SELECT name, display_name, user_id FROM user_profile;"
        cursor.execute(query)
        users = cursor.fetchall()
        
        print(f"✅ DB 연결 성공! 총 {len(users)}명의 원본 데이터를 가져왔습니다.")
        print(f"🔄 [{p_name}] 계정 그룹별(앞 3자리) 파일 분리를 시작합니다...")

        project_groups = {}

        for user in users:
            id_value = str(user.get('user_id', ''))
            
            # 'sip:006...' 형태에서 앞 3자리 숫자 추출 (예: 006)
            match = re.search(r'sip:(\d{3})', id_value)
            group_code = match.group(1) if match else "unknown"
                
            if group_code not in project_groups:
                project_groups[group_code] = []
                
            project_groups[group_code].append({
                "name": user.get('name'),
                "display_name": user.get('display_name'),
                "id": id_value
            })

        print(f"\n💾 결과 파일 생성 중...")
        print("=========================================")

        # 파일명에 공백이 있으면 안 좋으니 언더바로 변환 (예: CTB POC -> CTB_POC)
        safe_p_name = p_name.replace(" ", "_")

        for group_code, sorted_users in project_groups.items():
            # 최종 파일명 예시: PTA_group_006.json / CTB_POC_group_006.json
            file_name = f"{safe_p_name}_group_{group_code}.json"
            
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(sorted_users, f, ensure_ascii=False, indent=4)
                
            print(f"📦 {file_name} 저장 완료! (인원: {len(sorted_users)}명)")

        print("=========================================")
        print(f"🎉 [{p_name}] 모든 데이터 분류가 완벽하게 끝났습니다!")

    except pymysql.Error as e:
        print(f"❌ DB 에러 발생: {e}")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()
            print("\n🔒 DB 연결을 안전하게 종료했습니다.")

if __name__ == "__main__":
    main()