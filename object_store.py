import json
import os

STORE_PATH = "saved_objects.json"


def _load_all():
    if not os.path.exists(STORE_PATH):
        return {}
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_all(data):
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_objects(project_name):
    """{이름: node dict} 형태로, 저장된 순서 그대로 돌려줍니다."""
    return _load_all().get(project_name, {})


def save_object(project_name, obj_name, node):
    data = _load_all()
    data.setdefault(project_name, {})[obj_name] = node
    _save_all(data)


def delete_object(project_name, obj_name):
    data = _load_all()
    if project_name in data and obj_name in data[project_name]:
        del data[project_name][obj_name]
        _save_all(data)


def copy_object(source_project, target_project, obj_name, target_name=None):
    """source_project의 obj_name 객체를 target_project로 복사합니다(원본은 유지).
    target_name을 안 주면 같은 이름으로 복사하며, 대상에 이미 같은 이름이 있으면
    덮어씁니다. 원본을 찾지 못하면 False를 돌려줍니다."""
    data = _load_all()
    node = data.get(source_project, {}).get(obj_name)
    if node is None:
        return False
    data.setdefault(target_project, {})[target_name or obj_name] = dict(node)
    _save_all(data)
    return True


def move_object(source_project, target_project, obj_name, target_name=None):
    """copy_object와 동일하되 성공 시 원본(source_project)에서는 지웁니다."""
    if not copy_object(source_project, target_project, obj_name, target_name):
        return False
    delete_object(source_project, obj_name)
    return True
