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
