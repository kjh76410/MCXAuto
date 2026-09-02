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

# action key -> (표시 이름, 객체 선택 필요 여부, 값 입력 필요 여부, 값 입력란 placeholder,
#                두 번째 객체 선택 필요 여부)
ACTION_META = {
    "click": ("클릭", True, False, "", False),
    "long_click": ("길게 클릭", True, False, "", False),
    "set_text": ("텍스트 입력", True, True, "입력할 텍스트", False),
    "wait_exists": ("나타날 때까지 대기", True, True, "최대 대기 시간(초), 비우면 10초", False),
    # 저장해둔 값이 아니라, 지금 화면에 있는 두 객체의 실제 값끼리 비교합니다.
    "check_same": ("두 객체 값 같은지 확인", True, False, "", True),
    # 상태를 checked/selected 같은 속성으로 판단하지 않고, '원하는 상태를 나타내는
    # 확인 객체'가 지금 화면에 있는지로 판단합니다(예: 일반 메시지 아이콘이 이미
    # 보이면 = 원하는 상태니 그냥 넘어감. 안 보이면 = 아직 비상 상태니 버튼을
    # 눌러서 바꿔야 함). 커스텀으로 그린 아이콘/버튼처럼 실제 checked 속성이 없는
    # 토글에도 씁니다.
    "click_if_missing": ("조건부 클릭(확인 객체가 없으면 클릭)", True, False, "", True),
    # android.widget.ToggleButton/CheckBox/Switch처럼 실제 checked 속성을 보고하는
    # 진짜 토글 위젯 전용입니다(객체 관리에서 요소를 고를 때 "checkable: 예"로
    # 뜨는지 먼저 확인하세요). 커스텀으로 그린 아이콘처럼 checked 속성이 없는
    # 버튼에는 안 맞으니 그때는 click_if_missing을 쓰세요.
    "toggle_state": ("토글 상태 맞추기(켜짐/꺼짐)", True, True, "on(켜짐) 또는 off(꺼짐)", False),
    "sleep": ("그냥 대기", False, True, "대기할 시간(초)", False),
    "back": ("뒤로가기 버튼", False, False, "", False),
    # 캡처해둔 특정 객체가 아니라, 프로젝트 창의 주채널/부채널 드롭다운에서 지금
    # 지정된 실제 채널명으로 화면을 찾아 클릭합니다. 채널마다 새로 객체를
    # 캡처하거나 channel_role을 붙일 필요 없이, 시나리오 자체에 "이 자리는
    # 주채널/부채널"이라고 바로 넣을 수 있게 하기 위한 전용 동작입니다.
    "find_main_channel": ("주채널 찾기(클릭)", False, False, "", False),
    "find_sub_channel": ("부채널 찾기(클릭)", False, False, "", False),
    # 재난망/재난망_LM75 전용. 프로젝트 창의 일반그룹/공통통화그룹(+ 각 SRTP)
    # 드롭다운에서 지정한 실제 그룹명으로 찾아 클릭합니다.
    "find_normal_group": ("일반그룹 찾기(클릭)", False, False, "", False),
    "find_normal_group_srtp": ("일반그룹 SRTP 찾기(클릭)", False, False, "", False),
    "find_common_group": ("공통통화그룹 찾기(클릭)", False, False, "", False),
    "find_common_group_srtp": ("공통통화그룹 SRTP 찾기(클릭)", False, False, "", False),
}

# find_main_channel/find_sub_channel/find_normal_group/find_normal_group_srtp/
# find_common_group/find_common_group_srtp 액션 -> channel_roles의 키.
CHANNEL_FIND_ACTION_ROLES = {
    "find_main_channel": "주채널",
    "find_sub_channel": "부채널",
    "find_normal_group": "일반그룹",
    "find_normal_group_srtp": "일반그룹 SRTP",
    "find_common_group": "공통통화그룹",
    "find_common_group_srtp": "공통통화그룹 SRTP",
}


def step_label(step):
    """스텝 하나를 목록/로그에 보여줄 한 줄 문자열로 만듭니다."""
    label, _needs_object, _needs_value, _placeholder, _needs_object2 = ACTION_META[step["action"]]
    text = f"[{label}]"
    if step.get("object"):
        text += f" {step['object']}"
    if step.get("object2"):
        if step["action"] == "click_if_missing":
            text += f"  (없으면 '{step['object2']}' 클릭)"
        else:
            text += f" ↔ {step['object2']}"
    if step.get("value"):
        text += f'  ← "{step["value"]}"'
    return text


def _selector_code(node):
    """selector()와 같은 우선순위로, 실제 셀렉터를 만드는 코드 문자열을 만듭니다."""
    if node.get("resource_id"):
        return f"d(resourceId={node['resource_id']!r})"
    if node.get("text"):
        return f"d(text={node['text']!r})"
    if node.get("desc"):
        return f"d(description={node['desc']!r})"
    return f"d(className={node.get('class_name', '')!r})"


def _state_selector_kwargs(node):
    """존재 여부로 '지금 상태'를 판단할 때 쓸 조건들. resourceId/text/desc 중
    하나만 골라 쓰는 selector()와 달리, 저장돼 있는 값을 전부 같이 조건으로
    씁니다. 아이콘처럼 resourceId는 상태와 무관하게 항상 같고 desc/text만 상태에
    따라 달라지는 경우, resourceId만 보면 상태와 상관없이 늘 '있음'으로 나와
    상태를 구분하지 못하기 때문입니다."""
    kwargs = {}
    if node.get("resource_id"):
        kwargs["resourceId"] = node["resource_id"]
    if node.get("text"):
        kwargs["text"] = node["text"]
    if node.get("desc"):
        kwargs["description"] = node["desc"]
    if not kwargs:
        kwargs["className"] = node.get("class_name", "")
    return kwargs


def _state_selector(d, node):
    return d(**_state_selector_kwargs(node))


def _state_selector_code(node):
    kwargs = _state_selector_kwargs(node)
    args = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    return f"d({args})"


def step_real_code_lines(step, saved_objects):
    """스텝 하나를, execute_step()이 실제로 하는 일 그대로 옮긴 파이썬 코드
    줄 목록으로 바꿉니다(한 스텝이 여러 줄일 수 있어 리스트로 돌려줍니다).
    저장된 객체의 실제 resourceId/text 등을 그대로 풀어써서, 시나리오 작성
    화면에서 만든 시나리오도 코드형 시나리오처럼 '진짜 코드'로 읽히게 하기
    위한 것입니다. execute_step과 다르게 여기서 실제로 실행하진 않습니다."""
    action = step["action"]
    value = step.get("value") or ""

    if action == "back":
        # execute_step의 back 분기와 동일하게, 여기서 끝(아래 공통 sleep(1)을
        # 또 붙이면 실제와 달리 두 번 대기하는 것처럼 보입니다).
        return ['d.press("back")', "time.sleep(1)"]

    if action == "sleep":
        duration = value if value else "1"
        # execute_step은 sleep 액션 자신의 대기 + 맨 끝의 공통 sleep(1)까지
        # 두 번 잡니다. 실제 동작 그대로 두 줄로 보여줍니다.
        return [f"time.sleep({duration})", "time.sleep(1)"]

    if action in CHANNEL_FIND_ACTION_ROLES:
        role = CHANNEL_FIND_ACTION_ROLES[action]
        # 실제 채널명은 실행 시점에 프로젝트 창의 드롭다운에서 정해지므로
        # 여기서는 자리표시자로만 보여줍니다. 필요하면 스크롤도 합니다.
        return [f"ensure_channel_visible(d, <{role}>).click()", "time.sleep(1)"]

    obj_name = step.get("object") or ""
    node = saved_objects.get(obj_name)
    if node is None:
        # 객체 관리에서 지워졌거나 이름이 안 맞으면 실제 셀렉터를 만들 수 없으니
        # 눈에 띄게 표시만 해둡니다.
        return [f"# ⚠️ 객체 {obj_name!r}을(를) 찾을 수 없습니다 (객체 관리에서 삭제되었을 수 있음)"]

    sel = _selector_code(node)

    if action == "check_same":
        obj2_name = step.get("object2") or ""
        node2 = saved_objects.get(obj2_name)
        if node2 is None:
            return [f"# ⚠️ 비교 대상 객체 {obj2_name!r}을(를) 찾을 수 없습니다 (객체 관리에서 삭제되었을 수 있음)"]
        sel2 = _selector_code(node2)
        return [f"assert {sel}.get_text() == {sel2}.get_text()", "time.sleep(1)"]

    if action == "click_if_missing":
        obj2_name = step.get("object2") or ""
        node2 = saved_objects.get(obj2_name)
        if node2 is None:
            return [f"# ⚠️ 클릭할 객체 {obj2_name!r}을(를) 찾을 수 없습니다 (객체 관리에서 삭제되었을 수 있음)"]
        sel2 = _selector_code(node2)
        # 확인 객체는 resourceId만으로 보면 상태를 구분 못 할 수 있어(위 주석 참고)
        # 저장된 조건을 전부 합친 셀렉터로 확인합니다.
        state_sel = _state_selector_code(node)
        return [
            f"if not {state_sel}.exists:",
            f"    {sel2}.click()",
            "time.sleep(1)",
        ]

    if action == "toggle_state":
        desired_on = value.strip().lower() in ("on", "켜짐", "켜기", "true", "1")
        return [
            f"if bool({sel}.info.get('checked')) != {desired_on}:",
            f"    {sel}.click()",
            "time.sleep(1)",
        ]

    if action == "click":
        line = f"{sel}.click()"
    elif action == "long_click":
        line = f"{sel}.long_click()"
    elif action == "set_text":
        line = f"{sel}.set_text({value!r})"
    elif action == "wait_exists":
        timeout = value if value else "10"
        line = f"{sel}.wait(timeout={timeout})"
    else:
        line = f"{sel}"

    # execute_step은 back을 뺀 모든 액션 뒤에 공통으로 1초를 더 기다립니다.
    return [line, "time.sleep(1)"]


def _resolve_channel_node(node, channel_roles):
    """node가 특정 채널 역할(주채널/부채널)로 저장된 객체면, 캡처 당시의 채널명
    대신 지금 그 역할로 지정된 실제 채널명으로 바꿔치기한 사본을 돌려준다.
    역할이 없거나 channel_roles에 해당 역할이 아직 지정 안 됐으면(None) 캡처된
    값 그대로 둔다(안전한 폴백).

    resourceId/desc는 함께 비워서 selector()가 text 매칭으로 이 요소를 찾게
    만든다. 리스트의 채널 행들은 보통 같은 resourceId를 공유하는 재활용 뷰라,
    resourceId를 그대로 두면 selector()가 우선순위상 resourceId부터 보고
    아무 행이나(대개 캡처 당시의 첫 행) 찾아버려서 text를 바꾼 게 무의미해진다."""
    role = node.get("channel_role")
    if role and channel_roles and channel_roles.get(role):
        node = dict(node)
        node["text"] = channel_roles[role]
        node["resource_id"] = ""
        node["desc"] = ""
    return node


def _get_node(saved_objects, obj_name, channel_roles=None):
    node = saved_objects.get(obj_name) if obj_name else None
    if node is None:
        return None
    return _resolve_channel_node(node, channel_roles)


def selector(d, node):
    """객체 관리에서 저장해둔 노드 dict를 uiautomator2 셀렉터로 바꿉니다.
    resourceId/text가 둘 다 없는 아이콘류(예: 서로 다른 상태를 나타내는 두
    아이콘)는 content-desc(desc)로라도 구분해야, className만 남아 화면의 같은
    종류 위젯 아무거나와 매치되는 걸(=사실상 항상 '있음'으로 보이는 것) 막습니다."""
    if node.get("resource_id"):
        return d(resourceId=node["resource_id"])
    if node.get("text"):
        return d(text=node["text"])
    if node.get("desc"):
        return d(description=node["desc"])
    return d(className=node.get("class_name", ""))


def _infer_package(node):
    """package가 따로 저장 안 된(예전에 저장한) 객체도, resource_id 앞부분이
    보통 패키지명이라 거기서 유추해봅니다."""
    package = node.get("package")
    if package:
        return package
    resource_id = node.get("resource_id") or ""
    if ":id/" in resource_id:
        return resource_id.split(":id/", 1)[0]
    return None


def ensure_object_visible(d, node, max_attempts=8):
    """클릭/입력 대상 요소가 지금 화면에 실제로 있는지 먼저 확인합니다. 다른
    화면에 있어서(activity가 안 떠 있어서) 안 보이면 back 키를 눌러보다가,
    그래도 안 보이면(엉뚱한 앱으로 나가버린 경우) 패키지를 다시 실행해 찾아갑니다.
    activity를 문자열로 비교하지 않고 '요소가 보이는지'로 직접 판단하기 때문에
    activity 정보 없이 저장된 예전 객체도 그대로 동작합니다."""
    sel = selector(d, node)
    if sel.wait(timeout=1.5):
        return sel

    package = _infer_package(node)
    for _ in range(max_attempts):
        current = d.app_current()
        if package and current.get("package") != package:
            d.app_start(package, stop=False)
        else:
            d.press("back")
        time.sleep(1)
        if sel.wait(timeout=1.5):
            return sel

    hint = node.get("resource_id") or node.get("text") or node.get("class_name") or ""
    raise RuntimeError(f"객체 '{hint}'가 있는 화면을 찾지 못했습니다.")


def ensure_channel_visible(d, channel_name, max_attempts=8, max_swipes=15):
    """주채널/부채널/공통통화그룹 찾기 전용. 채널 목록은 길면 스크롤해야 보이는
    항목이 있을 수 있어, ensure_object_visible과 달리 text가 안 보이면 화면을
    옮기기 전에 먼저 스크롤 가능한 컨테이너를 훑어가며 찾습니다.

    scroll.to()의 내장 스크롤에만 맡기면(swipe 몇 번 만에 못 찾으면 그냥
    포기) 목록이 길 때 놓치는 경우가 있어서, 직접 두 단계로 나눠 찾습니다:
    1) 맨 위로 끝까지 올려서 확인 (목록 위쪽에 있는 경우)
    2) 위에 없으면, 한 칸씩 아래로 내리며 리스트 끝까지 매번 확인 (아래쪽에 있는 경우)

    그래도 없으면(채널 목록 화면 자체가 안 떠 있을 수 있어) back을 눌러 화면을
    바꿔가며 매번 다시 1)~2)를 반복합니다."""
    sel = d(text=channel_name)

    def scroll_and_find():
        if sel.wait(timeout=1.0):
            return True

        scrollable = d(scrollable=True)
        if not scrollable.exists:
            return False

        # 1) 위로 끝까지 올려서 확인
        scrollable.scroll.toBeginning(max_swipes=max_swipes)
        if sel.wait(timeout=1.0):
            return True

        # 2) 위에 없으면 한 칸씩 아래로 내리며 끝까지 확인
        for _ in range(max_swipes):
            scrolled_more = scrollable.scroll.forward()
            if sel.wait(timeout=1.0):
                return True
            if not scrolled_more:
                # 더 내려갈 수 없으면(리스트 끝) 그만합니다.
                break
        return False

    if scroll_and_find():
        return sel

    for _ in range(max_attempts):
        d.press("back")
        time.sleep(1)
        if scroll_and_find():
            return sel

    raise RuntimeError(f"'{channel_name}' 채널을 화면에서 찾지 못했습니다(스크롤 포함).")


def execute_step(d, saved_objects, step, channel_roles=None):
    """스텝 하나를 실제로 단말에 실행합니다. 실패하면 예외를 던집니다.
    channel_roles({"주채널": 실제채널명, "부채널": 실제채널명})가 주어지면,
    channel_role이 지정된 객체는 캡처 당시 값 대신 이 값으로 셀렉터를 만듭니다."""
    action = step["action"]
    value = step.get("value") or ""
    _label, needs_object, _needs_value, _placeholder, needs_object2 = ACTION_META[action]

    if action == "back":
        d.press("back")
        time.sleep(1)
        return

    if action in CHANNEL_FIND_ACTION_ROLES:
        # 캡처해둔 객체가 아니라, 지금 프로젝트 창에서 지정된 실제 채널/그룹명으로
        # 곧바로 화면을 찾아 클릭합니다(스크롤 포함). 다른 화면에 있어도
        # back으로 목록 화면까지 찾아가게 합니다.
        role = CHANNEL_FIND_ACTION_ROLES[action]
        channel_name = (channel_roles or {}).get(role)
        if not channel_name:
            raise RuntimeError(f"{role}이 지정되지 않았습니다 (프로젝트 창에서 먼저 채널을 골라주세요)")
        ensure_channel_visible(d, channel_name).click()
        time.sleep(1)
        return

    if action == "click_if_missing":
        # 확인 객체(원하는 상태를 나타냄)는 '있으면 그만, 없으면 문제'라
        # ensure_object_visible처럼 back/앱 재실행까지 시도하며 찾지 않고,
        # 지금 화면 기준으로 가볍게만 확인합니다(없는 게 정상적인 결과일 수
        # 있어서). 없을 때만 클릭할 객체를 찾아 누릅니다.
        obj_name = step.get("object")
        obj2_name = step.get("object2")
        node = _get_node(saved_objects, obj_name, channel_roles)
        node2 = _get_node(saved_objects, obj2_name, channel_roles)
        if node is None:
            raise RuntimeError(f"확인할 객체 '{obj_name}'을(를) 찾을 수 없습니다 (객체 관리에서 삭제되었을 수 있음)")
        if node2 is None:
            raise RuntimeError(f"클릭할 객체 '{obj2_name}'을(를) 찾을 수 없습니다 (객체 관리에서 삭제되었을 수 있음)")
        # resourceId만으로 보면 상태를 구분 못 할 수 있어(위 주석 참고) 저장된
        # 조건(resourceId/text/desc)을 전부 합친 셀렉터로 확인합니다.
        if not _state_selector(d, node).exists:
            ensure_object_visible(d, node2).click()
        time.sleep(1)
        return

    sel = None
    if needs_object:
        obj_name = step.get("object")
        node = _get_node(saved_objects, obj_name, channel_roles)
        if node is None:
            raise RuntimeError(f"객체 '{obj_name}'을(를) 찾을 수 없습니다 (객체 관리에서 삭제되었을 수 있음)")
        if action in ("click", "long_click", "set_text", "check_same", "toggle_state"):
            # 대상 화면이 안 떠 있으면 back/앱 재실행으로 찾아간 뒤 클릭/입력합니다.
            sel = ensure_object_visible(d, node)
        else:
            # wait_exists는 자기 타임아웃으로 로딩을 기다리는 게 목적이라
            # 여기서 먼저 back을 눌러버리면 오히려 방해가 됩니다.
            sel = selector(d, node)

    sel2 = None
    if needs_object2:
        obj2_name = step.get("object2")
        node2 = _get_node(saved_objects, obj2_name, channel_roles)
        if node2 is None:
            raise RuntimeError(f"비교 대상 객체 '{obj2_name}'을(를) 찾을 수 없습니다 (객체 관리에서 삭제되었을 수 있음)")
        # 보통 두 객체는 같은 화면에 같이 있으니, 첫 객체를 찾아간 뒤라면 대부분
        # 곧바로 보입니다.
        sel2 = ensure_object_visible(d, node2)

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
    elif action == "check_same":
        # 저장해둔 값이 아니라, 지금 화면에 있는 두 객체의 실제 값끼리 비교합니다.
        actual1 = sel.get_text() or ""
        actual2 = sel2.get_text() or ""
        if actual1 != actual2:
            raise RuntimeError(
                f"두 값이 다릅니다 ('{step.get('object')}': '{actual1}' / "
                f"'{step.get('object2')}': '{actual2}')"
            )
    elif action == "toggle_state":
        # 무조건 누르면 원하는 것과 반대로 뒤집힐 수 있어서, 지금 checked 상태를
        # 먼저 읽어보고 원하는 상태가 아닐 때만 누릅니다.
        desired_on = value.strip().lower() in ("on", "켜짐", "켜기", "true", "1")
        info = sel.info or {}
        current_on = bool(info.get("checked")) or bool(info.get("selected"))
        if current_on != desired_on:
            sel.click()
    elif action == "sleep":
        time.sleep(float(value) if value else 1.0)

    time.sleep(1)


def run_scenario(uuid, project, steps, on_log=print, title=None, channel_roles=None):
    """단말(uuid)에 시나리오 스텝들을 순서대로 실행합니다.
    첫 실패에서 멈추며, 끝까지 성공하면 True를 돌려줍니다.
    channel_roles는 프로젝트 창의 주채널/부채널 드롭다운에서 지정한
    {"주채널": 실제채널명, "부채널": 실제채널명} 매핑으로, channel_role이
    붙은 객체의 셀렉터를 실행 시점에 그 채널명으로 바꿔치기하는 데 씁니다."""
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
            execute_step(d, saved_objects, step, channel_roles)
            on_log(f"  {i}. {label}  ✅")
        except Exception as e:
            on_log(f"  {i}. {label}  ❌ {e}")
            on_log("⏹ 오류가 발생해 실행을 중단했습니다.")
            return False

    on_log("✅ 시나리오 실행 완료")
    return True
