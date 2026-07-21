import sys
import os
import math
import random

from PySide6.QtCore import Qt, QObject, Signal, QTimer, QSize
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)
import qtawesome as qta


# ==========================================
# 🎨 [iOS System Palette]
# ==========================================
class Palette:
    bg = "#F2F2F7"
    panel = "#FFFFFF"
    border = "#E5E5EA"
    text_main = "#1C1C1E"
    text_sub = "#8E8E93"
    blue = "#0B4192"
    blue_hover = "#093475"
    orange = "#FF9500"
    orange_hover = "#DB7F00"
    danger = "#FF3B30"
    danger_bg = "#FFE5E4"
    danger_bg_hover = "#FFD2D0"
    tint_blue_bg = "#E4E9F3"
    tint_blue_hover = "#D2DAE9"
    tint_orange_bg = "#FFF1DC"
    tint_orange_hover = "#FFE6BF"
    neutral_bg = "#EDEDF0"
    neutral_hover = "#E2E2E6"
    radius = 4


def load_custom_font():
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_path, "assets", "fonts", "NotoSansKR-Regular.ttf")
    if os.path.exists(font_path):
        QFontDatabase.addApplicationFont(font_path)


FONT_SCALE = 0.85


def kfont(size, bold=False):
    f = QFont("Noto Sans KR", max(8, round(size * FONT_SCALE)))
    f.setBold(bold)
    return f


def styled(widget, css):
    widget.setAttribute(Qt.WA_StyledBackground, True)
    widget.setStyleSheet(css)
    return widget


def add_shadow(widget, blur=24, y_offset=3, alpha=25):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)
    return widget


def card_css(bg=Palette.panel, border="transparent", radius=Palette.radius):
    return f"background-color:{bg}; border:1px solid {border}; border-radius:{radius}px;"


def _shade(hex_color, factor):
    """hex_color를 factor(0~1)만큼 어둡게 만든 색을 돌려줍니다.
    버튼마다 매번 테두리/눌림 색을 따로 지정하지 않고, bg/hover 색에서 자동으로
    한 톤 어두운 테두리·pressed 색을 뽑아내 네이티브 버튼 느낌(입체감)을 내기 위함."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return hex_color
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (max(0, min(255, int(c * factor))) for c in (r, g, b))
    return f"#{r:02X}{g:02X}{b:02X}"


def btn_css(bg, fg, hover, radius=Palette.radius, disabled_bg="#F2F2F7", disabled_fg="#C7C7CC"):
    border = _shade(bg, 0.85)
    pressed = _shade(hover, 0.95)
    return (
        f"QPushButton {{ background-color:{bg}; color:{fg}; border:1px solid {border}; "
        f"border-radius:{radius}px; font-weight:600; }}"
        f"QPushButton:hover {{ background-color:{hover}; }}"
        f"QPushButton:pressed {{ background-color:{pressed}; border-color:{border}; }}"
        f"QPushButton:disabled {{ background-color:{disabled_bg}; color:{disabled_fg}; border-color:{disabled_bg}; }}"
    )


def make_button(text, bg, fg, hover, height=26, radius=Palette.radius, icon_name=None, icon_size=14):
    btn = QPushButton(text)
    btn.setFixedHeight(height)
    btn.setFont(kfont(11, True))
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(btn_css(bg, fg, hover, radius))
    if icon_name:
        btn.setIcon(qta.icon(icon_name, color=fg))
        btn.setIconSize(QSize(icon_size, icon_size))
    return btn


def clear_layout(layout, keep=0):
    while layout.count() > keep:
        item = layout.takeAt(keep)
        w = item.widget()
        if w is not None:
            w.deleteLater()


# ==========================================
# 🔔 스레드 -> UI 안전 전달용 시그널 버스
# ==========================================
class Signals(QObject):
    log_append = Signal(str, bool)
    flow_card = Signal(str, str, str, bool)
    network_label = Signal(str)
    floor_state = Signal(str)
    device_ready = Signal(object)
    pcap_state = Signal(bool)


class QtLogConsole:
    """config_handlers / common_logger가 기대하는 tkinter Text 스타일의
    insert("end", text) / see("end") API를 흉내내는 얇은 어댑터.
    백그라운드 스레드에서도 안전하게 호출할 수 있도록 시그널로만 통신합니다."""

    def __init__(self, app):
        self._app = app

    def insert(self, index, text):
        self._app.safe_log_insert(text)

    def see(self, index):
        pass


class ClickableLabel(QLabel):
    clicked = Signal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class SegmentedButton(QWidget):
    """CTkSegmentedButton과 비슷한 set()/get() API를 제공하는 단일 선택 버튼 그룹."""

    changed = Signal(str)

    def __init__(self, values, selected_color=Palette.neutral_hover, height=23, font=None, parent=None):
        super().__init__(parent)
        self._selected_color = selected_color
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons = {}
        for v in values:
            btn = QPushButton(v)
            btn.setCheckable(True)
            btn.setFixedHeight(height)
            btn.setFont(font or kfont(10))
            btn.setCursor(Qt.PointingHandCursor)
            layout.addWidget(btn)
            self._group.addButton(btn)
            self._buttons[v] = btn
        self._group.buttonClicked.connect(self._on_click)
        self._apply_style()

    def _on_click(self, btn):
        self._apply_style()
        self.changed.emit(btn.text())

    def _apply_style(self):
        for btn in self._buttons.values():
            if btn.isChecked():
                btn.setStyleSheet(
                    f"QPushButton {{ background-color:{self._selected_color}; color:{Palette.text_main}; "
                    f"border:none; border-radius:3px; font-weight:600; }}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton {{ background-color:{Palette.neutral_bg}; color:{Palette.text_main}; "
                    f"border:none; border-radius:3px; }}"
                    f"QPushButton:hover {{ background-color:{Palette.neutral_hover}; }}"
                )

    def set(self, value):
        if not value:
            checked = self._group.checkedButton()
            if checked:
                self._group.setExclusive(False)
                checked.setChecked(False)
                self._group.setExclusive(True)
        else:
            btn = self._buttons.get(value)
            if btn:
                btn.setChecked(True)
        self._apply_style()

    def get(self):
        checked = self._group.checkedButton()
        return checked.text() if checked else ""


class PulseCanvas(QWidget):
    """PTT 발언권 상태에 연동되는 사운드 파형 애니메이션."""

    def __init__(self, color=Palette.blue, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._offset = 0
        self.active = False
        self.setMinimumHeight(60)
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self.active = True
        self._timer.start()

    def stop(self):
        self.active = False
        self._timer.stop()
        self.update()

    def _tick(self):
        self._offset += 8
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cy = h / 2

        if not self.active:
            painter.setPen(QPen(QColor("#3A4A63"), 2))
            painter.drawLine(0, int(cy), w, int(cy))
            return

        painter.setPen(QPen(self._color, 2.5))
        path = QPainterPath()
        first = True
        for x in range(0, w, 4):
            amp = random.uniform(0.8, 1.2) * 35
            y = cy + math.sin((x + self._offset) * 0.05) * amp * math.cos(
                (x - self._offset) * 0.02
            )
            if first:
                path.moveTo(x, y)
                first = False
            else:
                path.lineTo(x, y)
        painter.drawPath(path)
