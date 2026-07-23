import importlib
import inspect
import keyword
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import PrimaryPushButton, TogglePushButton
import qtawesome as qta

import object_store
from code_editor import CodeEditor
from device_panel import PROJECT_HANDLERS, SCENARIO_LABELS
from ui_common import Palette, add_shadow, card_css, clear_layout, kfont, styled


class ScenarioLibraryPage(QWidget):
    """프로젝트별로 저장된 시나리오(핸들러 메서드)를 관리하는 화면.
    왼쪽부터 [프로젝트 목록] - [시나리오 목록] - [코드 보기/수정] 3단 구성이고,
    시나리오를 고르면 오른쪽에 실제 소스 코드가 뜨고 편집 후 저장하면 해당
    config_handlers 파일에 바로 반영됩니다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("scenarioInterface")
        self._project_buttons = {}
        self._scenario_buttons = {}
        self._current_project = None
        self._current = None  # (module, handler_cls, method_name, file_path, start_line, line_count)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(16)

        outer.addWidget(self._build_project_list(), 2)
        self._scenario_list_card, self._scenario_list_layout = self._build_scenario_list()
        outer.addWidget(self._scenario_list_card, 2)
        outer.addWidget(self._build_code_panel(), 6)

        if PROJECT_HANDLERS:
            first_project = next(iter(PROJECT_HANDLERS))
            self._project_buttons[first_project].setChecked(True)
            self._on_project_selected(first_project)

    # ---------- 1단: 저장된 프로젝트 목록 ----------
    def _build_project_list(self):
        card = styled(QFrame(), card_css())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(6)

        title = QLabel("프로젝트")
        title.setFont(kfont(12, True))
        title.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(title)

        group = QButtonGroup(card)
        group.setExclusive(True)
        for proj_name in PROJECT_HANDLERS:
            btn = TogglePushButton(proj_name)
            btn.setFont(kfont(11, True))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, p=proj_name: self._on_project_selected(p))
            group.addButton(btn)
            layout.addWidget(btn)
            self._project_buttons[proj_name] = btn
        layout.addStretch(1)

        return add_shadow(card)

    # ---------- 2단: 선택한 프로젝트의 시나리오 목록 ----------
    def _build_scenario_list(self):
        card = styled(QFrame(), card_css())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(6)

        title = QLabel("시나리오")
        title.setFont(kfont(12, True))
        title.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(title)

        btn_add = PrimaryPushButton(qta.icon("fa5s.plus", color="white"), "시나리오 추가")
        btn_add.setFont(kfont(10, True))
        btn_add.setFixedHeight(28)
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._on_add_scenario_clicked)
        layout.addWidget(btn_add)

        layout.addStretch(1)

        return add_shadow(card), layout

    def _on_project_selected(self, proj_name):
        self._current_project = proj_name
        clear_layout(self._scenario_list_layout, keep=2)  # keep=2: 타이틀 + "시나리오 추가" 버튼
        self._scenario_buttons = {}
        self._show_code_placeholder("왼쪽에서 시나리오를 선택하세요.")

        module_name, class_name = PROJECT_HANDLERS[proj_name]
        try:
            module = importlib.import_module(module_name)
            handler_cls = getattr(module, class_name)
        except Exception as e:
            self._scenario_list_layout.insertWidget(
                self._scenario_list_layout.count() - 1, self._build_warning_label(str(e))
            )
            return

        method_names = [
            name for name, value in vars(handler_cls).items()
            if not name.startswith("_") and callable(value)
        ]
        if not method_names:
            self._scenario_list_layout.insertWidget(
                self._scenario_list_layout.count() - 1, self._build_warning_label("등록된 시나리오가 없습니다.")
            )
            return

        group = QButtonGroup(self._scenario_list_card)
        group.setExclusive(True)
        for name in method_names:
            label = SCENARIO_LABELS.get(name, name)
            btn = TogglePushButton(label)
            btn.setFont(kfont(11, True))
            btn.setFixedHeight(30)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(
                lambda checked=False, p=proj_name, n=name: self._on_scenario_selected(p, n)
            )
            group.addButton(btn)
            self._scenario_list_layout.insertWidget(self._scenario_list_layout.count() - 1, btn)
            self._scenario_buttons[name] = btn

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

    def _build_warning_label(self, message):
        lbl = QLabel(f"⚠️ {message}")
        lbl.setFont(kfont(10))
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{Palette.danger};")
        return lbl

    # ---------- 3단: 코드 보기 / 수정 ----------
    def _build_code_panel(self):
        card = styled(QFrame(), card_css())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self._code_title_lbl = QLabel("코드")
        self._code_title_lbl.setFont(kfont(13, True))
        self._code_title_lbl.setStyleSheet(f"color:{Palette.text_main};")
        header.addWidget(self._code_title_lbl)
        header.addStretch(1)

        self._btn_save = PrimaryPushButton("저장")
        self._btn_save.setFixedHeight(30)
        self._btn_save.setFont(kfont(11, True))
        self._btn_save.setCursor(Qt.PointingHandCursor)
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._save_current_scenario)
        header.addWidget(self._btn_save)
        layout.addLayout(header)

        self._code_edit = CodeEditor(object_provider=self._saved_objects_for_current_project)
        self._code_edit.setFont(QFont("Consolas", 11))
        self._code_edit.setStyleSheet(
            f"QPlainTextEdit {{ background-color:{Palette.bg}; color:{Palette.text_main}; "
            f"border:1px solid {Palette.border}; border-radius:{Palette.radius}px; padding:8px; }}"
        )
        self._code_edit.setPlainText(
            "왼쪽에서 프로젝트와 시나리오를 선택하세요.\n"
            "(편집 중 Ctrl+Space: 객체 관리에 저장해둔 객체 이름 자동완성)"
        )
        self._code_edit.setReadOnly(True)
        layout.addWidget(self._code_edit, 1)

        self._status_lbl = QLabel("")
        self._status_lbl.setFont(kfont(10))
        self._status_lbl.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(self._status_lbl)

        return card

    def _saved_objects_for_current_project(self):
        if not self._current_project:
            return {}
        return object_store.list_objects(self._current_project)

    def _show_code_placeholder(self, message):
        self._current = None
        self._code_title_lbl.setText("코드")
        self._code_edit.setReadOnly(True)
        self._code_edit.setPlainText(message)
        self._btn_save.setEnabled(False)
        self._status_lbl.setText("")

    def _on_scenario_selected(self, proj_name, method_name):
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
        self._code_title_lbl.setText(f"{proj_name} - {label} ({method_name})")
        self._code_edit.setPlainText("".join(source_lines))
        self._code_edit.setReadOnly(False)
        self._btn_save.setEnabled(True)
        self._status_lbl.setText(file_path)

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
