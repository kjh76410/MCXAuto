import sys
import os
import math
import random
import webbrowser

from PySide6.QtCore import Qt, QObject, Signal, QTimer, QSize, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta
from qfluentwidgets import PushButton, PrimaryPushButton

import launcher_links_store


# ==========================================
# 🎨 [Pastel Lavender Palette]
# ==========================================
class Palette:
    bg = "#F7F6FC"
    panel = "#FFFFFF"
    border = "#E9E6F5"
    text_main = "#3F3D56"
    text_sub = "#8B889D"
    blue = "#7FA8E8"
    blue_hover = "#6994D9"
    accent = "#9B92E8"
    accent_hover = "#8579DD"
    orange = "#F0AA6E"
    orange_hover = "#E4954F"
    danger = "#EF9A96"
    danger_bg = "#FCEDEC"
    danger_bg_hover = "#F8DEDC"
    tint_blue_bg = "#EAF1FC"
    tint_blue_hover = "#DCE7F8"
    tint_orange_bg = "#FCF0E1"
    tint_orange_hover = "#F9E4C7"
    neutral_bg = "#F1EFFA"
    neutral_hover = "#E6E2F5"
    radius = 10


def load_custom_font():
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    for font_file in ("Pretendard-Regular.otf", "NotoSansKR-Regular.ttf"):
        font_path = os.path.join(base_path, "assets", "fonts", font_file)
        if os.path.exists(font_path):
            QFontDatabase.addApplicationFont(font_path)


FONT_SCALE = 0.85


def kfont(size, bold=False):
    f = QFont("Pretendard", max(8, round(size * FONT_SCALE)))
    f.setBold(bold)
    # Pretendard-Regular.otf는 자체 힌팅 명령이 없는 CFF 윤곽선이라, 작은 크기에서
    # "그"의 "ㅡ" 같은 얇은 가로 획이 그리드 피팅 과정에서 통째로 사라지는 문제가
    # 있었습니다. 품질 우선 안티앨리어싱 전략을 강제해 얇은 획이 픽셀 격자에 걸려도
    # 없어지지 않고 흐리게라도 남도록 합니다.
    f.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
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


def _paint_centered_icon(self, e):
    """텍스트 없이 아이콘만 있는 버튼용 paintEvent. qfluentwidgets PushButton의 기본
    아이콘 위치 계산식이 아이콘 뒤에 텍스트가 붙는 상황을 가정하고 있어서, 텍스트가
    없으면 버튼 폭을 아무리 조정해도 아이콘이 항상 왼쪽으로 살짝 치우쳐 보입니다.
    버튼 정중앙 좌표를 직접 계산해서 그립니다."""
    QPushButton.paintEvent(self, e)
    if self.icon().isNull():
        return

    painter = QPainter(self)
    painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    if not self.isEnabled():
        painter.setOpacity(0.3628)
    elif self.isPressed:
        painter.setOpacity(0.786)

    w, h = self.iconSize().width(), self.iconSize().height()
    x = (self.width() - w) / 2
    y = (self.height() - h) / 2
    self._drawIcon(self._icon, painter, QRectF(x, y, w, h))


class _CenteredIconButton(PushButton):
    """텍스트 없이 아이콘만 있는 PushButton용 (make_button()이 자동으로 골라 씁니다)."""
    paintEvent = _paint_centered_icon


class CenteredIconPrimaryButton(PrimaryPushButton):
    """텍스트 없이 아이콘만 있는 PrimaryPushButton용 (예: 원형 뱃지 버튼)."""
    paintEvent = _paint_centered_icon


def make_button(text, bg, fg, hover, height=26, radius=Palette.radius, icon_name=None, icon_size=14):
    """bg/hover/radius는 옛 QSS 버튼과의 시그니처 호환을 위해 남아있을 뿐, 실제 배경/테두리는
    이제 Fluent 기본 PushButton 스타일을 그대로 씁니다(fg는 아이콘 색상에만 씁니다)."""
    btn = _CenteredIconButton(text) if (icon_name and not text) else PushButton(text)
    btn.setFixedHeight(height)
    btn.setFont(kfont(11, True))
    btn.setCursor(Qt.PointingHandCursor)
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

    def __init__(self, values, selected_color=Palette.neutral_hover, selected_text_color=None,
                 height=23, font=None, parent=None):
        super().__init__(parent)
        self._selected_color = selected_color
        self._selected_text_color = selected_text_color or Palette.text_main
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
                    f"QPushButton {{ background-color:{self._selected_color}; color:{self._selected_text_color}; "
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


def _launcher_icon_path():
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "assets", "icons", "launcher_icon.png")


class LauncherBadge(QWidget):
    """악어 런처 아이콘 머리 위에 떠 있는 원형 뱃지 하나(고정 QA 뱃지 또는
    사용자가 추가한 링크 뱃지). 프레임 없는 항상-위 위젯이라 악어 아이콘과
    같은 방식으로 화면 위에 독립적으로 떠 있습니다."""

    clicked = Signal()

    def __init__(self, text, color, size=44, icon_name="fa5s.link"):
        super().__init__(None)
        self._size = size
        self._color = QColor(color)
        self._hover = False
        self._text = text
        self._icon = qta.icon(icon_name, color="#FFFFFF").pixmap(QSize(round(size * 0.42), round(size * 0.42)))
        self.setFixedSize(size, size)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(text)
        add_shadow(self, blur=14, y_offset=2, alpha=60)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        s = self._size
        rect = QRectF(2, 2, s - 4, s - 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color.lighter(112) if self._hover else self._color)
        painter.drawEllipse(rect)

        icon_size = self._icon.size()
        x = (s - icon_size.width()) / 2
        y = (s - icon_size.height()) / 2
        painter.drawPixmap(QRectF(x, y, icon_size.width(), icon_size.height()).toRect(), self._icon)


class _AddLinkDialog(QDialog):
    """악어 런처 우클릭 메뉴의 '링크 추가'로 뜨는 이름/URL 입력 다이얼로그."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("링크 추가")
        self.setFixedWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("뱃지 이름 (예: TMS)")
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("URL (예: 10.1.100.70:1443)")
        layout.addWidget(self.name_edit)
        layout.addWidget(self.url_edit)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("취소")
        btn_save = QPushButton("추가")
        btn_save.setDefault(True)
        btn_cancel.clicked.connect(self.reject)
        btn_save.clicked.connect(self.accept)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

    def values(self):
        return self.name_edit.text().strip(), self.url_edit.text().strip()


class RobotLauncherButton(QWidget):
    """앱의 메인 창과는 별개인, 윈도우 화면(데스크톱) 우측 하단에 항상 떠 있는
    런처 아이콘(assets/icons/launcher_icon.png를 그려 보여줍니다). 테두리 없는
    항상-위 위젯이라 main.py 실행 직후 메인 창 없이 이것만 먼저 띄워둘 수 있습니다.

    좌클릭하면 머리 위로 뱃지들이 토글되어 나타납니다: 맨 아래(가장 가까운) 뱃지는
    항상 있는 'QA'로, 누르면 open_main_requested를 emit해 메인 자동화툴 창을 엽니다.
    그 위로는 사용자가 우클릭 메뉴 '링크 추가'로 등록한 링크 뱃지들이 추가된 순서대로
    쌓이며, 누르면 해당 URL을 기본 브라우저로 엽니다. 등록한 링크는 launcher_links_store를
    통해 파일로 저장되어 다음 실행에도 유지됩니다."""

    open_main_requested = Signal()

    QA_COLOR = "#9B92E8"
    LINK_COLORS = ["#7FA8E8", "#F0AA6E", "#EF9A96", "#7FD8C6", "#E29BDB"]
    BADGE_SIZE = 44
    BADGE_GAP = 10

    ICON_BG_COLOR = "#1F2E56"

    def __init__(self, size=64):
        super().__init__(None)
        self._size = size
        self._hover = False
        self._icon = self._tint_white(QPixmap(_launcher_icon_path()))
        self._badges = []  # LauncherBadge 목록: [0]=QA(악어와 가장 가까움), 이후 링크들
        self._badges_visible = False
        self.setFixedSize(size, size)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("클릭: 바로가기 메뉴 · 우클릭: 링크 추가")
        add_shadow(self, blur=20, y_offset=4, alpha=70)
        self._move_to_screen_corner()
        self._rebuild_badges()

    def _move_to_screen_corner(self, margin=24):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.move(geo.right() - self._size - margin, geo.bottom() - self._size - margin)

    @staticmethod
    def _tint_white(pixmap):
        """아이콘 PNG의 불투명 픽셀을 전부 흰색으로 칠해, 색깔 있는 원본
        아이콘이라도 뱃지처럼 단색 흰색 글리프로 보이게 합니다."""
        if pixmap.isNull():
            return pixmap
        tinted = QPixmap(pixmap.size())
        tinted.setDevicePixelRatio(pixmap.devicePixelRatio())
        tinted.fill(Qt.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), QColor("#FFFFFF"))
        painter.end()
        return tinted

    def _rebuild_badges(self):
        for badge in self._badges:
            badge.hide()
            badge.deleteLater()
        self._badges = []

        qa_badge = LauncherBadge("QA", self.QA_COLOR, self.BADGE_SIZE, icon_name="fa5s.flask")
        qa_badge.clicked.connect(self._on_qa_badge_clicked)
        self._badges.append(qa_badge)

        for i, link in enumerate(launcher_links_store.list_links()):
            color = self.LINK_COLORS[i % len(self.LINK_COLORS)]
            badge = LauncherBadge(link.get("name", "?"), color, self.BADGE_SIZE, icon_name="fa5s.link")
            badge.clicked.connect(lambda checked=False, url=link.get("url", ""): self._on_link_badge_clicked(url))
            self._badges.append(badge)

        self._layout_badges()
        for badge in self._badges:
            badge.setVisible(self._badges_visible)

    def _layout_badges(self):
        x = self.x() + (self._size - self.BADGE_SIZE) // 2
        y = self.y() - self.BADGE_GAP
        for badge in self._badges:
            y -= badge.height()
            badge.move(x, y)
            y -= self.BADGE_GAP

    def _toggle_badges(self):
        self._badges_visible = not self._badges_visible
        if self._badges_visible:
            self._layout_badges()
        for badge in self._badges:
            badge.setVisible(self._badges_visible)

    def _on_qa_badge_clicked(self):
        self._toggle_badges()
        self.open_main_requested.emit()

    def _on_link_badge_clicked(self, url):
        self._toggle_badges()
        if url and not url.startswith(("http://", "https://")):
            url = "http://" + url
        if url:
            webbrowser.open(url)

    def _open_add_link_dialog(self):
        dlg = _AddLinkDialog()
        if dlg.exec() == QDialog.Accepted:
            name, url = dlg.values()
            if name and url:
                launcher_links_store.add_link(name, url)
                self._rebuild_badges()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_badges()
        elif event.button() == Qt.RightButton:
            menu = QMenu()
            action = menu.addAction("링크 추가")
            action.triggered.connect(self._open_add_link_dialog)
            menu.exec(event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        s = self._size
        radius = s * 0.28
        bg = QColor(self.ICON_BG_COLOR)
        if self._hover:
            bg = bg.lighter(112)
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(QRectF(0, 0, s, s), radius, radius)

        pad = s * 0.22
        icon_rect = QRectF(pad, pad, s - pad * 2, s - pad * 2)
        if not self._icon.isNull():
            painter.drawPixmap(icon_rect.toRect(), self._icon)
