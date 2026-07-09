class BaseAutomation:
    def run(self, d, env):
        raise NotImplementedError("프로젝트별 run 메서드를 구현해야 합니다.")