from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtWidgets import QCompleter, QPlainTextEdit


class CodeEditor(QPlainTextEdit):
    """저장된 객체 이름 자동완성이 붙은 QPlainTextEdit.
    Ctrl+Space를 누르거나 이름 일부를 입력하면 object_provider()가 돌려주는
    {이름: node} 중에서 매칭되는 것을 팝업으로 보여주고, 고르면 커서 위치의
    입력 중이던 접두어를 지우고 바로 쓸 수 있는 uiautomator2 선택자로 바꿔 넣습니다."""

    def __init__(self, object_provider, parent=None):
        super().__init__(parent)
        self._object_provider = object_provider

        self._completer = QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.activated[str].connect(self._insert_completion)

    def _insert_completion(self, name):
        node = self._object_provider().get(name)
        if node is None:
            return
        if node.get("resource_id"):
            snippet = f'd(resourceId="{node["resource_id"]}")'
        elif node.get("text"):
            snippet = f'd(text="{node["text"]}")'
        else:
            snippet = f'd(className="{node.get("class_name", "")}")'

        cursor = self.textCursor()
        extra = len(self._completer.completionPrefix())
        cursor.movePosition(cursor.MoveOperation.Left, cursor.MoveMode.KeepAnchor, extra)
        cursor.removeSelectedText()
        cursor.insertText(f"{snippet}  # {name}")
        self.setTextCursor(cursor)

    def _text_under_cursor(self):
        cursor = self.textCursor()
        cursor.select(cursor.SelectionType.WordUnderCursor)
        return cursor.selectedText()

    def keyPressEvent(self, event):
        if self.isReadOnly():
            super().keyPressEvent(event)
            return

        if self._completer.popup().isVisible() and event.key() in (
            Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab,
        ):
            event.ignore()
            return

        is_shortcut = bool(event.modifiers() & Qt.ControlModifier) and event.key() == Qt.Key_Space
        if not is_shortcut:
            super().keyPressEvent(event)

        prefix = self._text_under_cursor()
        if not is_shortcut and len(prefix) < 1:
            self._completer.popup().hide()
            return

        names = sorted(n for n in self._object_provider().keys() if prefix.lower() in n.lower())
        if not names:
            self._completer.popup().hide()
            return

        self._completer.setModel(QStringListModel(names, self._completer))
        self._completer.setCompletionPrefix(prefix)
        self._completer.popup().setCurrentIndex(self._completer.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(
            self._completer.popup().sizeHintForColumn(0)
            + self._completer.popup().verticalScrollBar().sizeHint().width()
        )
        self._completer.complete(cr)
