import uiautomator2 as u2

# uuid는 기존에 쓰시던 거 그대로 넣으세요
d = u2.connect("bad0f1") 

# 폰 화면 정보를 텍스트 파일로 저장
with open("ui_dump.xml", "w", encoding="utf-8") as f:
    f.write(d.dump_hierarchy())

print("✅ 화면 정보 추출 완료! ui_dump.xml을 열어보세요.")