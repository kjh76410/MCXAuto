import importlib
import inspect
import os
import re

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

import project_config_store
from device_panel import PROJECT_HANDLERS, reload_project_handlers
from ui_common import (
    Navy,
    kfont,
    navy_button,
    navy_card,
    navy_card_header,
    navy_input_css,
    navy_list_css,
    navy_mono_font,
    navy_page_css,
    navy_page_header,
    navy_pill,
)


class ProjectManagerPage(QWidget):
    """새 프로젝트를 등록하는 화면. 기존 프로젝트 중 하나를 골라 그 핸들러 파일
    (환경설정 run / 통화 발신 make_call·make_emergency_call / 메시지 send_message가
    들어있는 config_handlers/*.py)을 그대로 복제해 새 클래스로 저장하고,
    project_config.json에 단말 자동 인식용 ID(keyword)와 함께 등록합니다.
    복제된 시나리오는 이후 '시나리오' 화면에서 자유롭게 수정할 수 있습니다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("projectManagerInterface")
        self.setAttribute(Qt.WA_StyledBackground, True)
        # 자식까지 물들이지 않도록 이 위젯 하나만 가리키는 id 선택자로 바닥색을 칠합니다.
        self.setStyleSheet(navy_page_css("projectManagerInterface"))

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        header, self._breadcrumb = navy_page_header(
            "프로젝트 관리", "기존 프로젝트의 핸들러를 복제해 새 프로젝트를 등록합니다."
        )
        outer.addWidget(header)

        body = QHBoxLayout()
        body.setSpacing(14)
        outer.addLayout(body, 1)

        body.addWidget(self._build_project_list(), 4)
        body.addWidget(self._build_add_form(), 5)

        self._refresh_project_list()

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_project_list()
        self._refresh_source_combo()

    # ---------- 왼쪽: 등록된 프로젝트 목록 ----------
    def _build_project_list(self):
        card = navy_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        header, self._project_count = navy_card_header("등록된 프로젝트", badge=0)
        layout.addWidget(header)

        self._project_list = QListWidget()
        self._project_list.setStyleSheet(navy_list_css())
        layout.addWidget(self._project_list, 1)

        return card

    def _refresh_project_list(self):
        self._project_list.clear()
        projects = project_config_store.list_projects()
        self._project_count.setText(str(len(projects)))
        self._breadcrumb.setText(f"{len(projects)}개 등록됨")

        for proj in projects:
            name = proj.get("project_name", "")
            keyword = proj.get("keyword", "")
            has_handler = name in PROJECT_HANDLERS
            status = proj.get("handler_class", "") if has_handler else "핸들러 없음"

            # 한 줄에 [이름 / 단말 인식 ID / 핸들러 상태 배지]를 두 톤으로 나눠 보여주려고
            # 기본 텍스트 항목 대신 행 위젯을 얹습니다(클릭해서 쓰는 목록은 아니라 표시 전용).
            item = QListWidgetItem()
            self._project_list.addItem(item)

            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            row_layout.setSpacing(10)

            name_lbl = QLabel(name)
            name_lbl.setFont(kfont(11, True))
            name_lbl.setStyleSheet(f"color:{Navy.text};")
            row_layout.addWidget(name_lbl)

            id_lbl = QLabel(f"ID: {keyword}")
            id_lbl.setFont(navy_mono_font(9))
            id_lbl.setStyleSheet(f"color:{Navy.text_muted};")
            row_layout.addWidget(id_lbl)
            row_layout.addStretch(1)

            if has_handler:
                badge = navy_pill(status)
            else:
                badge = navy_pill(status, fg=Navy.danger, bg=Navy.danger_soft)
            badge.setFont(navy_mono_font(8) if has_handler else kfont(9, True))
            row_layout.addWidget(badge)

            item.setSizeHint(QSize(0, row.sizeHint().height() + 8))
            self._project_list.setItemWidget(item, row)

    # ---------- 오른쪽: 새 프로젝트 추가 ----------
    def _build_add_form(self):
        card = navy_card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        header, _ = navy_card_header("새 프로젝트 추가")
        layout.addWidget(header)

        layout.addWidget(self._field_label("프로젝트 이름"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("예) 신규프로젝트")
        self._style_edit(self._name_edit)
        layout.addWidget(self._name_edit)

        layout.addSpacing(4)
        layout.addWidget(self._field_label("단말 인식 ID"))
        self._keyword_edit = QLineEdit()
        self._keyword_edit.setPlaceholderText("단말 버전 문자열에 포함되는 고유 키워드 (예: PSP.R)")
        self._style_edit(self._keyword_edit)
        layout.addWidget(self._keyword_edit)
        layout.addWidget(
            self._field_hint("단말 연결 시 버전 문자열에 이 ID가 포함되어 있으면 자동으로 이 프로젝트로 인식합니다.")
        )

        layout.addSpacing(4)
        layout.addWidget(self._field_label("복제할 기존 프로젝트"))
        self._source_combo = QComboBox()
        self._source_combo.setFixedHeight(32)
        self._source_combo.setFont(kfont(10))
        self._source_combo.setStyleSheet(navy_input_css())
        layout.addWidget(self._source_combo)
        layout.addWidget(
            self._field_hint(
                "선택한 프로젝트의 환경설정/통화 발신/메시지 전송 시나리오를 그대로 복제합니다. "
                "복제된 내용은 '시나리오' 화면에서 자유롭게 수정할 수 있습니다."
            )
        )

        layout.addStretch(1)

        btn_add = navy_button("프로젝트 추가", kind="primary", height=34, icon_name="fa5s.plus")
        btn_add.clicked.connect(self._add_project)
        layout.addWidget(btn_add)

        self._refresh_source_combo()
        return card

    @staticmethod
    def _field_label(text):
        """입력칸 위에 붙는 항목 이름."""
        lbl = QLabel(text)
        lbl.setFont(kfont(10, True))
        lbl.setStyleSheet(f"color:{Navy.text}; padding-top:2px;")
        return lbl

    @staticmethod
    def _field_hint(text):
        """입력칸 아래에 붙는 설명 문구."""
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setFont(kfont(9))
        lbl.setStyleSheet(f"color:{Navy.text_muted};")
        return lbl

    @staticmethod
    def _style_edit(edit):
        edit.setFixedHeight(32)
        edit.setFont(kfont(10))
        edit.setStyleSheet(navy_input_css())

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
