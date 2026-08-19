"""시나리오 실행 엔진.

'시나리오 작성' 화면(scenario_builder_page)과 '프로젝트 창'의 시나리오 목록
(project_window) 양쪽에서 같은 방식으로 시나리오를 돌리기 위해, 실제 실행 로직만
UI와 떼어내 여기에 모아둡니다. 이 모듈은 PySide6를 import하지 않으므로 화면 없이
(예: 나중에 명령줄 배치 실행) 그대로 쓸 수 있습니다.

로그는 on_log(문자열) 콜백으로 흘려보내니, 부르는 쪽에서 로그창에 찍든 콘솔에
찍든 알아서 하면 됩니다. 실행은 호출한 스레드에서 그대로 돌기 때문에, UI에서
부를 때는 반드시 별도 스레드에서 부르세요.
"""

import time

import object_store

# action key -> (표시 이름, 객체 선택 필요 여부, 값 입력 필요 여부, 값 입력란 placeholder)
ACTION_META = {
    "click": ("클릭", True, False, ""),
    "long_click": ("길게 클릭", True, False, ""),
    "set_text": ("텍스트 입력", True, True, "입력할 텍스트"),
    "wait_exists": ("나타날 때까지 대기", True, True, "최대 대기 시간(초), 비우면 10초"),
    "sleep": ("그냥 대기", False, True, "대기할 시간(초)"),
    "back": ("뒤로가기 버튼", False, False, ""),
}


def step_label(step):
    """스텝 하나를 목록/로그에 보여줄 한 줄 문자열로 만듭니다."""
    label, _needs_object, _needs_value, _placeholder = ACTION_META[step["action"]]
    text = f"[{label}]"
    if step.get("object"):
        text += f" {step['object']}"
    if step.get("value"):
        text += f'  ← "{step["value"]}"'
    return text


def selector(d, node):
    """객체 관리에서 저장해둔 노드 dict를 uiautomator2 셀렉터로 바꿉니다."""
    if node.get("resource_id"):
        return d(resourceId=node["resource_id"])
    if node.get("text"):
        return d(text=node["text"])
    return d(className=node.get("class_name", ""))


def execute_step(d, saved_objects, step):
    """스텝 하나를 실제로 단말에 실행합니다. 실패하면 예외를 던집니다."""
    action = step["action"]
    value = step.get("value") or ""
    _label, needs_object, _needs_value, _placeholder = ACTION_META[action]

    if action == "back":
        d.press("back")
        return

    sel = None
    if needs_object:
        obj_name = step.get("object")
        node = saved_objects.get(obj_name) if obj_name else None
        if node is None:
            raise RuntimeError(f"객체 '{obj_name}'을(를) 찾을 수 없습니다 (객체 관리에서 삭제되었을 수 있음)")
        sel = selector(d, node)

    if action == "click":
        sel.click()
    elif action == "long_click":
        sel.long_click()
    elif action == "set_text":
        sel.set_text(value)
    elif action == "wait_exists":
        timeout = float(value) if value else 10.0
        if not sel.wait(timeout=timeout):
            raise RuntimeError("요소가 나타나지 않았습니다.")
    elif action == "sleep":
        time.sleep(float(value) if value else 1.0)


def run_scenario(uuid, project, steps, on_log=print, title=None):
    """단말(uuid)에 시나리오 스텝들을 순서대로 실행합니다.
    첫 실패에서 멈추며, 끝까지 성공하면 True를 돌려줍니다."""
    try:
        import uiautomator2 as u2

        d = u2.connect(uuid)
    except Exception as e:
        on_log(f"❌ 단말 연결 실패: {e}")
        return False

    saved_objects = object_store.list_objects(project)
    head = f"▶ 시나리오 실행 시작 ({len(steps)}개 스텝)"
    if title:
        head = f"▶ '{title}' 실행 시작 ({len(steps)}개 스텝)"
    on_log(head)

    for i, step in enumerate(steps, 1):
        label = step_label(step)
        try:
            execute_step(d, saved_objects, step)
            on_log(f"  {i}. {label}  ✅")
        except Exception as e:
            on_log(f"  {i}. {label}  ❌ {e}")
            on_log("⏹ 오류가 발생해 실행을 중단했습니다.")
            return False

    on_log("✅ 시나리오 실행 완료")
    return True
