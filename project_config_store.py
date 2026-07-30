import copy
import json
import os

CONFIG_PATH = "project_config.json"


def _load():
    if not os.path.exists(CONFIG_PATH):
        return {"projects": [], "default": "알 수 없는 프로젝트"}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.write("\n")


def list_projects():
    """project_config.json에 등록된 프로젝트 항목(dict) 리스트를 그대로 돌려줍니다."""
    return _load().get("projects", [])


def get_project(project_name):
    for proj in list_projects():
        if proj.get("project_name") == project_name:
            return proj
    return None


def project_name_exists(project_name):
    return get_project(project_name) is not None


def add_project(source_project_name, new_project_name, keyword, handler_module, handler_class):
    """source_project_name의 설정(features/per_group_emergency_call/db_config 등)을 그대로
    물려받되 keyword/project_name/handler_module/handler_class만 새 값으로 바꾼 항목을
    projects 목록 맨 뒤에 추가합니다."""
    data = _load()
    source = None
    for proj in data.get("projects", []):
        if proj.get("project_name") == source_project_name:
            source = proj
            break

    new_entry = copy.deepcopy(source) if source else {}
    new_entry["keyword"] = keyword
    new_entry["project_name"] = new_project_name
    new_entry["handler_module"] = handler_module
    new_entry["handler_class"] = handler_class

    data.setdefault("projects", []).append(new_entry)
    _save(data)
    return new_entry
