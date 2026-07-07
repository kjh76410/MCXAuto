import subprocess
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
    def parse_group_list(file_path):
        """네임스페이스를 제거하고 안전하게 파싱합니다."""
        group_data = []
        if not file_path or not os.path.exists(file_path):
            return group_data

        try:
            # 1. 파일 내용을 읽어서 xmlns 부분을 강제로 제거하는 트릭 (네임스페이스 에러 방지)
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_string = f.read()
            
            # xmlns=... 로 시작하는 부분을 제거
            xml_string = re.sub(r' xmlns=".*?"', '', xml_string)
            root = ET.fromstring(xml_string)
            
            # 2. 파싱 시도
            # 이제 네임스페이스가 없으므로 일반적인 태그 검색이 가능합니다.
            for entry in root.findall('.//entry'):
                name_tag = entry.find('display-name')
                name = name_tag.text if name_tag is not None else "Unknown"
                
                uri_tag = entry.find('uri-entry')
                call_id = "Unknown"
                if uri_tag is not None and uri_tag.text:
                    match = re.search(r'sip:(\d+)@', uri_tag.text)
                    if match:
                        call_id = match.group(1)
                
                group_data.append(f"{name} ({call_id})")
                
            print(f"[FileManager] ✅ 파싱 완료: {len(group_data)}개의 그룹 발견")
                    
        except Exception as e:
            print(f"[FileManager] ⚠️ XML 파싱 에러: {e}")
            
        return group_data

    def parse_my_call_id(file_path):
        """XML에서 <identity> 태그 내의 Call ID를 추출합니다."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_string = re.sub(r' xmlns=".*?"', '', f.read())
            root = ET.fromstring(xml_string)
            
            # <identity> 밑의 <one> 태그를 찾음
            identity_tag = root.find('.//identity/one')
            if identity_tag is not None:
                uri = identity_tag.get('id') # id 속성 가져오기
                match = re.search(r'sip:(\d+)@', uri)
                if match:
                    return match.group(1)
            return "ID 없음"
        except Exception as e:
            print(f"[FileManager] ⚠️ My ID 파싱 에러: {e}")
            return "파싱 실패"