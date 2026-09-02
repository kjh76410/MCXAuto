"""저장된 시나리오와 그 폴더 구성을 파일로 관리합니다.

시나리오 본문은 예전 그대로 saved_scenarios.json에 {프로젝트: {이름: [스텝, ...]}}
형태로 둡니다(프로젝트 창/시나리오 목록 화면이 그대로 읽습니다). 폴더는 값의
모양을 바꾸지 않으려고 별도 파일(scenario_folders.json)에 따로 저장합니다 —
객체 쪽(object_store)이 폴더를 노드 dict 안에 넣는 것과 다른 이유는, 시나리오의
값이 dict가 아니라 스텝 리스트라 끼워 넣을 자리가 없기 때문입니다.

scenario_folders.json 모양:
    {"<프로젝트>": {"default": "기본 폴더", "folders": [...], "assign": {"<시나리오>": "<폴더>"}}}
"""

import json
import os

STORE_PATH = "saved_scenarios.json"
FOLDERS_STORE_PATH = "scenario_folders.json"

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


def _project_folders(data, project_name):
    entry = data.setdefault(project_name, {})
    entry.setdefault("default", DEFAULT_FOLDER)
    entry.setdefault("folders", [])
    entry.setdefault("assign", {})
    return entry


def list_scenarios(project_name):
    """{시나리오 이름: [step, ...]} 형태로, 저장된 순서 그대로 돌려줍니다."""
    return _load_all().get(project_name, {})


# ---------- 폴더 ----------
def default_folder_name(project_name):
    """이 프로젝트의 기본 폴더 표시 이름. 이름을 바꾼 적 없으면 '기본 폴더'."""
    entry = _load_folders_all().get(project_name) or {}
    return entry.get("default") or DEFAULT_FOLDER


def list_folders(project_name):
    """프로젝트의 폴더 이름 목록을 저장된 순서 그대로 돌려줍니다. 기본 폴더는
    따로 추가한 적 없어도 항상 맨 앞에 포함됩니다(이름을 바꿨으면 바뀐 이름으로)."""
    default_name = default_folder_name(project_name)
    entry = _load_folders_all().get(project_name) or {}
    folders = [f for f in entry.get("folders", []) if f != default_name]
    return [default_name] + folders


def scenario_folder(project_name, scenario_name):
    """시나리오가 속한 폴더 이름. 지정된 적 없으면(폴더 기능 전에 저장된 것 포함)
    기본 폴더로 봅니다. 지금은 없는 폴더를 가리키고 있어도 마찬가지입니다."""
    entry = _load_folders_all().get(project_name) or {}
    folder = (entry.get("assign") or {}).get(scenario_name)
    return folder if folder in list_folders(project_name) else default_folder_name(project_name)


def add_folder(project_name, folder_name):
    """새 폴더를 추가합니다. 이미 있으면 아무 것도 안 합니다."""
    folder_name = (folder_name or "").strip()
    if not folder_name or folder_name == default_folder_name(project_name):
        return
    data = _load_folders_all()
    entry = _project_folders(data, project_name)
    if folder_name not in entry["folders"]:
        entry["folders"].append(folder_name)
        _save_folders_all(data)


def rename_folder(project_name, old_name, new_name):
    """폴더 이름을 바꾸고, 그 폴더에 있던 시나리오들의 소속도 함께 옮깁니다.
    기본 폴더도 이름을 바꿀 수 있습니다(기본 폴더 역할은 유지).
    새 이름이 이미 있는 폴더면 그 폴더로 합쳐집니다."""
    old_name = (old_name or "").strip()
    new_name = (new_name or "").strip()
    if not new_name or old_name == new_name:
        return False

    current_default = default_folder_name(project_name)
    renaming_default = old_name == current_default

    # 폴더 목록/기본 폴더 이름을 바꾸기 전에 "지금 기준"으로 old_name에 속한
    # 시나리오를 먼저 옮겨둡니다(assign에 아예 없는 = 기본 폴더 소속까지 포함).
    moved = [
        name for name in list_scenarios(project_name)
        if scenario_folder(project_name, name) == old_name
    ]

    data = _load_folders_all()
    entry = _project_folders(data, project_name)
    for name in moved:
        entry["assign"][name] = new_name

    if old_name in entry["folders"]:
        entry["folders"].remove(old_name)
    if renaming_default:
        # 기본 폴더는 folders 목록이 아니라 default 항목으로 관리하므로, 새 이름이
        # folders에 남아 있으면 같은 폴더가 두 번 보이게 됩니다.
        if new_name in entry["folders"]:
            entry["folders"].remove(new_name)
        entry["default"] = new_name
    elif new_name != current_default and new_name not in entry["folders"]:
        entry["folders"].append(new_name)

    _save_folders_all(data)
    return True


def delete_folder(project_name, folder_name):
    """폴더와 그 안의 모든 시나리오를 삭제합니다. 기본 폴더는 삭제할 수 없습니다."""
    folder_name = (folder_name or "").strip()
    if not folder_name or folder_name == default_folder_name(project_name):
        return False

    to_delete = [
        name for name in list_scenarios(project_name)
        if scenario_folder(project_name, name) == folder_name
    ]

    data = _load_folders_all()
    entry = _project_folders(data, project_name)
    if folder_name in entry["folders"]:
        entry["folders"].remove(folder_name)
    for name in to_delete:
        entry["assign"].pop(name, None)
    _save_folders_all(data)

    if to_delete:
        scenarios = _load_all()
        for name in to_delete:
            scenarios.get(project_name, {}).pop(name, None)
        _save_all(scenarios)
    return True


def set_scenario_folder(project_name, scenario_name, folder):
    """시나리오를 다른 폴더로 옮깁니다. 기본 폴더로 보내면 assign에서 지웁니다
    (지정이 없으면 기본 폴더로 취급되므로 굳이 남겨둘 필요가 없습니다)."""
    data = _load_folders_all()
    entry = _project_folders(data, project_name)
    if not folder or folder == entry["default"]:
        entry["assign"].pop(scenario_name, None)
    else:
        if folder not in entry["folders"]:
            entry["folders"].append(folder)
        entry["assign"][scenario_name] = folder
    _save_folders_all(data)


# ---------- 시나리오 ----------
def save_scenario(project_name, scenario_name, steps, folder=None):
    data = _load_all()
    data.setdefault(project_name, {})[scenario_name] = steps
    _save_all(data)
    if folder is not None:
        set_scenario_folder(project_name, scenario_name, folder)


def delete_scenario(project_name, scenario_name):
    data = _load_all()
    if project_name in data and scenario_name in data[project_name]:
        del data[project_name][scenario_name]
        _save_all(data)

    folders = _load_folders_all()
    entry = folders.get(project_name)
    if entry and scenario_name in (entry.get("assign") or {}):
        del entry["assign"][scenario_name]
        _save_folders_all(folders)


def rename_scenario(project_name, old_name, new_name):
    """이름만 바꿔 저장합니다(스텝과 폴더 소속, 목록에서의 자리는 그대로)."""
    if old_name == new_name:
        return True
    data = _load_all()
    project_scenarios = data.get(project_name) or {}
    if old_name not in project_scenarios:
        return False

    folder = scenario_folder(project_name, old_name)
    # dict는 새 키를 맨 뒤에 붙이므로, 순서를 지키려면 통째로 다시 만듭니다.
    data[project_name] = {
        (new_name if name == old_name else name): steps
        for name, steps in project_scenarios.items()
    }
    _save_all(data)

    folders = _load_folders_all()
    entry = _project_folders(folders, project_name)
    entry["assign"].pop(old_name, None)
    _save_folders_all(folders)
    set_scenario_folder(project_name, new_name, folder)
    return True


def move_scenario(project_name, scenario_name, direction):
    """scenario_name을 같은 폴더 안에서 direction만큼 옮깁니다(-1: 위로, +1: 아래로).

    폴더별로 묶어 보여주기 때문에 전체 순서에서 바로 옆이 아니라 '같은 폴더 안의
    바로 위/아래 시나리오'와 자리를 바꿉니다. 더 옮길 곳이 없으면 False."""
    data = _load_all()
    project_scenarios = data.get(project_name)
    if not project_scenarios or scenario_name not in project_scenarios:
        return False

    names = list(project_scenarios.keys())
    folder = scenario_folder(project_name, scenario_name)
    idx = names.index(scenario_name)

    target = None
    stop = len(names) if direction > 0 else -1
    for i in range(idx + direction, stop, direction):
        if scenario_folder(project_name, names[i]) == folder:
            target = i
            break
    if target is None:
        return False

    names[idx], names[target] = names[target], names[idx]
    data[project_name] = {n: project_scenarios[n] for n in names}
    _save_all(data)
    return True
