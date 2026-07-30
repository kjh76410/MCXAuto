import importlib
import inspect
import os
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import PrimaryPushButton
import qtawesome as qta

import project_config_store
from device_panel import PROJECT_HANDLERS, reload_project_handlers
from ui_common import Palette, add_shadow, card_css, kfont, styled


class ProjectManagerPage(QWidget):
    """새 프로젝트를 등록하는 화면. 기존 프로젝트 중 하나를 골라 그 핸들러 파일
    (환경설정 run / 통화 발신 make_call·make_emergency_call / 메시지 send_message가
    들어있는 config_handlers/*.py)을 그대로 복제해 새 클래스로 저장하고,
    project_config.json에 단말 자동 인식용 ID(keyword)와 함께 등록합니다.
    복제된 시나리오는 이후 '시나리오' 화면에서 자유롭게 수정할 수 있습니다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("projectManagerInterface")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(16)

        outer.addWidget(self._build_project_list(), 4)
        outer.addWidget(self._build_add_form(), 5)

        self._refresh_project_list()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_project_list()
        self._refresh_source_combo()

    # ---------- 왼쪽: 등록된 프로젝트 목록 ----------
    def _build_project_list(self):
        card = styled(QFrame(), card_css())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(6)

        title = QLabel("등록된 프로젝트")
        title.setFont(kfont(12, True))
        title.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(title)

        self._project_list = QListWidget()
        layout.addWidget(self._project_list, 1)

        return add_shadow(card)

    def _refresh_project_list(self):
        self._project_list.clear()
        for proj in project_config_store.list_projects():
            name = proj.get("project_name", "")
            keyword = proj.get("keyword", "")
            has_handler = name in PROJECT_HANDLERS
            status = proj.get("handler_class", "") if has_handler else "핸들러 없음"
            self._project_list.addItem(QListWidgetItem(f"{name}  (ID: {keyword})  —  {status}"))

    # ---------- 오른쪽: 새 프로젝트 추가 ----------
    def _build_add_form(self):
        card = styled(QFrame(), card_css())
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        title = QLabel("새 프로젝트 추가")
        title.setFont(kfont(13, True))
        title.setStyleSheet(f"color:{Palette.text_main};")
        layout.addWidget(title)

        layout.addWidget(self._field_label("프로젝트 이름"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("예) 신규프로젝트")
        self._style_edit(self._name_edit)
        layout.addWidget(self._name_edit)

        layout.addWidget(self._field_label("단말 인식 ID"))
        self._keyword_edit = QLineEdit()
        self._keyword_edit.setPlaceholderText("단말 버전 문자열에 포함되는 고유 키워드 (예: PSP.R)")
        self._style_edit(self._keyword_edit)
        layout.addWidget(self._keyword_edit)
        hint = QLabel("단말 연결 시 버전 문자열에 이 ID가 포함되어 있으면 자동으로 이 프로젝트로 인식합니다.")
        hint.setWordWrap(True)
        hint.setFont(kfont(9))
        hint.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(hint)

        layout.addWidget(self._field_label("복제할 기존 프로젝트"))
        self._source_combo = QComboBox()
        layout.addWidget(self._source_combo)
        hint2 = QLabel(
            "선택한 프로젝트의 환경설정/통화 발신/메시지 전송 시나리오를 그대로 복제합니다.\n"
            "복제된 내용은 '시나리오' 화면에서 자유롭게 수정할 수 있습니다."
        )
        hint2.setWordWrap(True)
        hint2.setFont(kfont(9))
        hint2.setStyleSheet(f"color:{Palette.text_sub};")
        layout.addWidget(hint2)

        layout.addStretch(1)

        btn_add = PrimaryPushButton(qta.icon("fa5s.plus", color="white"), "프로젝트 추가")
        btn_add.setFixedHeight(32)
        btn_add.setFont(kfont(11, True))
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._add_project)
        layout.addWidget(btn_add)

        self._refresh_source_combo()
        return add_shadow(card)

    @staticmethod
    def _field_label(text):
        lbl = QLabel(text)
        lbl.setFont(kfont(11, True))
        lbl.setStyleSheet(f"color:{Palette.text_sub};")
        return lbl

    @staticmethod
    def _style_edit(edit):
        edit.setStyleSheet(
            f"QLineEdit {{ background-color:#FFFFFF; color:{Palette.text_main}; "
            f"border:1px solid {Palette.border}; border-radius:6px; padding:4px 8px; }}"
        )

    def _refresh_source_combo(self):
        current = self._source_combo.currentText() if self._source_combo.count() else None
        self._source_combo.clear()
        self._source_combo.addItems(list(PROJECT_HANDLERS.keys()))
        if current:
            idx = self._source_combo.findText(current)
            if idx >= 0:
                self._source_combo.setCurrentIndex(idx)

    # ---------- 이름/파일 이름 생성 ----------
    @staticmethod
    def _to_identifier(text, suffix=""):
        cleaned = re.sub(r"[^\w]", "", text)
        if not cleaned or cleaned[0].isdigit():
            cleaned = f"P{cleaned}"
        return cleaned + suffix

    @staticmethod
    def _slugify(text):
        cleaned = re.sub(r"[^\w]+", "_", text.strip()).strip("_")
        return cleaned or "project"

    def _unique_class_name(self, base):
        existing = {p.get("handler_class") for p in project_config_store.list_projects() if p.get("handler_class")}
        name = base
        i = 2
        while name in existing:
            name = f"{base}{i}"
            i += 1
        return name

    def _unique_module_stem(self, base):
        stem = base
        i = 2
        while os.path.exists(os.path.join("config_handlers", f"{stem}.py")):
            stem = f"{base}{i}"
            i += 1
        return stem

    # ---------- 추가 ----------
    def _add_project(self):
        new_name = self._name_edit.text().strip()
        keyword = self._keyword_edit.text().strip()
        source_name = self._source_combo.currentText()

        if not new_name:
            QMessageBox.warning(self, "이름 필요", "새 프로젝트 이름을 입력해주세요.")
            return
        if not keyword:
            QMessageBox.warning(self, "ID 필요", "단말을 자동으로 인식할 ID(keyword)를 입력해주세요.")
            return
        if not source_name:
            QMessageBox.warning(self, "복제할 프로젝트 필요", "핸들러를 복제할 기존 프로젝트를 선택해주세요.")
            return
        if new_name in PROJECT_HANDLERS or project_config_store.project_name_exists(new_name):
            QMessageBox.warning(self, "이름 중복", f"'{new_name}' 프로젝트가 이미 있습니다.")
            return

        module_name, class_name = PROJECT_HANDLERS[source_name]
        try:
            module = importlib.import_module(module_name)
            handler_cls = getattr(module, class_name)
            source_file = inspect.getsourcefile(handler_cls)
            with open(source_file, "r", encoding="utf-8") as f:
                source_text = f.read()
        except Exception as e:
            QMessageBox.warning(self, "원본 핸들러 로드 실패", str(e))
            return

        new_class_name = self._unique_class_name(self._to_identifier(new_name, "Handler"))
        new_module_stem = self._unique_module_stem(f"{self._slugify(new_name)}_handler")
        new_file_path = os.path.join("config_handlers", f"{new_module_stem}.py")

        new_source_text, count = re.subn(
            rf"\bclass\s+{re.escape(class_name)}\b", f"class {new_class_name}", source_text, count=1
        )
        if count == 0:
            QMessageBox.warning(self, "복제 실패", f"원본 파일에서 'class {class_name}' 선언을 찾지 못했습니다.")
            return

        try:
            with open(new_file_path, "w", encoding="utf-8") as f:
                f.write(new_source_text)
        except OSError as e:
            QMessageBox.warning(self, "파일 생성 실패", str(e))
            return

        new_module_name = f"config_handlers.{new_module_stem}"
        project_config_store.add_project(source_name, new_name, keyword, new_module_name, new_class_name)
        reload_project_handlers()

        self._name_edit.clear()
        self._keyword_edit.clear()
        self._refresh_project_list()
        self._refresh_source_combo()

        QMessageBox.information(
            self,
            "추가 완료",
            f"'{new_name}' 프로젝트를 추가하고 '{source_name}'의 환경설정/통화 발신/메시지 시나리오를 복제했습니다.\n"
            f"필요한 부분은 '시나리오' 화면에서 수정해주세요.\n\n"
            f"(새 화면·목록에 반영: 객체 관리 / 시나리오 작성 / 시나리오 화면을 다시 열면 바로 보입니다.)",
        )
