import importlib
import inspect
import keyword
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetricsF
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

import object_store
import project_config_store
import scenario_runner
import scenario_store
from code_editor import CodeEditor
from device_panel import PROJECT_HANDLERS, SCENARIO_LABELS
from ui_common import (
    NavListButton,
    Navy,
    clear_layout,
    kfont,
    navy_button,
    navy_card,
    navy_card_header,
    navy_hline,
    navy_input_css,
    navy_mono_font,
    navy_page_css,
    navy_page_header,
    navy_section_header,
    styled,
)


class ScenarioLibraryPage(QWidget):
    """프로젝트별로 저장된 시나리오(핸들러 메서드)를 관리하는 화면.
    맨 위 페이지 헤더(제목 + 프로젝트 드롭다운 + 현재 위치) 아래로 [시나리오 목록] -
    [코드 보기/수정] 두 칸이고, 시나리오를 고르면 오른쪽에 실제 소스 코드가 뜨고
    편집 후 저장하면 해당 config_handlers 파일에 바로 반영됩니다.

    보이는 스타일은 ui_common.Navy 토큰(밝은 회청색 바닥 + 흰 카드 + 네이비 액센트)을
    씁니다. 페이지 배경은 #scenarioInterface 선택자로 이 위젯만 칠합니다(선택자 없이
    주면 카드 안 자식 위젯까지 같이 칠해집니다)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("scenarioInterface")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # 자식까지 물들이지 않도록 이 위젯 하나만 가리키는 id 선택자로 바닥색을 칠합니다.
        self.setStyleSheet(navy_page_css("scenarioInterface"))

        self._scenario_buttons = {}
        self._current_project = None
        self._current = None  # (module, handler_cls, method_name, file_path, start_line, line_count)
        self._current_builder_scenario_name = None
        # 객체 기반(시나리오 작성) 시나리오를 편집 모드로 들어간 상태인지. 이 상태에서
        # 저장하면 스텝 목록이 아니라 실제 코드(핸들러 메서드)로 전환됩니다.
        self._detaching_builder_scenario = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)
        outer.addWidget(self._build_page_header())

        body = QHBoxLayout()
        body.setSpacing(14)
        outer.addLayout(body, 1)

        # 프로젝트를 고르면 _on_project_selected()가 시나리오 목록/코드 패널의 위젯을
        # 바로 건드리므로, 두 패널을 먼저 다 만든 뒤에 드롭다운을 채웁니다(채우면서
        # 첫 프로젝트가 자동 선택됩니다).
        self._scenario_list_card, self._scenario_list_layout = self._build_scenario_list()
        body.addWidget(self._scenario_list_card, 3)
        body.addWidget(self._build_code_panel(), 7)

        self._refresh_project_combo()

    # ---------- 공통: 카드 껍데기 / 카드 헤더 ----------
    @staticmethod
    def _build_card():
        return navy_card()

    # ---------- 페이지 헤더 ----------
    def _build_page_header(self):
        header, self._breadcrumb = navy_page_header(
            "시나리오",
            "프로젝트별로 저장된 시나리오 코드를 확인하고 바로 수정합니다.",
            actions=[self._build_project_combo()],
        )
        return header

    def _build_project_combo(self):
        """제목 "시나리오" 바로 옆에 붙는 프로젝트 선택 드롭다운.
        예전에는 왼쪽에 프로젝트 목록 카드가 한 칸을 차지했지만, 다른 화면들(객체
        관리/시나리오 작성)과 같은 방식으로 제목 줄로 옮겼습니다."""
        self._project_combo = QComboBox()
        self._project_combo.setFixedHeight(32)
        self._project_combo.setMinimumWidth(200)
        self._project_combo.setFont(kfont(10))
        self._project_combo.setStyleSheet(navy_input_css())
        self._project_combo.currentIndexChanged.connect(self._on_project_combo_changed)
        return self._project_combo

    def _refresh_project_combo(self):
        """등록된 프로젝트로 드롭다운을 다시 채웁니다. 국내/해외가 섞여 있으면 항목
        앞에 지역을 붙여 구분합니다(드롭다운에는 구분선을 넣을 자리가 없습니다).
        고르고 있던 프로젝트는 유지하고, 없으면 첫 번째를 자동으로 고릅니다."""
        self._project_combo.blockSignals(True)
        self._project_combo.clear()
        groups = project_config_store.group_projects_by_region(list(PROJECT_HANDLERS.keys()))
        for group_label, proj_names in groups:
            for proj_name in proj_names:
                label = f"[{group_label}] {proj_name}" if group_label else proj_name
                self._project_combo.addItem(label, proj_name)
        idx = self._project_combo.findData(self._current_project)
        self._project_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._project_combo.blockSignals(False)

        selected = self._project_combo.currentData()
        if selected and selected != self._current_project:
            self._on_project_selected(selected)

    def _on_project_combo_changed(self, _index):
        proj_name = self._project_combo.currentData()
        if proj_name:
            self._on_project_selected(proj_name)

    def select_project(self, project_name):
        """런처 메뉴처럼 바깥에서 특정 프로젝트를 골라 이 화면을 열 때 씁니다
        (ui_logic.show_as_left_card가 있으면 불러줍니다).

        이미 그 프로젝트가 골라져 있으면 setCurrentIndex는 시그널을 안 보내므로,
        어느 쪽이든 목록이 새로 채워지도록 _on_project_selected를 직접 부릅니다."""
        idx = self._project_combo.findData(project_name)
        if idx < 0:
            return False
        self._project_combo.blockSignals(True)
        self._project_combo.setCurrentIndex(idx)
        self._project_combo.blockSignals(False)
        self._on_project_selected(project_name)
        return True

    def _update_breadcrumb(self, scenario=None):
        parts = [p for p in (self._current_project, scenario) if p]
        self._breadcrumb.setText("  ›  ".join(parts))

    # ---------- 왼쪽: 선택한 프로젝트의 시나리오 목록 ----------
    def _build_scenario_list(self):
        card = self._build_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(4)

        btn_refresh = navy_button(
            "", kind="ghost", height=26, icon_name="fa5s.sync-alt", icon_size=12
        )
        btn_refresh.setFixedWidth(30)
        btn_refresh.setToolTip("시나리오 목록 새로고침")
        btn_refresh.clicked.connect(self._on_refresh_scenario_list_clicked)

        self._btn_copy_scenario = navy_button(
            "", kind="ghost", height=26, icon_name="fa5s.copy", icon_size=12
        )
        self._btn_copy_scenario.setFixedWidth(30)
        self._btn_copy_scenario.setToolTip(
            "선택한 시나리오를 다른 프로젝트로 복사 "
            "(같은 프로젝트를 고르면 이름을 바꿔 복제합니다)"
        )
        # 핸들러 코드 시나리오는 config_handlers 소스를 건드려야 해서 복사 대상이
        # 아닙니다. 스텝 목록 시나리오를 골랐을 때만 켭니다.
        self._btn_copy_scenario.setEnabled(False)
        self._btn_copy_scenario.clicked.connect(self._copy_selected_scenario)

        header, self._scenario_count = navy_card_header(
            "시나리오", badge=0, actions=[self._btn_copy_scenario, btn_refresh]
        )
        layout.addWidget(header)

        layout.addStretch(1)

        return card, layout

    def showEvent(self, event):
        super().showEvent(event)
        # 다른 화면(특히 "프로젝트 관리"/"시나리오 작성")에서 프로젝트를 추가하거나
        # 시나리오를 추가/삭제하고 돌아왔을 때도 목록이 최신 상태로 보이도록 이 페이지가
        # 다시 보일 때마다 새로고침합니다.
        self._refresh_project_combo()
        if self._current_project:
            self._on_project_selected(self._current_project)

    def _on_project_selected(self, proj_name):
        self._current_project = proj_name
        self._current_builder_scenario_name = None
        self._btn_copy_scenario.setEnabled(False)
        clear_layout(self._scenario_list_layout, keep=1)  # keep=1: 카드 헤더
        # clear_layout은 맨 끝의 stretch까지 같이 거두므로 바로 다시 깔아둡니다. 이걸 빼먹으면
        # 아래의 insertWidget(count()-1, ...)이 stretch가 아니라 마지막으로 넣은 항목 앞에
        # 계속 쌓이게 됩니다.
        self._scenario_list_layout.addStretch(1)
        self._scenario_buttons = {}
        self._show_code_placeholder("왼쪽에서 시나리오를 선택하세요.")

        module_name, class_name = PROJECT_HANDLERS[proj_name]
        handler_cls = None
        try:
            module = importlib.import_module(module_name)
            handler_cls = getattr(module, class_name)
        except Exception as e:
            self._scenario_list_layout.insertWidget(
                self._scenario_list_layout.count() - 1, self._build_warning_label(str(e))
            )

        group = QButtonGroup(self._scenario_list_card)
        group.setExclusive(True)

        method_names = []
        if handler_cls is not None:
            method_names = [
                name for name, value in vars(handler_cls).items()
                if not name.startswith("_") and callable(value)
            ]
            if method_names:
                self._scenario_list_layout.insertWidget(
                    self._scenario_list_layout.count() - 1, navy_section_header("핸들러")
                )
            for name in method_names:
                label = SCENARIO_LABELS.get(name, name)
                btn = NavListButton(label, height=32)
                btn.clicked.connect(
                    lambda checked=False, p=proj_name, n=name: self._on_scenario_selected(p, n)
                )
                group.addButton(btn)
                self._scenario_list_layout.insertWidget(self._scenario_list_layout.count() - 1, btn)
                self._scenario_buttons[name] = btn

        builder_scenarios = scenario_store.list_scenarios(proj_name)
        if builder_scenarios:
            self._scenario_list_layout.insertWidget(
                self._scenario_list_layout.count() - 1, navy_section_header("시나리오")
            )
            for name in builder_scenarios:
                btn = NavListButton(name, height=32)
                btn.clicked.connect(
                    lambda checked=False, p=proj_name, n=name: self._on_builder_scenario_selected(p, n)
                )
                group.addButton(btn)
                self._scenario_list_layout.insertWidget(self._scenario_list_layout.count() - 1, btn)
                self._scenario_buttons[f"__builder__{name}"] = btn

        self._scenario_count.setText(str(len(method_names) + len(builder_scenarios)))

        if not method_names and not builder_scenarios:
            self._scenario_list_layout.insertWidget(
                self._scenario_list_layout.count() - 1, self._build_empty_label("등록된 시나리오가 없습니다.")
            )

    def _on_refresh_scenario_list_clicked(self):
        if self._current_project:
            self._on_project_selected(self._current_project)

    @staticmethod
    def _unique_scenario_name(name, existing):
        """이름 (복사본) -> 이름 (복사본 2) ... 순으로 안 겹치는 이름을 만듭니다."""
        candidate = f"{name} (복사본)"
        i = 2
        while candidate in existing:
            candidate = f"{name} (복사본 {i})"
            i += 1
        return candidate

    def _copy_selected_scenario(self):
        """목록에서 고른 시나리오를 다른 프로젝트로 복사합니다.
        같은 프로젝트를 고르면 새 이름을 받아 그 자리에서 복제합니다.

        스텝 목록으로 만든 시나리오(시나리오 작성 화면)만 대상입니다. 핸들러 코드
        시나리오는 config_handlers 소스 파일을 고쳐야 해서 여기서 다루지 않습니다."""
        name = self._current_builder_scenario_name
        if not self._current_project or not name:
            QMessageBox.warning(
                self, "시나리오 미선택",
                "복사할 시나리오를 '시나리오' 묶음에서 먼저 선택해주세요.\n"
                "(핸들러 코드 시나리오는 복사할 수 없습니다.)",
            )
            return
        steps = scenario_store.list_scenarios(self._current_project).get(name)
        if steps is None:
            QMessageBox.warning(self, "시나리오 없음", f"{name!r}을(를) 찾을 수 없습니다.")
            return

        targets = list(PROJECT_HANDLERS)
        current_idx = targets.index(self._current_project) if self._current_project in targets else 0
        target, ok = QInputDialog.getItem(
            self, "대상 프로젝트 선택",
            f"{name!r}을(를) 어느 프로젝트로 복사할까요?\n"
            "(지금 프로젝트를 고르면 이름을 바꿔 복제합니다.)",
            targets, current_idx, False,
        )
        if not ok or not target:
            return

        existing = scenario_store.list_scenarios(target)
        new_name = name
        if target == self._current_project:
            new_name, ok = QInputDialog.getText(
                self, "복사본 이름", "새 시나리오 이름:",
                text=self._unique_scenario_name(name, existing),
            )
            new_name = (new_name or "").strip()
            if not ok or not new_name:
                return
        if new_name in existing:
            ret = QMessageBox.question(
                self, "이름 중복",
                f"{target!r} 프로젝트에 이미 있는 {new_name!r}을(를) 덮어쓸까요?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return

        # 폴더 구성은 프로젝트마다 따로라, 대상 프로젝트에 같은 이름의 폴더가 있을
        # 때만 그 폴더로 넣습니다(없는 폴더를 대신 만들지는 않고 기본 폴더로).
        folder = scenario_store.scenario_folder(self._current_project, name)
        target_folder = folder if folder in scenario_store.list_folders(target) else None
        scenario_store.save_scenario(
            target, new_name, [dict(step) for step in steps], folder=target_folder
        )

        self._on_project_selected(self._current_project)
        QMessageBox.information(
            self, "복사 완료",
            f"{name!r}을(를) {target!r} 프로젝트의 {new_name!r}(으)로 복사했습니다.",
        )

    @staticmethod
    def _find_class_body_end(lines, class_name):
        """lines(파일 전체 줄 목록)에서 class_name의 본문이 끝나는 삽입 지점(줄 인덱스)을 찾습니다.
        클래스 선언 다음부터 들여쓰기가 없는(=클래스 밖으로 나간) 첫 줄 앞에 삽입하고,
        파일 끝까지 클래스 본문이면 파일 끝에 삽입합니다."""
        class_re = re.compile(rf"^class\s+{re.escape(class_name)}\b")
        in_class = False
        for i, line in enumerate(lines):
            if class_re.match(line):
                in_class = True
                continue
            if in_class:
                stripped = line.rstrip("\n")
                if stripped and not stripped[0].isspace():
                    return i
        return len(lines)

    @staticmethod
    def _build_warning_label(message):
        """핸들러 로드 실패처럼 문제가 생겼을 때 목록 자리에 끼워 넣는 인라인 경고 박스."""
        lbl = QLabel(message)
        lbl.setFont(kfont(10))
        lbl.setWordWrap(True)
        return styled(
            lbl,
            f"background-color:{Navy.danger_soft}; color:{Navy.danger}; border:none; "
            f"border-left:3px solid {Navy.danger}; border-radius:{Navy.radius_sm}px; padding:8px 10px;",
        )

    @staticmethod
    def _build_empty_label(message):
        """아직 아무것도 없다는 빈 상태 안내. 경고가 아니라 옅은 점선 박스로만 보여줍니다."""
        lbl = QLabel(message)
        lbl.setFont(kfont(10))
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignCenter)
        return styled(
            lbl,
            f"background-color:{Navy.surface_alt}; color:{Navy.text_muted}; "
            f"border:1px dashed {Navy.border_strong}; border-radius:{Navy.radius_sm}px; padding:14px 10px;",
        )

    # ---------- 오른쪽: 코드 보기 / 수정 ----------
    def _build_code_panel(self):
        card = self._build_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(8)
        self._code_title_lbl = QLabel("코드")
        self._code_title_lbl.setFont(kfont(14, True))
        self._code_title_lbl.setStyleSheet(f"color:{Navy.navy};")
        header.addWidget(self._code_title_lbl)

        # 제목 바로 옆의 연필 아이콘: 평소엔 코드가 읽기 전용이다가, 눌러야 고칠 수
        # 있게 됩니다(실수로 건드리는 것 방지). 객체 기반 시나리오는 여기서 편집을
        # 시작하면 저장할 때 실제 코드로 전환됩니다.
        self._btn_edit_code = navy_button(
            "", kind="ghost", height=26, icon_name="fa5s.pen", icon_size=12
        )
        self._btn_edit_code.setFixedWidth(30)
        self._btn_edit_code.setToolTip("코드 수정하기")
        self._btn_edit_code.clicked.connect(self._on_edit_code_clicked)
        self._btn_edit_code.setVisible(False)
        header.addWidget(self._btn_edit_code)

        header.addStretch(1)

        self._btn_save = navy_button("저장", kind="primary", height=32, icon_name="fa5s.check")
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._save_current_scenario)
        header.addWidget(self._btn_save)
        layout.addLayout(header)
        layout.addWidget(navy_hline())

        self._code_edit = CodeEditor(object_provider=self._saved_objects_for_current_project)
        code_font = navy_mono_font(11)
        self._code_edit.setFont(code_font)
        # 파이썬 코드라 탭 폭을 공백 4칸에 맞춰둡니다(기본값은 8칸이라 들여쓰기가 어긋나 보입니다).
        self._code_edit.setTabStopDistance(4 * QFontMetricsF(code_font).horizontalAdvance(" "))
        self._code_edit.setStyleSheet(
            f"QPlainTextEdit {{ background-color:{Navy.surface_alt}; color:{Navy.text}; "
            f"border:1px solid {Navy.border}; border-radius:{Navy.radius_sm}px; padding:12px; "
            f"selection-background-color:#D6E2F7; selection-color:{Navy.navy}; }}"
            f"QPlainTextEdit:focus {{ border:1px solid {Navy.accent}; }}"
            # 전역 QSS(ui_logic._global_qss)가 스크롤바를 예전 라벤더 색으로 칠하기 때문에,
            # 이 편집기 안에서만 네이비 톤으로 다시 덮어씁니다.
            f"QScrollBar:vertical {{ background:transparent; width:10px; margin:6px 4px 6px 0; }}"
            f"QScrollBar::handle:vertical {{ background:{Navy.border_strong}; border-radius:5px; min-height:28px; }}"
            f"QScrollBar::handle:vertical:hover {{ background:{Navy.text_muted}; }}"
            f"QScrollBar:horizontal {{ background:transparent; height:10px; margin:0 6px 4px 6px; }}"
            f"QScrollBar::handle:horizontal {{ background:{Navy.border_strong}; border-radius:5px; min-width:28px; }}"
            f"QScrollBar::handle:horizontal:hover {{ background:{Navy.text_muted}; }}"
            f"QScrollBar::add-line, QScrollBar::sub-line {{ width:0; height:0; }}"
            f"QScrollBar::add-page, QScrollBar::sub-page {{ background:none; }}"
        )
        self._code_edit.setPlainText(
            "왼쪽에서 프로젝트와 시나리오를 선택하세요.\n"
            "(편집 중 Ctrl+Space: 객체 관리에 저장해둔 객체 이름 자동완성)"
        )
        self._code_edit.setReadOnly(True)
        layout.addWidget(self._code_edit, 1)

        # 파일 경로나 저장 결과를 보여주는 아래쪽 상태줄. 경로가 잘 읽히도록 고정폭 글꼴을 씁니다.
        self._status_lbl = QLabel("")
        self._status_lbl.setFont(navy_mono_font(9))
        self._status_lbl.setStyleSheet(f"color:{Navy.text_muted};")
        layout.addWidget(self._status_lbl)

        return card

    def _saved_objects_for_current_project(self):
        if not self._current_project:
            return {}
        return object_store.list_objects(self._current_project)

    def _show_code_placeholder(self, message):
        self._current = None
        self._current_builder_scenario_name = None
        self._detaching_builder_scenario = False
        self._btn_edit_code.setVisible(False)
        self._code_title_lbl.setText("코드")
        self._code_edit.setReadOnly(True)
        self._code_edit.setPlainText(message)
        self._btn_save.setEnabled(False)
        self._status_lbl.setText("")
        self._update_breadcrumb()

    def _on_scenario_selected(self, proj_name, method_name):
        self._current_builder_scenario_name = None
        self._detaching_builder_scenario = False
        self._btn_copy_scenario.setEnabled(False)

        module_name, class_name = PROJECT_HANDLERS[proj_name]
        try:
            module = importlib.import_module(module_name)
            handler_cls = getattr(module, class_name)
            method = getattr(handler_cls, method_name)
            source_lines, start_line = inspect.getsourcelines(method)
            file_path = inspect.getsourcefile(method)
        except Exception as e:
            self._show_code_placeholder(f"⚠️ 코드를 불러오지 못했습니다: {e}")
            return

        label = SCENARIO_LABELS.get(method_name, method_name)
        self._current = (module, handler_cls, method_name, file_path, start_line, len(source_lines))
        title = f"{method_name}()" if label == method_name else f"{label}  ·  {method_name}()"
        self._code_title_lbl.setText(title)
        self._update_breadcrumb(label)
        self._code_edit.setPlainText("".join(source_lines))
        self._code_edit.setReadOnly(True)
        self._btn_edit_code.setVisible(True)
        self._btn_save.setEnabled(False)
        self._status_lbl.setText(file_path)

    def _builder_scenario_body_lines(self, name):
        """스텝 목록을, execute_step()과 같은 동작을 하는 실제 코드 줄 목록으로
        바꿉니다(주석 없이 순수 코드만 — 이 화면에서 편집을 시작할 때/코드 미리보기
        둘 다에서 씁니다)."""
        saved_objects = self._saved_objects_for_current_project()
        steps = scenario_store.list_scenarios(self._current_project).get(name) or []
        lines = []
        for step in steps:
            lines.extend(scenario_runner.step_real_code_lines(step, saved_objects))
            lines.append("")
        return lines

    def _on_builder_scenario_selected(self, proj_name, name):
        steps = scenario_store.list_scenarios(proj_name).get(name)
        if steps is None:
            self._show_code_placeholder(f"⚠️ 시나리오를 찾을 수 없습니다: {name}")
            return

        self._current = None  # 코드 파일이 아니라 "저장"으로 덮어쓸 대상이 없음
        self._current_builder_scenario_name = name
        self._detaching_builder_scenario = False
        self._btn_copy_scenario.setEnabled(True)
        self._code_title_lbl.setText(f"{name}  ·  시나리오 작성")
        self._update_breadcrumb(name)
        preview_lines = [
            f"# '{name}'은 시나리오 작성 화면에서 객체 기반으로 만든 시나리오입니다.",
            "# 연필 아이콘(편집)을 누르면 이 코드를 직접 고칠 수 있습니다 — 저장하면",
            "# 실제 코드(핸들러 메서드)로 전환되고, 이 스텝 목록 저장본은 지워집니다.",
            "",
        ] + self._builder_scenario_body_lines(name)
        self._code_edit.setPlainText("\n".join(preview_lines))
        self._code_edit.setReadOnly(True)
        self._btn_edit_code.setVisible(True)
        self._btn_save.setEnabled(False)
        self._status_lbl.setText("연필 아이콘(편집)을 누르면 직접 고칠 수 있습니다(저장 시 실제 코드로 전환).")

    def _on_edit_code_clicked(self):
        if self._current is None and self._current_builder_scenario_name:
            ret = QMessageBox.question(
                self, "실제 코드로 전환",
                f"'{self._current_builder_scenario_name}'은 스텝 목록으로 만든 시나리오입니다.\n"
                "지금 편집을 시작하고 저장하면 실제 코드(핸들러 메서드)로 전환되고, "
                "스텝 목록 저장본은 삭제됩니다. 계속할까요?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return
            self._detaching_builder_scenario = True
            body = self._builder_scenario_body_lines(self._current_builder_scenario_name)
            self._code_edit.setPlainText("\n".join(body).strip("\n") or "pass")
            self._status_lbl.setText("편집 중입니다 — 저장하면 실제 코드로 전환됩니다.")

        self._code_edit.setReadOnly(False)
        self._btn_save.setEnabled(True)
        self._code_edit.setFocus()

    @staticmethod
    def _make_method_name(name, existing):
        """자유 텍스트인 시나리오 이름을, 핸들러 파일에 넣을 수 있는 유효하고 겹치지
        않는 파이썬 식별자로 바꿉니다."""
        base = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in name.strip())
        base = re.sub(r"_+", "_", base).strip("_")
        if not base or base[0].isdigit():
            base = f"scenario_{base}" if base else "scenario"
        if keyword.iskeyword(base):
            base = f"{base}_"
        candidate = base
        n = 2
        while candidate in existing:
            candidate = f"{base}_{n}"
            n += 1
        return candidate

    def _save_current_scenario(self):
        if self._current is not None:
            self._save_code_based_scenario()
        elif self._detaching_builder_scenario and self._current_builder_scenario_name:
            self._save_detached_builder_scenario()

    def _save_detached_builder_scenario(self):
        """편집을 시작한 객체 기반 시나리오를, 지금 코드 박스에 있는 내용 그대로
        핸들러 파일에 새 메서드로 적어 넣고(기존 '시나리오 추가'와 같은 삽입 방식),
        스텝 목록 저장본은 지웁니다. 이후로는 이 시나리오가 '핸들러' 쪽 코드형
        시나리오로 보입니다."""
        proj_name = self._current_project
        name = self._current_builder_scenario_name
        if not proj_name or not name:
            return

        module_name, class_name = PROJECT_HANDLERS[proj_name]
        try:
            module = importlib.import_module(module_name)
            handler_cls = getattr(module, class_name)
        except Exception as e:
            QMessageBox.warning(self, "핸들러 로드 실패", str(e))
            return

        existing = {
            n for n, value in vars(handler_cls).items()
            if not n.startswith("_") and callable(value)
        }
        method_name = self._make_method_name(name, existing)

        file_path = inspect.getsourcefile(handler_cls)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as e:
            QMessageBox.warning(self, "파일 열기 실패", str(e))
            return

        body_lines = self._code_edit.toPlainText().splitlines() or ["pass"]
        indented = "\n".join(f"        {line}" if line.strip() else "" for line in body_lines)
        stub = f"\n    def {method_name}(self, d, log_console=None):\n{indented}\n"

        insert_at = self._find_class_body_end(lines, class_name)
        lines[insert_at:insert_at] = stub.splitlines(keepends=True)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            importlib.reload(module)
        except Exception as e:
            QMessageBox.warning(self, "저장 실패", str(e))
            return

        scenario_store.delete_scenario(proj_name, name)
        self._detaching_builder_scenario = False
        self._on_project_selected(proj_name)
        self._on_scenario_selected(proj_name, method_name)
        self._status_lbl.setText(f"✅ 실제 코드로 전환되어 저장됨: {file_path}")

    def _save_code_based_scenario(self):
        module, handler_cls, method_name, file_path, start_line, line_count = self._current

        new_text = self._code_edit.toPlainText()
        if not new_text.endswith("\n"):
            new_text += "\n"

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = new_text.splitlines(keepends=True)
            lines[start_line - 1:start_line - 1 + line_count] = new_lines
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            importlib.reload(module)
        except Exception as e:
            QMessageBox.warning(self, "저장 실패", f"{e}")
            return

        self._status_lbl.setText(f"✅ 저장됨: {file_path}")
        # 방금 저장한 내용 기준으로 시작줄/줄수가 바뀌었을 수 있으니 다시 읽어와 최신 상태로 맞춥니다.
        proj_name = next((p for p, (m, c) in PROJECT_HANDLERS.items() if m == module.__name__), None)
        if proj_name:
            self._on_scenario_selected(proj_name, method_name)
