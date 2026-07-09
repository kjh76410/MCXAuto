import subprocess
import json
import os
import xml.etree.ElementTree as ET
import re


class FileManager:

    @staticmethod
    def get_project_features(project_name):
        """프로젝트 이름을 받아 JSON에서 features 딕셔너리를 반환합니다."""
        try:
            config_path = os.path.join(os.getcwd(), "project_config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

                # 프로젝트 목록을 돌면서 일치하는 프로젝트의 features 반환
                for proj in config_data.get("projects", []):
                    if proj.get("project_name") == project_name:
                        return proj.get("features", {})
        except Exception as e:
            print(f"[FileManager] ⚠️ 기능 설정 로드 에러: {e}")

        return {}  # 실패하거나 없으면 빈 딕셔너리 반환

    @staticmethod
    def pull_profile_xml(uuid, local_folder="temp_xml"):
        """단말기에서 XML 폴더 전체를 PC로 가져온 뒤, 메인 프로필 파일 경로를 반환합니다."""
        import os
        import subprocess
        import shutil  # ✨ [추가] 폴더 통째로 삭제하기 위한 모듈

        try:
            # 1. ✨ [핵심 수정] 기존 폴더가 있으면 안에 있는 파일까지 싹 다 날려버립니다!
            if os.path.exists(local_folder):
                shutil.rmtree(local_folder)

            # 그리고 완전히 깨끗한 새 폴더를 생성합니다.
            os.makedirs(local_folder)

            # 2. 단말기의 xml 폴더 안의 모든 파일(.)을 깨끗한 로컬 폴더로 가져옵니다.
            cmd = f"adb -s {uuid} pull /sdcard/mcptt/xml/. {local_folder}"
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
            print(
                f"[FileManager] ✅ 기존 데이터 초기화 및 폴더 전체 가져오기 성공: {local_folder}"
            )

            # 3. 메인 user_profile.xml의 경로 반환
            main_xml_path = os.path.join(local_folder, "user_profile.xml")

            if os.path.exists(main_xml_path):
                return main_xml_path
            else:
                print(
                    "[FileManager] ⚠️ 폴더는 가져왔지만 user_profile.xml 이 없습니다."
                )
                return None

        except subprocess.CalledProcessError:
            print(f"[FileManager] ❌ ADB pull 실패 (단말기에 폴더가 없거나 권한 문제)")
            return None
        except Exception as e:
            print(f"[FileManager] ❌ 파일 초기화 중 에러 발생: {e}")
            return None

    @staticmethod
    def get_project_name(version_name):
        """버전 이름에서 json 설정 파일의 키워드를 매칭하여 프로젝트 이름을 반환합니다."""
        if not version_name or version_name in [
            "설치 안 됨",
            "버전 확인 불가",
            "알 수 없음",
        ]:
            return "대기 중"

        try:
            config_path = os.path.join(os.getcwd(), "project_config.json")
            default_name = "알 수 없는 프로젝트"

            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)

                projects = config_data.get("projects", [])
                default_name = config_data.get("default", default_name)

                for proj in projects:
                    keyword = proj.get("keyword", "")
                    if keyword and (keyword.lower() in version_name.lower()):
                        return proj.get("project_name", default_name)
            else:
                print(f"⚠️ 경고: {config_path} 파일을 찾을 수 없습니다.")

            return default_name
        except Exception as e:
            print(f"프로젝트명 추출 오류: {e}")
            return "분석 오류"

    @staticmethod
    def parse_my_info(file_path):
        """XML에서 <MCPTTUserID> 태그 내의 이름과 Call ID를 추출합니다."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                xml_string = re.sub(r' xmlns=".*?"', "", f.read())
            root = ET.fromstring(xml_string)

            user_id_tag = root.find(".//MCPTTUserID")
            if user_id_tag is not None:
                name_tag = user_id_tag.find("display-name")
                name = name_tag.text if name_tag is not None else "이름 없음"

                uri_tag = user_id_tag.find("uri-entry")
                call_id = "번호 없음"
                if uri_tag is not None and uri_tag.text:
                    match = re.search(r"sip:(\d+)@", uri_tag.text)
                    if match:
                        call_id = match.group(1)
                return f"{name} ({call_id})"

            return "내 정보 없음"
        except Exception as e:
            print(f"[FileManager] ⚠️ 내 정보 파싱 에러: {e}")
            return "파싱 실패"

    # --- 💡 여기서부터 중복을 제거하고 코덱 로직을 합친 완성본입니다 ---

    @staticmethod
    def parse_group_list(file_path):
        """XML에서 그룹 이름, ID, 타입 및 코덱 정보를 추출합니다."""
        group_data = []

        if not file_path or not os.path.exists(file_path):
            return group_data

        xml_folder_path = os.path.dirname(os.path.abspath(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                xml_string = f.read()

            xml_string = re.sub(r' xmlns=".*?"', "", xml_string)
            root = ET.fromstring(xml_string)

            # --- [일반 그룹 반복문 시작] ---
            for entry in root.findall(".//MCPTTGroupInfo/entry"):
                name_tag = entry.find("display-name")
                name = name_tag.text if name_tag is not None else "Unknown"

                uri_tag = entry.find("uri-entry")
                call_id = "Unknown"
                if uri_tag is not None and uri_tag.text:
                    match = re.search(r"sip:([^@]+)@", uri_tag.text)
                    if match:
                        call_id = match.group(1)

                priority_tag = entry.find(".//anyExt/group-priority")
                priority = priority_tag.text if priority_tag is not None else "0"
                group_type = "Chat Group" if priority == "31" else "PreArranged Group"

                voice, video = FileManager.get_group_codecs(xml_folder_path, call_id)

                group_data.append(
                    {
                        "name": name,
                        "id": call_id,
                        "type": group_type,
                        "voice_codec": voice,
                        "video_codec": video,
                    }
                )
            # --- [일반 그룹 반복문 끝] ---

        except Exception as e:
            print(f"[FileManager] ⚠️ XML 파싱 에러: {e}")

        # ==========================================
        # 💡 [핵심] 반복문을 완전히 빠져나온 후, 딱 한 번만 ReGroup을 찾습니다!
        # ==========================================
        regroups = FileManager.get_regroup_list(xml_folder_path)

        # 중복 방지: 이미 있는 그룹 ID면 빼고 넣기
        existing_ids = {g["id"] for g in group_data}
        for rg in regroups:
            if rg["id"] not in existing_ids:
                group_data.append(rg)
                existing_ids.add(rg["id"])

        return group_data

    @staticmethod
    def get_group_codecs(xml_folder_path, group_id):
        """특정 그룹 ID를 포함하는 XML 파일을 찾아 음성/영상 코덱을 반환합니다."""
        target_file = None

        # 1. 폴더 안의 파일들을 뒤져서 그룹 ID가 이름에 포함된 파일 찾기
        try:
            for filename in os.listdir(xml_folder_path):
                # group_id가 파일명에 포함되어 있으면 타겟으로 지정
                if group_id in filename and filename.endswith(".xml"):
                    target_file = os.path.join(xml_folder_path, filename)
                    break
        except Exception as e:
            print(f"[FileManager] 폴더 읽기 에러: {e}")
            return "", ""

        # 파일이 없으면 빈 문자열 반환
        if not target_file:
            return "", ""

        # 2. 해당 파일 파싱해서 코덱 정보 뽑기
        try:
            tree = ET.parse(target_file)
            root = tree.getroot()

            # 네임스페이스 설정 (실제 3GPP 표준에 맞춘 세팅)
            namespaces = {"mcpttgi": "urn:3gpp:ns:mcpttGroupInfo:1.0"}

            voice_codec = ""
            video_codec = ""

            # 음성 코덱 찾기
            voice_node = root.find(
                ".//mcpttgi:preferred-voice-encodings/mcpttgi:encoding", namespaces
            )
            if voice_node is not None:
                voice_codec = voice_node.get("name", "")

            # 영상 코덱 찾기
            video_node = root.find(
                ".//mcpttgi:mcvideo-preferred-video-encodings/mcpttgi:encoding",
                namespaces,
            )
            if video_node is not None:
                video_codec = video_node.get("name", "")

            return voice_codec, video_codec

        except Exception as e:
            print(f"[FileManager] [{group_id}] 코덱 파일 파싱 에러: {e}")
            return "", ""

    @staticmethod
    def get_regroup_list(xml_folder_path):
        """XML 폴더를 탐색하여 중복 없이 ReGroup 정보만 추출합니다."""
        regroup_data = []
        seen_ids = set()  # 💡 중복 출력을 막기 위한 ID 보관함

        if not xml_folder_path or not os.path.exists(xml_folder_path):
            return regroup_data

        try:
            for filename in os.listdir(xml_folder_path):
                if filename.endswith(".xml"):
                    file_path = os.path.join(xml_folder_path, filename)
                    try:
                        tree = ET.parse(file_path)
                        root = tree.getroot()

                        for elem in root.iter():
                            if "on-network-regrouped" in elem.tag:

                                raw_id = elem.get("temporary-MCPTT-group-ID", "")
                                call_id = "Unknown"
                                if raw_id:
                                    match = re.search(r"sip:([^@]+)@", raw_id)
                                    if match:
                                        call_id = match.group(1)

                                # 💡 [핵심 안전장치] 이미 아까 찾아서 리스트에 넣은 ID면 패스!
                                if call_id in seen_ids:
                                    break
                                seen_ids.add(call_id)  # 처음 보는 ID면 보관함에 넣기

                                name = elem.get(
                                    "temporary-MCPTT-group-name", "Unknown ReGroup"
                                )
                                voice, video = FileManager.get_group_codecs(
                                    xml_folder_path, call_id
                                )

                                regroup_data.append(
                                    {
                                        "name": name,
                                        "id": call_id,
                                        "type": "ReGroup",
                                        "voice_codec": voice,
                                        "video_codec": video,
                                    }
                                )
                                break  # 이 파일에선 찾았으니 다음 파일로 넘어가기

                    except Exception as e:
                        continue

        except Exception as e:
            print(f"[FileManager] ❌ ReGroup 탐색 중 에러: {e}")

        return regroup_data

    @staticmethod
    def get_all_users_from_xml(xml_folder_path):
        """XML 폴더를 뒤져서 그룹이 아닌 '유저' 정보만 중복 없이 추출합니다."""
        user_list = []
        seen_ids = set()

        if not xml_folder_path or not os.path.exists(xml_folder_path):
            return user_list

        for filename in os.listdir(xml_folder_path):
            if not filename.endswith(".xml"):
                continue

            filepath = os.path.join(xml_folder_path, filename)
            try:
                tree = ET.parse(filepath)
                for elem in tree.getroot().iter():
                    u_name = ""
                    d_name = "이름 없음"

                    # 1. 하위 태그 텍스트에서 URI와 이름 찾기
                    for child in elem:
                        if "uri-entry" in child.tag or "uri" in child.tag:
                            if child.text:
                                match = re.search(r"sip:([^@]+)@", child.text)
                                if match:
                                    u_name = match.group(1)
                        if "display-name" in child.tag:
                            if child.text:
                                d_name = child.text

                    # 2. 속성(Attribute)에 URI가 숨어있는 경우 대응 (<entry uri="...">)
                    if not u_name:
                        raw_uri = elem.get("uri", "")
                        if raw_uri:
                            match = re.search(r"sip:([^@]+)@", raw_uri)
                            if match:
                                u_name = match.group(1)
                                # 이름 태그가 하위에 있는지 확인 (네임스페이스 무시)
                                for child in elem:
                                    if "display-name" in child.tag and child.text:
                                        d_name = child.text
                                        break

                    # 💡 [핵심 필터링] 번호가 있고, 끝이 'g'로 끝나지 않는 것만(그룹 제외) 추가!
                    if u_name and not u_name.endswith("g"):
                        if u_name not in seen_ids:
                            user_list.append({"name": u_name, "display_name": d_name})
                            seen_ids.add(u_name)

            except Exception:
                continue

        # 유저 ID 기준으로 보기 좋게 정렬
        user_list.sort(key=lambda x: x["name"])
        return user_list
