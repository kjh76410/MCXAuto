import copy
import json
import os

CONFIG_PATH = "project_config.json"

# 프로젝트를 "국내"/"해외"로 묶어 관리하기 위한 region 값들. 아직 region을
# 지정하지 않은 프로젝트는 None(미지정)으로 다룹니다.
REGIONS = ("국내", "해외")


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


def add_project(source_project_name, new_project_name, keyword, handler_module, handler_class, region=None):
    """source_project_name의 설정(features/per_group_emergency_call/db_config 등)을 그대로
    물려받되 keyword/project_name/handler_module/handler_class만 새 값으로 바꾼 항목을
    projects 목록 맨 뒤에 추가합니다. region을 명시하면(REGIONS 중 하나) 그 값으로 덮어쓰고,
    안 주면(None) source의 region을 그대로 물려받습니다(다른 필드들과 같은 방식)."""
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
    if region in REGIONS:
        new_entry["region"] = region

    data.setdefault("projects", []).append(new_entry)
    _save(data)
    return new_entry


def get_project_region(project_name):
    """region이 아직 지정되지 않은 프로젝트는 None(미지정)을 돌려줍니다."""
    proj = get_project(project_name)
    region = proj.get("region") if proj else None
    return region if region in REGIONS else None


def set_project_region(project_name, region):
    """region은 REGIONS 중 하나. 그 외 값(None/빈 문자열 등)을 주면 미지정으로 되돌립니다."""
    data = _load()
    for proj in data.get("projects", []):
        if proj.get("project_name") == project_name:
            if region in REGIONS:
                proj["region"] = region
            else:
                proj.pop("region", None)
            break
    _save(data)


def group_projects_by_region(project_names):
    """project_names(순서 있는 이름 목록)를 국내 -> 해외 -> 미지정 순으로 묶어
    [(그룹 표시 이름 또는 None, [project_name, ...]), ...] 형태로 돌려줍니다.

    실제로 서로 다른 region이 섞여 있을 때만 그룹 이름을 붙이고, 전부 같은
    region이거나(또는 다들 미지정이면) region을 아직 안 쓰는 화면처럼 그룹 이름
    없이 하나로 합쳐 돌려줍니다(첫 번째 튜플의 그룹 이름이 None)."""
    order = REGIONS + (None,)
    buckets = {key: [] for key in order}
    for name in project_names:
        buckets[get_project_region(name)].append(name)

    groups = [(region, buckets[region]) for region in order if buckets[region]]
    if len(groups) <= 1:
        return [(None, list(project_names))]

    labels = {"국내": "국내", "해외": "해외", None: "미지정"}
    return [(labels[region], names) for region, names in groups]
