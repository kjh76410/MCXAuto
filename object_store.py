import json
import os

STORE_PATH = "saved_objects.json"
FOLDERS_STORE_PATH = "object_folders.json"
DEFAULT_FOLDER_NAMES_PATH = "object_default_folder_names.json"

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


def _load_default_names():
    if not os.path.exists(DEFAULT_FOLDER_NAMES_PATH):
        return {}
    try:
        with open(DEFAULT_FOLDER_NAMES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_default_names(data):
    with open(DEFAULT_FOLDER_NAMES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_objects(project_name):
    """{이름: node dict} 형태로, 저장된 순서 그대로 돌려줍니다."""
    return _load_all().get(project_name, {})


def default_folder_name(project_name):
    """이 프로젝트의 기본 폴더 표시 이름. 이름을 바꾼 적 없으면 '기본 폴더'."""
    return _load_default_names().get(project_name) or DEFAULT_FOLDER


def object_folder(node, project_name=None):
    """노드의 폴더 이름을 돌려줍니다. 폴더 기능 추가 전에 저장된 객체처럼 folder
    필드가 없는 경우 project_name의 기본 폴더 이름으로(안 주면 '기본 폴더'로)
    취급합니다."""
    folder = node.get("folder")
    if folder:
        return folder
    return default_folder_name(project_name) if project_name else DEFAULT_FOLDER


def list_folders(project_name):
    """프로젝트의 폴더 이름 목록을 저장된 순서 그대로 돌려줍니다. 기본 폴더는
    명시적으로 추가한 적 없어도 항상 맨 앞에 포함됩니다(이름을 바꿨으면 바뀐
    이름으로)."""
    default_name = default_folder_name(project_name)
    data = _load_folders_all()
    folders = [f for f in data.get(project_name, []) if f != default_name]
    return [default_name] + folders


def add_folder(project_name, folder_name):
    """새 폴더를 추가합니다. 이미 있으면 아무 것도 안 합니다."""
    folder_name = folder_name.strip()
    if not folder_name or folder_name == default_folder_name(project_name):
        return
    data = _load_folders_all()
    folders = data.setdefault(project_name, [])
    if folder_name not in folders:
        folders.append(folder_name)
        _save_folders_all(data)


def rename_folder(project_name, old_name, new_name):
    """폴더 이름을 바꾸고, 그 폴더에 속한 객체들의 folder 필드도 함께 갱신합니다.
    기본 폴더도 이름을 바꿀 수 있습니다(기본 폴더로서의 역할은 유지됩니다).
    새 이름이 이미 있는 폴더면 그 폴더로 합쳐집니다."""
    old_name = (old_name or "").strip()
    new_name = (new_name or "").strip()
    if not new_name or old_name == new_name:
        return False

    current_default = default_folder_name(project_name)
    renaming_default = old_name == current_default

    # 폴더 목록/기본 폴더 이름을 바꾸기 전에, "지금 기준"으로 old_name에 속하는
    # 객체들을 먼저 찾아 명시적으로 옮겨둡니다(기본 폴더처럼 folder 필드가 아예
    # 없는 객체까지 포함해서).
    data = _load_all()
    for node in data.get(project_name, {}).values():
        if object_folder(node, project_name) == old_name:
            node["folder"] = new_name
    _save_all(data)

    folders_data = _load_folders_all()
    folders = folders_data.setdefault(project_name, [])
    if old_name in folders:
        folders.remove(old_name)
    if renaming_default:
        # 기본 폴더는 folders 목록이 아니라 별도 저장소(이름만)로 관리하므로,
        # 새 이름이 folders 목록에 남아 있으면 같은 폴더가 두 번 보이게 됩니다.
        if new_name in folders:
            folders.remove(new_name)
        default_names = _load_default_names()
        default_names[project_name] = new_name
        _save_default_names(default_names)
    elif new_name != current_default and new_name not in folders:
        folders.append(new_name)
    _save_folders_all(folders_data)
    return True


def delete_folder(project_name, folder_name):
    """폴더와 그 안의 모든 객체를 삭제합니다. 기본 폴더는 삭제할 수 없습니다."""
    folder_name = (folder_name or "").strip()
    if not folder_name or folder_name == default_folder_name(project_name):
        return False

    folders_data = _load_folders_all()
    folders = folders_data.get(project_name, [])
    if folder_name in folders:
        folders.remove(folder_name)
        _save_folders_all(folders_data)

    data = _load_all()
    project_objects = data.get(project_name, {})
    to_delete = [
        name for name, node in project_objects.items()
        if object_folder(node, project_name) == folder_name
    ]
    for name in to_delete:
        del project_objects[name]
    if to_delete:
        _save_all(data)
    return True


def save_object(project_name, obj_name, node, folder=None):
    data = _load_all()
    node = dict(node)
    if folder is not None:
        node["folder"] = folder
    elif "folder" not in node:
        node["folder"] = default_folder_name(project_name)
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
