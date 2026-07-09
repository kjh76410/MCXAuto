import importlib

def get_handler(project_name):
    """프로젝트 이름을 받으면 해당 핸들러 클래스를 자동으로 찾아 인스턴스화합니다."""
    try:
        # project_name이 "CTB"라면 config_handlers.ctb_handler 모듈을 로드
        module_name = f"config_handlers.{project_name.lower()}_handler"
        module = importlib.import_module(module_name)
        
        # 'CTBHandler' 같은 클래스명을 자동으로 생성 (대문자 조합)
        class_name = f"{project_name.upper()}Handler"
        return getattr(module, class_name)()
    except Exception as e:
        print(f"❌ 핸들러 로드 실패 ({project_name}): {e}")
        return None