import subprocess
import json
import os
import xml.etree.ElementTree as ET
import re

class FileManager:
    @staticmethod
    def pull_profile_xml(uuid, local_path="temp_profile.xml"):
        """단말기에서 XML 파일을 PC로 가져옵니다."""
        try:
            # check=True를 추가해서 adb 명령이 실패하면 즉시 알 수 있게 합니다.
            cmd = f"adb -s {uuid} pull /sdcard/mcptt/xml/user_profile.xml {local_path}"
            subprocess.run(cmd, shell=True, check=True)
            print(f"[FileManager] ✅ 파일 가져오기 성공: {local_path}")
            return local_path
        except subprocess.CalledProcessError:
            print(f"[FileManager] ❌ ADB pull 실패 (파일이 없거나 권한 문제)")
            return None

    @staticmethod
    def get_project_name(version_name):
        """
        버전 이름에서 json 설정 파일의 키워드를 매칭하여 프로젝트 이름을 반환합니다.
        예: 'CTB.R-3.1.3...' -> 'CTB POC'
        """
        import json
        import os

        # 1. 앱이 설치되어 있지 않거나 에러가 났을 때의 방어 코드
        if not version_name or version_name in ["설치 안 됨", "버전 확인 불가", "알 수 없음"]:
            return "대기 중"
            
        try:
            # 2. json 파일 경로 설정 (main.py나 프로젝트 루트 폴더 기준)
            config_path = os.path.join(os.getcwd(), "project_config.json")
            
            # 기본값 설정 (만약 파일이 없거나 매칭이 안 될 때를 대비)
            default_name = "알 수 없는 프로젝트"
            
            if os.path.exists(config_path):
                # 3. JSON 파일 읽기
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                
                projects = config_data.get("projects", [])
                default_name = config_data.get("default", default_name)
                
                # 4. 버전명에 keyword가 포함되어 있는지 매칭 검사
                # (대소문자 구분을 없애기 위해 둘 다 소문자로 변환해서 비교하면 더 안전합니다)
                for proj in projects:
                    keyword = proj.get("keyword", "")
                    if keyword and (keyword.lower() in version_name.lower()):
                        return proj.get("project_name", default_name)
            else:
                print(f"⚠️ 경고: {config_path} 파일을 찾을 수 없습니다.")

            # 5. 매칭되는 키워드가 없으면 JSON에 정의된 default 값 반환
            return default_name
            
        except Exception as e:
            print(f"프로젝트명 추출 오류: {e}")
            return "분석 오류"

    @staticmethod
    def parse_group_list(file_path):
        """XML에서 그룹 이름, ID, 그리고 타입을 추출합니다."""
        group_data = [] # {name, id, type} 형태의 딕셔너리를 담을 리스트
        
        if not file_path or not os.path.exists(file_path):
            return group_data

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_string = f.read()
            
            xml_string = re.sub(r' xmlns=".*?"', '', xml_string)
            root = ET.fromstring(xml_string)
            
            for entry in root.findall('.//MCPTTGroupInfo/entry'):
                # 1. 이름 및 ID 추출
                name_tag = entry.find('display-name')
                name = name_tag.text if name_tag is not None else "Unknown"
                
                uri_tag = entry.find('uri-entry')
                call_id = "Unknown"
                if uri_tag is not None and uri_tag.text:
                    match = re.search(r'sip:([^@]+)@', uri_tag.text)
                    if match: call_id = match.group(1)

                # 2. 타입 분류 (Priority 값 활용)
                priority_tag = entry.find('.//anyExt/group-priority')
                priority = priority_tag.text if priority_tag is not None else "0"
                
                # Priority 31이면 Chat Group, 10이면 PreArranged Group으로 분류
                group_type = "Chat Group" if priority == "31" else "PreArranged Group"
                
                group_data.append({
                    "name": name,
                    "id": call_id,
                    "type": group_type
                })
                
        except Exception as e:
            print(f"[FileManager] ⚠️ XML 파싱 에러: {e}")
            
        return group_data

    @staticmethod # 💡 에러 방지를 위해 추가했습니다.
    def parse_my_info(file_path):
        """XML에서 <MCPTTUserID> 태그 내의 이름과 Call ID를 추출합니다."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_string = re.sub(r' xmlns=".*?"', '', f.read())
            root = ET.fromstring(xml_string)
            
            # <MCPTTUserID> 태그를 찾음
            user_id_tag = root.find('.//MCPTTUserID')
            if user_id_tag is not None:
                # 1. 내 이름 추출
                name_tag = user_id_tag.find('display-name')
                name = name_tag.text if name_tag is not None else "이름 없음"
                
                # 2. 내 Call ID 추출
                uri_tag = user_id_tag.find('uri-entry')
                call_id = "번호 없음"
                if uri_tag is not None and uri_tag.text:
                    match = re.search(r'sip:(\d+)@', uri_tag.text)
                    if match:
                        call_id = match.group(1)
                        
                return f"{name} ({call_id})"
                
            return "내 정보 없음"
        except Exception as e:
            print(f"[FileManager] ⚠️ 내 정보 파싱 에러: {e}")
            return "파싱 실패"