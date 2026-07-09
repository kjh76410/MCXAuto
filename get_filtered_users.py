import pymysql
import csv  # 👈 파일 저장을 위해 추가!

print("🌐 서버 DB에 다이렉트로 접속합니다...")

try:
    conn = pymysql.connect(
        host='211.118.224.205',
        user='cybertel',
        password='Cybertel1234567890!',
        db='mcptt_server',
        charset='utf8mb4'
    )
    
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    query = "SELECT display_name, name FROM user_profile;"
    cursor.execute(query)
    users = cursor.fetchall()
    
    print(f"✅ DB에서 {len(users)}명의 데이터를 성공적으로 가져왔습니다!")
    print("엑셀 파일로 저장을 시작합니다...")

    # 🎯 여기서부터 파일 생성 코드입니다!
    # 'utf-8-sig'는 한글이 엑셀에서 안 깨지게 해주는 마법의 설정입니다.
    with open('user_list.csv', 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Display Name'])  # 엑셀 첫 줄(헤더) 작성
        
        # 유저 데이터를 한 줄씩 엑셀에 쓰기
        for user in users:
            writer.writerow([user.get('name'), user.get('display_name')])

    print("=========================================")
    print("🎉 성공! 파이썬 스크립트가 있는 폴더에 'user_list.csv' 파일이 생성되었습니다!")
    print("=========================================\n")

except pymysql.Error as e:
    print(f"❌ DB 접속 또는 쿼리 실행 중 에러 발생: {e}")

finally:
    if 'conn' in locals() and conn.open:
        conn.close()