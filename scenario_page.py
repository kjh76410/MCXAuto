import importlib
import inspect
import keyword
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetricsF
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

import object_store
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
    navy_mono_font,
    navy_page_css,
    navy_page_header,
    navy_section_header,
    styled,
)


class ScenarioLibraryPage(QWidget):
    """프로젝트별로 저장된 시나리오(핸들러 메서드)를 관리하는 화면.
    맨 위 페이지 헤더(제목 + 현재 위치) 아래로 [프로젝트 목록] - [시나리오 목록] -
    [코드 보기/수정] 3단 구성이고, 시나리오를 고르면 오른쪽에 실제 소스 코드가 뜨고
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

        self._project_buttons = {}
        self._scenario_buttons = {}
        self._current_project = None
        self._current = None  # (module, handler_cls, method_name, file_path, start_line, line_count)
        self._current_builder_scenario_name = None
        # ui_logic.py가 채워주는 콜백: (project_name, scenario_name) -> None.
        # "시나리오 작성" 화면으로 전환해 해당 시나리오를 편집기에 불러오는 역할.
        self.on_edit_builder_scenario = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)
        outer.addWidget(self._build_page_header())

        body = QHBoxLayout()
        body.setSpacing(14)
        outer.addLayout(body, 1)

        # 프로젝트 목록을 마지막에 만드는 이유: 그 안에서 첫 프로젝트를 자동 선택하며
        # _on_project_selected()가 시나리오 목록/코드 패널의 위젯을 바로 건드리는데, 그
        # 위젯들은 아래 두 패널을 먼저 만들어야 존재합니다. 화면상 배치는 addWidget 순서
        # (project -> scenario list -> code)로 그대로 유지됩니다.
        self._scenario_list_card, self._scenario_list_layout = self._build_scenario_list()
        code_panel = self._build_code_panel()
        project_list = self._build_project_list()

        body.addWidget(project_list, 2)
        body.addWidget(self._scenario_list_card, 3)
        body.addWidget(code_panel, 7)

    # ---------- 공통: 카드 껍데기 / 카드 헤더 ----------
    @staticmethod
    def _build_card():
        return navy_card()

    # ---------- 페이지 헤더 ----------
    def _build_page_header(self):
        header, self._breadcrumb = navy_page_header(
            "시나리오", "프로젝트별로 저장된 시나리오 코드를 확인하고 바로 수정합니다."
        )
        return header

    def _update_breadcrumb(self, scenario=None):
        parts = [p for p in (self._current_project, scenario) if p]
        self._breadcrumb.setText("  ›  ".join(parts))

    # ---------- 1단: 저장된 프로젝트 목록 ----------
    def _build_project_list(self):
        self._project_list_card = self._build_card()
        layout = QVBoxLayout(self._project_list_card)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(4)

        header, self._project_count = navy_card_header("프로젝트", badge=0)
        layout.addWidget(header)

        self._project_list_layout = layout
        self._refresh_project_buttons()

        return self._project_list_card

    def _refresh_project_buttons(self):
        clear_layout(self._project_list_layout, keep=1)  # keep=1: 카드 헤더
        self._project_buttons = {}
        self._project_count.setText(str(len(PROJECT_HANDLERS)))
        group = QButtonGroup(self._project_list_card)
        group.setExclusive(True)
        for proj_name in PROJECT_HANDLERS:
            btn = NavListButton(proj_name, height=34)
            btn.clicked.connect(lambda checked=False, p=proj_name: self._on_project_selected(p))
            group.addButton(btn)
            self._project_list_layout.addWidget(btn)
            self._project_buttons[proj_name] = btn
        self._project_list_layout.addStretch(1)

        if self._current_project in self._project_buttons:
            self._project_buttons[self._current_project].setChecked(True)
        elif PROJECT_HANDLERS:
            first_project = next(iter(PROJECT_HANDLERS))
            self._project_buttons[first_project].setChecked(True)
            self._on_project_selected(first_project)

    # ---------- 2단: 선택한 프로젝트의 시나리오 목록 ----------
    def _build_scenario_list(self):
        card = self._build_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(4)

        header, self._scenario_count = navy_card_header("시나리오", badge=0)
        layout.addWidget(header)

        btn_add = navy_button("시나리오 추가", kind="primary", height=32, icon_name="fa5s.plus")
        btn_add.clicked.connect(self._on_add_scenario_clicked)
        layout.addWidget(btn_add)

        layout.addStretch(1)

        return card, layout

    def showEvent(self, event):
        super().showEvent(event)
        # 다른 화면(특히 "프로젝트 관리"/"시나리오 작성")에서 프로젝트를 추가하거나
        # 시나리오를 추가/삭제하고 돌아왔을 때도 목록이 최신 상태로 보이도록 이 페이지가
        # 다시 보일 때마다 새로고침합니다.
        self._refresh_project_buttons()
        if self._current_project:
            self._on_project_selected(self._current_project)

    def _on_project_selected(self, proj_name):
        self._current_project = proj_name
        clear_layout(self._scenario_list_layout, keep=2)  # keep=2: 카드 헤더 + "시나리오 추가" 버튼
        # clear_layout은 맨 끝의 stretch까지 같이 거두므로 바로 다시 깔아둡니다. 이걸 빼먹으면
        # 아래의 insertWidget(count()-1, ...)이 stretch가 아니라 "시나리오 추가" 버튼 앞에
        # 항목을 쌓게 되고(=버튼이 목록 맨 뒤로 밀림), 다음 갱신 때 keep=2 범위 밖으로
        # 밀려난 버튼이 통째로 삭제됩니다.
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

    def _on_add_scenario_clicked(self):
        proj_name = self._current_project
        if not proj_name:
            QMessageBox.warning(self, "프로젝트 미선택", "먼저 왼쪽에서 프로젝트를 선택해주세요.")
            return

        module_name, class_name = PROJECT_HANDLERS[proj_name]
        try:
            module = importlib.import_module(module_name)
            handler_cls = getattr(module, class_name)
        except Exception as e:
            QMessageBox.warning(self, "핸들러 로드 실패", str(e))
            return

        existing = {
            name for name, value in vars(handler_cls).items()
            if not name.startswith("_") and callable(value)
        }

        name, ok = QInputDialog.getText(self, "시나리오 추가", "새 시나리오의 메서드 이름 (영문/숫자/밑줄):")
        if not ok or not name:
            return
        name = name.strip()
        if not name.isidentifier() or keyword.iskeyword(name) or name.startswith("_"):
            QMessageBox.warning(self, "이름 오류", "영문/숫자/밑줄로 시작하는 유효한 파이썬 식별자를 입력해주세요 (밑줄로 시작 불가).")
            return
        if name in existing:
            QMessageBox.warning(self, "이름 중복", f"'{name}' 시나리오가 이미 있습니다.")
            return

        file_path = inspect.getsourcefile(handler_cls)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as e:
            QMessageBox.warning(self, "파일 열기 실패", str(e))
            return

        insert_at = self._find_class_body_end(lines, class_name)
        stub = (
            f"\n    def {name}(self, d, log_console=None):\n"
            f'        """TODO: 시나리오 설명을 작성하세요."""\n'
            f"        pass\n"
        )
        lines[insert_at:insert_at] = stub.splitlines(keepends=True)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            importlib.reload(module)
        except Exception as e:
            QMessageBox.warning(self, "저장 실패", str(e))
            return

        self._on_project_selected(proj_name)
        self._on_scenario_selected(proj_name, name)

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

    # ---------- 3단: 코드 보기 / 수정 ----------
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
        header.addStretch(1)

        self._btn_edit_in_builder = navy_button(
            "시나리오 작성에서 편집", kind="ghost", height=32, icon_name="fa5s.edit",
        )
        self._btn_edit_in_builder.clicked.connect(self._open_current_builder_scenario_for_edit)
        self._btn_edit_in_builder.setVisible(False)
        header.addWidget(self._btn_edit_in_builder)

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
        self._btn_edit_in_builder.setVisible(False)
        self._code_title_lbl.setText("코드")
        self._code_edit.setReadOnly(True)
        self._code_edit.setPlainText(message)
        self._btn_save.setEnabled(False)
        self._status_lbl.setText("")
        self._update_breadcrumb()

    def _on_scenario_selected(self, proj_name, method_name):
        self._current_builder_scenario_name = None
        self._btn_edit_in_builder.setVisible(False)

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
        self._code_edit.setReadOnly(False)
        self._btn_save.setEnabled(True)
        self._status_lbl.setText(file_path)

    def _on_builder_scenario_selected(self, proj_name, name):
        steps = scenario_store.list_scenarios(proj_name).get(name)
        if steps is None:
            self._show_code_placeholder(f"⚠️ 시나리오를 찾을 수 없습니다: {name}")
            return

        self._current = None  # 코드 파일이 아니라 "저장"으로 덮어쓸 대상이 없음
        self._current_builder_scenario_name = name
        self._btn_edit_in_builder.setVisible(True)
        self._code_title_lbl.setText(f"{name}  ·  시나리오 작성")
        self._update_breadcrumb(name)
        lines = [f"# '{name}'은 시나리오 작성 화면에서 객체 기반으로 만든 시나리오입니다.\n",
                 "# 위의 '시나리오 작성에서 편집' 버튼을 누르면 바로 수정할 수 있습니다.\n\n"]
        for step in steps:
            lines.append(scenario_runner.step_code(step) + "\n")
        self._code_edit.setPlainText("".join(lines))
        self._code_edit.setReadOnly(True)
        self._btn_save.setEnabled(False)
        self._status_lbl.setText("'시나리오 작성에서 편집' 버튼으로 바로 수정할 수 있습니다.")

    def _open_current_builder_scenario_for_edit(self):
        if not self._current_project or not self._current_builder_scenario_name:
            return
        if self.on_edit_builder_scenario:
            self.on_edit_builder_scenario(self._current_project, self._current_builder_scenario_name)

    def _save_current_scenario(self):
        if not self._current:
            return
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
