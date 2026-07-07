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
        """버전 이름(예: PTA.R-3.1.3...)에서 첫 번째 점(.) 앞의 텍스트만 추출합니다."""
        
        # 앱이 설치되어 있지 않거나 에러가 났을 때의 방어 코드
        if not version_name or version_name in ["설치 안 됨", "버전 확인 불가", "알 수 없음"]:
            return "대기 중"
            
        try:
            # 1. '-' 기호를 기준으로 앞부분(PTA.R)만 가져옴
            prefix = version_name.split('-')[0]
            
            # 2. '.' 기호를 기준으로 앞부분(PTA)만 최종적으로 가져옴
            project_name = prefix.split('.')[0]
            
            return project_name
            
        except Exception as e:
            print(f"프로젝트명 추출 오류: {e}")
            return "분석 오류"

    @staticmethod
    def parse_group_list(file_path):
        """네임스페이스를 제거하고 MCPTTGroupInfo 하위의 entry 태그에서 그룹 목록을 추출합니다."""
        group_data = []
        if not file_path or not os.path.exists(file_path):
            return group_data

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_string = f.read()
            
            # xmlns=... 로 시작하는 부분을 강제 제거 (네임스페이스 에러 방지)
            xml_string = re.sub(r' xmlns=".*?"', '', xml_string)
            root = ET.fromstring(xml_string)
            
            # 💡 수정된 부분: <MCPTTGroupInfo> 안쪽에 있는 <entry> 태그들을 찾습니다.
            for entry in root.findall('.//MCPTTGroupInfo/entry'):
                # 1. display-name 추출
                name_tag = entry.find('display-name')
                name = name_tag.text if name_tag is not None else "Unknown"
                
                # 2. uri-entry에서 Call ID 추출 (예: sip:06180098723@... -> 06180098723)
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