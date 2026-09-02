import json
import os

STORE_PATH = "saved_scenarios.json"


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


def list_scenarios(project_name):
    """{시나리오 이름: [step, ...]} 형태로, 저장된 순서 그대로 돌려줍니다."""
    return _load_all().get(project_name, {})


def save_scenario(project_name, scenario_name, steps):
    data = _load_all()
    data.setdefault(project_name, {})[scenario_name] = steps
    _save_all(data)


def delete_scenario(project_name, scenario_name):
    data = _load_all()
    if project_name in data and scenario_name in data[project_name]:
        del data[project_name][scenario_name]
        _save_all(data)


def move_scenario(project_name, scenario_name, direction):
    """scenario_name을 목록에서 direction만큼 옮깁니다(-1: 위로, +1: 아래로).
    이미 맨 위/맨 아래라 옮길 수 없으면 아무 것도 안 하고 False를 돌려줍니다."""
    data = _load_all()
    project_scenarios = data.get(project_name)
    if not project_scenarios or scenario_name not in project_scenarios:
        return False
    names = list(project_scenarios.keys())
    idx = names.index(scenario_name)
    new_idx = idx + direction
    if not (0 <= new_idx < len(names)):
        return False
    names[idx], names[new_idx] = names[new_idx], names[idx]
    data[project_name] = {n: project_scenarios[n] for n in names}
    _save_all(data)
    return True
