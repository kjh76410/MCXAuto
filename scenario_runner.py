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
from file_manager import FileManager

# 'XML 정보와 비교' 동작에서 어떤 값을 비교할지 고르는 선택지.
# key는 FileManager.parse_my_info_parts()가 돌려주는 (이름, 번호) 튜플의 인덱스에 대응합니다.
MY_INFO_FIELDS = {"name": "단말 이름", "number": "단말 번호"}

# action key -> (표시 이름, 객체 선택 필요 여부, 값 입력 필요 여부, 값 입력란 placeholder,
#                두 번째 객체 선택 필요 여부)
ACTION_META = {
    "click": ("클릭", True, False, "", False),
    "long_click": ("길게 클릭", True, False, "", False),
    "set_text": ("텍스트 입력", True, True, "입력할 텍스트", False),
    "wait_exists": ("나타날 때까지 대기", True, True, "최대 대기 시간(초), 비우면 10초", False),
    # 클릭/입력 없이, 지정한 객체가 있는 화면까지만 이동합니다. 지금 화면에 없으면
    # back을 눌러가며(그래도 없으면 앱을 다시 실행해서) 나타날 때까지 찾습니다
    # (ensure_object_visible과 동일 — click 등의 동작들이 실행 직전에 알아서
    # 하는 것과 같은 화면 찾기를, 클릭 없이 그 자체로 스텝에 넣고 싶을 때 씁니다.
    # 예: 메시지를 시작하기 전에 반드시 채널 목록 화면부터 시작하도록 강제하기).
    "find_object": ("찾기(back으로 화면 찾기, 클릭 안 함)", True, False, "", False),
    # check_same처럼 화면의 두 객체끼리 비교하는 게 아니라, 이 객체 하나의 지금
    # 화면 값이 캡처했을 때 저장해둔 text와 같은지 확인합니다.
    "check_text": ("저장된 text와 같은지 확인", True, False, "", False),
    # 특정 버튼/객체가 아니라 '화면 자체'가 바뀌었는지 확인합니다. 로딩 중이라
    # 버튼이 아직 없어도 Activity는 화면 전환과 동시에 바뀌므로 더 안정적입니다.
    # 여기 고르는 객체는 클릭/찾기 대상이 아니라, 그 객체를 저장할 때 같이
    # 기록해둔 activity 값을 목표 화면으로 쓰기 위한 것뿐입니다(그 화면에서
    # 캡처해둔 아무 객체나 골라도 됩니다).
    "wait_activity": ("화면(Activity) 나타날 때까지 대기", True, True, "최대 대기 시간(초), 비우면 10초", False),
    # 저장해둔 값이 아니라, 지금 화면에 있는 두 객체의 실제 값끼리 비교합니다.
    "check_same": ("두 객체 값 같은지 확인", True, False, "", True),
    # 화면의 두 객체끼리가 아니라, 화면 객체 하나를 단말 XML(user_profile.xml)에서
    # 읽은 단말 이름/번호와 비교합니다. value에는 MY_INFO_FIELDS의 key("name"/
    # "number")를 저장해둡니다.
    "check_matches_my_info": ("객체 값이 단말 정보(XML)와 같은지 확인", True, True, "", False),
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
    # 지정된 실제 채널명으로 화면을 찾아 클릭합니다. 채널마다 객체를 새로 캡처할
    # 필요 없이, 시나리오 자체에 "이 자리는 주채널/부채널"이라고 바로 넣을 수 있게
    # 하기 위한 전용 동작입니다.
    "find_main_channel": ("주채널 찾기(클릭)", False, False, "", False),
    "find_sub_channel": ("부채널 찾기(클릭)", False, False, "", False),
    # 재난망/재난망_LM75 전용. 프로젝트 창의 일반그룹/공통통화그룹(+ 각 SRTP)
    # 드롭다운에서 지정한 실제 그룹명으로 찾아 클릭합니다.
    "find_normal_group": ("일반그룹 찾기(클릭)", False, False, "", False),
    "find_normal_group_srtp": ("일반그룹 SRTP 찾기(클릭)", False, False, "", False),
    "find_common_group": ("공통통화그룹 찾기(클릭)", False, False, "", False),
    "find_common_group_srtp": ("공통통화그룹 SRTP 찾기(클릭)", False, False, "", False),
    # 해외 프로젝트 전용. 프로젝트 창의 Chat group/PreArranged group/Private
    # 드롭다운에서 지정한 실제 이름으로 찾아 클릭합니다.
    "find_chat_group": ("Chat group 찾기(클릭)", False, False, "", False),
    "find_prearranged_group": ("PreArranged group 찾기(클릭)", False, False, "", False),
    "find_private": ("Private 찾기(클릭)", False, False, "", False),
    # 위 find_* 들과 같은 대상을 같은 방식(스크롤+back)으로 찾지만 클릭은 안
    # 합니다(find_object의 "찾기(클릭 안 함)"과 같은 개념) — 통화를 걸지 않고
    # 채널 목록 화면에서 그 채널/그룹이 있는지만 확인하고 싶을 때 씁니다.
    "find_main_channel_only": ("주채널 찾기(클릭 안 함)", False, False, "", False),
    "find_sub_channel_only": ("부채널 찾기(클릭 안 함)", False, False, "", False),
    "find_normal_group_only": ("일반그룹 찾기(클릭 안 함)", False, False, "", False),
    "find_normal_group_srtp_only": ("일반그룹 SRTP 찾기(클릭 안 함)", False, False, "", False),
    "find_common_group_only": ("공통통화그룹 찾기(클릭 안 함)", False, False, "", False),
    "find_common_group_srtp_only": ("공통통화그룹 SRTP 찾기(클릭 안 함)", False, False, "", False),
    "find_chat_group_only": ("Chat group 찾기(클릭 안 함)", False, False, "", False),
    "find_prearranged_group_only": ("PreArranged group 찾기(클릭 안 함)", False, False, "", False),
    "find_private_only": ("Private 찾기(클릭 안 함)", False, False, "", False),
}

# find_* 채널 찾기 액션 -> channel_roles의 키. 프로젝트 창의 "채널 지정"에 어떤
# 행이 보이는지와 무관하게, 여기 있는 역할이 곧 지정 가능한 채널 역할 전부입니다.
CHANNEL_FIND_ACTION_ROLES = {
    "find_main_channel": "주채널",
    "find_sub_channel": "부채널",
    "find_normal_group": "일반그룹",
    "find_normal_group_srtp": "일반그룹 SRTP",
    "find_common_group": "공통통화그룹",
    "find_common_group_srtp": "공통통화그룹 SRTP",
    "find_chat_group": "Chat group",
    "find_prearranged_group": "PreArranged group",
    "find_private": "Private",
}

# 위와 같은 역할이지만 클릭 안 하는 find_*_only 액션용 매핑.
CHANNEL_FIND_NO_CLICK_ACTION_ROLES = {
    "find_main_channel_only": "주채널",
    "find_sub_channel_only": "부채널",
    "find_normal_group_only": "일반그룹",
    "find_normal_group_srtp_only": "일반그룹 SRTP",
    "find_common_group_only": "공통통화그룹",
    "find_common_group_srtp_only": "공통통화그룹 SRTP",
    "find_chat_group_only": "Chat group",
    "find_prearranged_group_only": "PreArranged group",
    "find_private_only": "Private",
}

# 지정 가능한 채널 역할 전체(위 매핑에 나온 순서 그대로).
CHANNEL_ROLES = tuple(CHANNEL_FIND_ACTION_ROLES.values())


def empty_channel_roles():
    """아직 아무 채널도 지정되지 않은 channel_roles 매핑(단말 연결/해제 시 초기값)."""
    return {role: None for role in CHANNEL_ROLES}


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
        if step["action"] == "check_matches_my_info":
            text += f"  ↔ {MY_INFO_FIELDS.get(step['value'], step['value'])}(XML)"
        else:
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

    if action in CHANNEL_FIND_ACTION_ROLES or action in CHANNEL_FIND_NO_CLICK_ACTION_ROLES:
        role = CHANNEL_FIND_ACTION_ROLES.get(action) or CHANNEL_FIND_NO_CLICK_ACTION_ROLES.get(action)
        # 실제 채널명은 실행 시점에 프로젝트 창의 드롭다운에서 정해지므로
        # 여기서는 자리표시자로만 보여줍니다. 필요하면 스크롤도 합니다.
        call = f"ensure_channel_visible(d, <{role}>)"
        if action in CHANNEL_FIND_ACTION_ROLES:
            call += ".click()"
        return [call, "time.sleep(1)"]

    obj_name = step.get("object") or ""
    node = saved_objects.get(obj_name)
    if node is None:
        # 객체 관리에서 지워졌거나 이름이 안 맞으면 실제 셀렉터를 만들 수 없으니
        # 눈에 띄게 표시만 해둡니다.
        return [f"# ⚠️ 객체 {obj_name!r}을(를) 찾을 수 없습니다 (객체 관리에서 삭제되었을 수 있음)"]

    sel = _selector_code(node)

    if action == "find_object":
        # resourceId만으로는 화면을 구분 못 할 수 있어(공용 툴바 타이틀뷰 등)
        # click_if_missing과 같은 이유로 저장된 조건을 전부 합친 셀렉터를 씁니다.
        state_sel = _state_selector_code(node)
        return [f"{state_sel}.wait(timeout=1.5)  # 찾기(클릭 안 함)", "time.sleep(1)"]

    if action == "wait_activity":
        target_activity = node.get("activity") or ""
        timeout = value if value else "10"
        return [
            f"_deadline = time.time() + {timeout}",
            f"while d.app_current().get('activity') != {target_activity!r}:",
            "    if time.time() >= _deadline:",
            "        raise RuntimeError('화면이 나타나지 않았습니다')",
            "    time.sleep(0.5)",
            "time.sleep(1)",
        ]

    if action == "check_matches_my_info":
        field = value or "name"
        field_label = MY_INFO_FIELDS.get(field, field)
        return [
            "_my_name, _my_number = FileManager.parse_my_info_parts(FileManager.pull_profile_xml(d.serial))",
            f"assert {sel}.get_text() == _my_{field}  # {field_label}(XML)",
            "time.sleep(1)",
        ]

    if action == "check_text":
        expected = node.get("text") or ""
        return [f"assert {sel}.get_text() == {expected!r}", "time.sleep(1)"]

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


def _get_node(saved_objects, obj_name):
    return saved_objects.get(obj_name) if obj_name else None


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
    """resourceId 앞부분이 곧 패키지명이라, 있으면 그걸 최우선으로 씁니다.
    저장해둔 package 필드보다 이쪽을 더 믿는 이유는, 그 필드가 캡처 당시
    d.app_current()로 읽은 값이라 기기에 따라 틀린 값(예: 실제론 MCPTT
    화면인데 엉뚱한 다른 앱을 보고하는 경우)이 저장돼 있을 수 있기 때문입니다.
    resourceId가 없는 객체(desc/className만으로 저장된 아이콘 등)만 저장해둔
    package 필드로 대체합니다."""
    resource_id = node.get("resource_id") or ""
    if ":id/" in resource_id:
        return resource_id.split(":id/", 1)[0]
    return node.get("package") or None


def ensure_object_visible(d, node, max_attempts=8, build_selector=selector):
    """클릭/입력 대상 요소가 지금 화면에 실제로 있는지 먼저 확인합니다. 다른
    화면에 있어서(activity가 안 떠 있어서) 안 보이면 back 키를 눌러보다가,
    그래도 안 보이면(엉뚱한 앱으로 나가버린 경우) 패키지를 다시 실행해 찾아갑니다.
    activity를 문자열로 비교하지 않고 '요소가 보이는지'로 직접 판단하기 때문에
    activity 정보 없이 저장된 예전 객체도 그대로 동작합니다.
    build_selector로 selector() 대신 _state_selector()(resourceId/text/desc를
    전부 같이 보는 조건)를 넘기면, resourceId만으로는 화면을 구분 못 하는
    경우(예: 공용 툴바 타이틀뷰)도 정확히 그 화면인지 확인할 수 있습니다."""
    sel = build_selector(d, node)
    if sel.wait(timeout=1.5):
        return sel

    package = _infer_package(node)
    for attempt in range(max_attempts):
        # d.app_current()는 기기/ROM에 따라 실제 화면과 다른 값을 계속 보고하는
        # 경우가 있습니다(예: 실제로는 MCPTT 화면인데 갤러리 앱이 떠 있다고 계속
        # 우김). 이 값을 매 시도마다 그대로 믿고 back이냐 app_start냐를 고르면,
        # 그런 기기에서는 매번 app_start만 불려서(이미 떠 있는 앱을 포그라운드로
        # 다시 올리기만 할 뿐 화면 자체는 안 바뀜) back이 단 한 번도 안 눌리는
        # 채로 그냥 실패해버립니다. 그래서 앞쪽 절반은 app_current()를 아예 안
        # 보고 무조건 back으로 밀어붙이고, 그래도 못 찾은 뒤쪽 절반에서만
        # app_current()를 참고해 정말 다른 앱으로 나가버린 경우를 다시 살립니다.
        if package and attempt >= max_attempts // 2 and d.app_current().get("package") != package:
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


def execute_step(d, saved_objects, step, channel_roles=None, uuid=None, my_info_cache=None):
    """스텝 하나를 실제로 단말에 실행합니다. 실패하면 예외를 던집니다.
    channel_roles({역할명: 실제채널명})는 CHANNEL_FIND_ACTION_ROLES의 "찾기" 액션이
    어떤 채널/그룹을 눌러야 하는지 알아내는 데 씁니다.
    uuid/my_info_cache는 check_matches_my_info가 단말 XML에서 이름/번호를 읽는 데
    씁니다(캐시를 넘기면 시나리오 한 번 실행에서 여러 스텝이 이 동작을 써도 XML을
    한 번만 가져옵니다)."""
    action = step["action"]
    value = step.get("value") or ""
    _label, needs_object, _needs_value, _placeholder, needs_object2 = ACTION_META[action]

    if action == "back":
        d.press("back")
        time.sleep(1)
        return

    if action in CHANNEL_FIND_ACTION_ROLES or action in CHANNEL_FIND_NO_CLICK_ACTION_ROLES:
        # 캡처해둔 객체가 아니라, 지금 프로젝트 창에서 지정된 실제 채널/그룹명으로
        # 곧바로 화면을 찾습니다(스크롤 포함, back으로 목록 화면까지 찾아가는 것도
        # 포함). *_only 액션이면 찾기만 하고 클릭은 안 합니다.
        is_click = action in CHANNEL_FIND_ACTION_ROLES
        role = CHANNEL_FIND_ACTION_ROLES.get(action) or CHANNEL_FIND_NO_CLICK_ACTION_ROLES.get(action)
        channel_name = (channel_roles or {}).get(role)
        if not channel_name:
            raise RuntimeError(f"{role}이 지정되지 않았습니다 (프로젝트 창에서 먼저 채널을 골라주세요)")
        sel = ensure_channel_visible(d, channel_name)
        if is_click:
            sel.click()
        time.sleep(1)
        return

    if action == "click_if_missing":
        # 확인 객체(원하는 상태를 나타냄)는 '있으면 그만, 없으면 문제'라
        # ensure_object_visible처럼 back/앱 재실행까지 시도하며 찾지 않고,
        # 지금 화면 기준으로 가볍게만 확인합니다(없는 게 정상적인 결과일 수
        # 있어서). 없을 때만 클릭할 객체를 찾아 누릅니다.
        obj_name = step.get("object")
        obj2_name = step.get("object2")
        node = _get_node(saved_objects, obj_name)
        node2 = _get_node(saved_objects, obj2_name)
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

    if action == "wait_activity":
        # 버튼 등 특정 객체가 아니라 Activity 이름으로 화면 전환 자체를 기다립니다.
        # 객체 자체를 찾거나 클릭하지 않으므로, 아래 공통 sel(=ensure_object_visible)
        # 단계를 타지 않고 여기서 바로 끝냅니다.
        obj_name = step.get("object")
        node = _get_node(saved_objects, obj_name)
        if node is None:
            raise RuntimeError(f"객체 '{obj_name}'을(를) 찾을 수 없습니다 (객체 관리에서 삭제되었을 수 있음)")
        target_activity = node.get("activity")
        if not target_activity:
            raise RuntimeError(
                f"'{obj_name}'에는 저장된 화면(Activity) 정보가 없습니다. "
                "객체 관리에서 이 객체를 다시 캡처해 저장해주세요."
            )
        timeout = float(value) if value else 10.0
        deadline = time.time() + timeout
        current_activity = ""
        while True:
            current_activity = d.app_current().get("activity", "")
            if current_activity == target_activity:
                break
            if time.time() >= deadline:
                raise RuntimeError(
                    f"화면이 나타나지 않았습니다 (기대: '{target_activity}' / 현재: '{current_activity}')"
                )
            time.sleep(0.5)
        time.sleep(1)
        return

    sel = None
    if needs_object:
        obj_name = step.get("object")
        node = _get_node(saved_objects, obj_name)
        if node is None:
            raise RuntimeError(f"객체 '{obj_name}'을(를) 찾을 수 없습니다 (객체 관리에서 삭제되었을 수 있음)")
        if action == "find_object":
            # 화면을 구분하는 게 목적이라, resourceId 하나만 보면 안 됩니다(예:
            # 툴바 타이틀뷰는 화면마다 resourceId는 같고 text만 바뀌는 경우가
            # 많아서, resourceId만 보면 아무 화면에서나 "이미 있음"으로 오판해
            # back을 한 번도 안 누르고 바로 통과해버립니다). 저장해둔 조건
            # (resourceId/text/desc)을 전부 같이 봐서 정확히 그 화면인지 확인합니다.
            sel = ensure_object_visible(d, node, build_selector=_state_selector)
        elif action in (
            "click", "long_click", "set_text", "check_same", "toggle_state",
            "check_matches_my_info", "check_text",
        ):
            # 대상 화면이 안 떠 있으면 back/앱 재실행으로 찾아간 뒤 클릭/입력합니다.
            sel = ensure_object_visible(d, node)
        else:
            # wait_exists는 자기 타임아웃으로 로딩을 기다리는 게 목적이라
            # 여기서 먼저 back을 눌러버리면 오히려 방해가 됩니다.
            sel = selector(d, node)

    sel2 = None
    if needs_object2:
        obj2_name = step.get("object2")
        node2 = _get_node(saved_objects, obj2_name)
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
    elif action == "check_text":
        # 다른 객체가 아니라, 이 객체를 캡처할 때 같이 저장해둔 text 값과 비교합니다.
        expected = node.get("text") or ""
        if not expected:
            raise RuntimeError(
                f"'{step.get('object')}'에는 저장된 text 값이 없습니다 "
                "(아이콘처럼 text 없이 캡처된 객체일 수 있음)."
            )
        actual = sel.get_text() or ""
        if actual != expected:
            raise RuntimeError(
                f"'{step.get('object')}' text가 다릅니다 (화면: '{actual}' / 저장된 값: '{expected}')"
            )
    elif action == "check_matches_my_info":
        # 화면 객체 값을, 저장해둔 객체가 아니라 단말 XML(user_profile.xml)에서
        # 방금 읽은 단말 이름/번호와 비교합니다.
        field = (value or "name").strip().lower()
        name, number = _get_my_info(uuid, my_info_cache)
        expected = name if field == "name" else number
        actual = sel.get_text() or ""
        if actual != expected:
            raise RuntimeError(
                f"'{step.get('object')}' 값이 단말 정보와 다릅니다 "
                f"(화면: '{actual}' / {MY_INFO_FIELDS.get(field, field)}: '{expected}')"
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
    elif action == "find_object":
        # ensure_object_visible(위)에서 이미 화면을 다 찾았으니 여기선 할 일이
        # 없습니다 — 클릭/입력 없이 그 화면에 도착한 것 자체가 목적입니다.
        pass

    time.sleep(1)


def _get_my_info(uuid, cache):
    """단말 XML(user_profile.xml)에서 (단말 이름, 단말 번호)를 읽어옵니다. cache가
    주어지면(dict) 그 안에 결과를 담아둬, 같은 시나리오 실행 안에서 이 동작을
    여러 번 써도 adb pull은 한 번만 합니다."""
    if cache is not None and "info" in cache:
        return cache["info"]
    path = FileManager.pull_profile_xml(uuid)
    if not path:
        raise RuntimeError("단말에서 XML 정보를 가져오지 못했습니다.")
    info = FileManager.parse_my_info_parts(path)
    if cache is not None:
        cache["info"] = info
    return info


def run_scenario(uuid, project, steps, on_log=print, title=None, channel_roles=None):
    """단말(uuid)에 시나리오 스텝들을 순서대로 실행합니다.
    첫 실패에서 멈추며, 끝까지 성공하면 True를 돌려줍니다.
    channel_roles는 프로젝트 창의 "채널 지정"에서 고른 {역할명: 실제채널명} 매핑으로,
    "...찾기(클릭)" 액션들이 어떤 채널/그룹을 눌러야 하는지 알아내는 데 씁니다."""
    try:
        import uiautomator2 as u2

        d = u2.connect(uuid)
    except Exception as e:
        on_log(f"❌ 단말 연결 실패: {e}")
        return False

    saved_objects = object_store.list_objects(project)
    my_info_cache = {}
    head = f"▶ 시나리오 실행 시작 ({len(steps)}개 스텝)"
    if title:
        head = f"▶ '{title}' 실행 시작 ({len(steps)}개 스텝)"
    on_log(head)

    for i, step in enumerate(steps, 1):
        label = step_label(step)
        try:
            execute_step(d, saved_objects, step, channel_roles, uuid, my_info_cache)
            on_log(f"  {i}. {label}  ✅")
        except Exception as e:
            on_log(f"  {i}. {label}  ❌ {e}")
            on_log("⏹ 오류가 발생해 실행을 중단했습니다.")
            return False

    on_log("✅ 시나리오 실행 완료")
    return True
