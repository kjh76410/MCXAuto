import json
import os

STORE_PATH = "saved_objects.json"
FOLDERS_STORE_PATH = "object_folders.json"

DEFAULT_FOLDER = "기본 폴더"


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


def _load_folders_all():
    if not os.path.exists(FOLDERS_STORE_PATH):
        return {}
    try:
        with open(FOLDERS_STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_folders_all(data):
    with open(FOLDERS_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_objects(project_name):
    """{이름: node dict} 형태로, 저장된 순서 그대로 돌려줍니다."""
    return _load_all().get(project_name, {})


def object_folder(node):
    """노드의 폴더 이름을 돌려줍니다. 폴더 기능 추가 전에 저장된 객체는
    folder 필드가 없으니 '기본 폴더'로 취급합니다."""
    return node.get("folder") or DEFAULT_FOLDER


def list_folders(project_name):
    """프로젝트의 폴더 이름 목록을 저장된 순서 그대로 돌려줍니다. '기본 폴더'는
    명시적으로 추가한 적 없어도 항상 맨 앞에 포함됩니다."""
    data = _load_folders_all()
    folders = [f for f in data.get(project_name, []) if f != DEFAULT_FOLDER]
    return [DEFAULT_FOLDER] + folders


def add_folder(project_name, folder_name):
    """새 폴더를 추가합니다. 이미 있으면 아무 것도 안 합니다."""
    folder_name = folder_name.strip()
    if not folder_name or folder_name == DEFAULT_FOLDER:
        return
    data = _load_folders_all()
    folders = data.setdefault(project_name, [])
    if folder_name not in folders:
        folders.append(folder_name)
        _save_folders_all(data)


def save_object(project_name, obj_name, node, folder=None):
    data = _load_all()
    node = dict(node)
    if folder is not None:
        node["folder"] = folder
    elif "folder" not in node:
        node["folder"] = DEFAULT_FOLDER
    data.setdefault(project_name, {})[obj_name] = node
    _save_all(data)


def rename_object(project_name, old_name, new_name):
    """이름만(그리고 그 안 내용은 그대로) 바꿔서 저장합니다. old_name이 없으면
    아무 것도 하지 않고 False를 돌려줍니다."""
    if old_name == new_name:
        return True
    data = _load_all()
    node = data.get(project_name, {}).get(old_name)
    if node is None:
        return False
    data[project_name][new_name] = node
    del data[project_name][old_name]
    _save_all(data)
    return True


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
