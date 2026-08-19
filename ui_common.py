import sys
import os
import math
import random

from PySide6.QtCore import (
    Qt,
    QObject,
    Signal,
    QTimer,
    QSize,
    QRectF,
    QPointF,
    QPoint,
    QEasingCurve,
    QPropertyAnimation,
    QParallelAnimationGroup,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta
from qfluentwidgets import PushButton, PrimaryPushButton


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


def place_as_left_card(window, margin=24, launcher_lane=110):
    """런처(우측 하단 데스크톱 아이콘)에서 여는 창을, 런처 자리만 비워두고 화면
    왼쪽을 꽉 채우는 큰 카드처럼 배치한 뒤 띄웁니다. 관리 창과 프로젝트 창이
    같은 자리/같은 크기로 열리도록 두 창 모두 이 함수를 씁니다."""
    screen = QApplication.primaryScreen()
    if screen is not None:
        geo = screen.availableGeometry()
        width = max(900, geo.width() - launcher_lane - margin * 2)
        height = max(600, geo.height() - margin * 2)
        window.resize(width, height)
        window.move(geo.left() + margin, geo.top() + margin)
    window.show()
    window.raise_()
    window.activateWindow()


def _launcher_icon_path():
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "assets", "icons", "launcher_icon.png")


def _paint_soft_shadow(painter, rect, radius, pad):
    """반투명 최상위 창에서 QGraphicsDropShadowEffect를 쓰면 Windows가
    UpdateLayeredWindowIndirect 오류를 내므로, 라운드 사각형 몇 겹으로
    부드러운 그림자를 직접 그립니다. rect 바깥 pad 만큼의 여백을 사용합니다."""
    for i in range(pad, 0, -1):
        painter.setBrush(QColor(0, 0, 0, 14 + (pad - i) * 8))
        painter.drawRoundedRect(
            rect.adjusted(-i, -i + 1, i, i + 1), radius + i, radius + i
        )


class LauncherBadge(QWidget):
    """런처 아이콘 옆으로 펼쳐지는 메뉴 박스 하나. 런처 아이콘과 같은 모양(살짝만
    둥근 네모)이고, 라벨을 주면 아이콘 오른쪽에 글자까지 그려서 박스가 가로로
    길어집니다. 프레임 없는 항상-위 위젯이라 화면 위에 독립적으로 떠 있습니다.

    QGraphicsDropShadowEffect는 반투명 최상위 창에서 Windows의
    UpdateLayeredWindowIndirect 오류를 내므로, 그림자는 paintEvent에서 직접 그립니다."""

    clicked = Signal()

    CORNER_RATIO = 0.12
    SHADOW_PAD = 3
    H_PADDING = 14        # 라벨이 있는 박스의 좌우 안쪽 여백
    ICON_TEXT_GAP = 9

    def __init__(self, text, color, size=56, icon_name="fa5s.link", show_label=True):
        super().__init__(None)
        self._size = size
        self._color = QColor(color)
        self._hover = False
        self._text = text
        self._show_label = bool(show_label and text)
        self._font = kfont(10, True)

        icon_px = round(size * 0.42)
        self._icon = qta.icon(icon_name, color="#FFFFFF").pixmap(QSize(icon_px, icon_px))
        self._icon_px = icon_px

        if self._show_label:
            text_w = QFontMetrics(self._font).horizontalAdvance(text)
            self._box_w = self.H_PADDING * 2 + icon_px + self.ICON_TEXT_GAP + text_w
        else:
            self._box_w = size

        pad = self.SHADOW_PAD
        # 그림자를 직접 그리므로 박스 바깥에 SHADOW_PAD 만큼 여백을 둔 크기로 만듭니다.
        self.setFixedSize(self._box_w + pad * 2, size + pad * 2)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(text)

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

        pad = self.SHADOW_PAD
        body = QRectF(pad, pad, self._box_w, self._size)
        radius = self._size * self.CORNER_RATIO
        painter.setPen(Qt.NoPen)
        _paint_soft_shadow(painter, body, radius, pad)
        painter.setBrush(self._color.lighter(112) if self._hover else self._color)
        painter.drawRoundedRect(body, radius, radius)

        icon_px = self._icon_px
        icon_y = pad + (self._size - icon_px) / 2
        if self._show_label:
            icon_x = pad + self.H_PADDING
        else:
            icon_x = pad + (self._box_w - icon_px) / 2
        painter.drawPixmap(QRectF(icon_x, icon_y, icon_px, icon_px).toRect(), self._icon)

        if self._show_label:
            text_x = icon_x + icon_px + self.ICON_TEXT_GAP
            text_rect = QRectF(text_x, pad, body.right() - text_x, self._size)
            painter.setFont(self._font)
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, self._text)


class RobotLauncherButton(QWidget):
    """앱의 메인 창과는 별개인, 윈도우 화면(데스크톱) 우측 하단에 항상 떠 있는
    런처 아이콘(assets/icons/launcher_icon.png를 그려 보여줍니다). 테두리 없는
    항상-위 위젯이라 main.py 실행 직후 메인 창 없이 이것만 먼저 띄워둘 수 있습니다.

    좌클릭하면 아이콘 왼쪽으로 메뉴 박스들이 스르륵 펼쳐지고, 다시 누르면 접힙니다.
    메뉴 항목은 set_menu_items()로 바깥(main.py)에서 넣어줍니다. 여기서 프로젝트
    목록 같은 걸 직접 읽지 않는 이유는, ui_common이 device_panel/스토어 모듈을
    import하면 순환 import가 되기 때문입니다. 항목을 안 넣으면 기본값으로 'QA' 박스
    하나만 있고, 누르면 open_main_requested를 emit합니다."""

    open_main_requested = Signal()

    QA_COLOR = "#9B92E8"
    BADGE_SIZE = 56
    BADGE_GAP = 3
    ANIM_MS = 180

    ICON_BG_COLOR = "#1F2E56"
    CORNER_RATIO = 0.12
    SHADOW_PAD = 4

    def __init__(self, size=56):
        super().__init__(None)
        self._size = size
        self._hover = False
        self._icon = self._tint_white(QPixmap(_launcher_icon_path()))
        self._badges = []        # 펼쳐지는 메뉴 박스(LauncherBadge) 목록
        self._menu_items = None  # set_menu_items()로 받은 항목 정의
        self._items_provider = None  # 펼칠 때마다 항목을 새로 만들어주는 함수
        self._badges_visible = False
        self._anim_group = None
        self.setFixedSize(size + self.SHADOW_PAD * 2, size + self.SHADOW_PAD * 2)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("클릭: 바로가기 메뉴")
        self._move_to_screen_corner()
        self._rebuild_badges()

    # ---------- 메뉴 항목 ----------
    def set_menu_items(self, items):
        """메뉴 박스로 띄울 항목들을 갈아끼웁니다. 항목은 dict이며 키는
        label(글자), icon(qtawesome 이름), color(박스 색), on_click(누를 때 호출),
        show_label(글자 표시 여부, 기본 True)입니다. 런처 아이콘과 가까운 쪽부터
        리스트 순서대로 왼쪽으로 늘어섭니다."""
        self._menu_items = list(items)
        self._rebuild_badges()

    def set_menu_items_provider(self, provider):
        """펼칠 때마다 호출해서 메뉴 항목 리스트를 새로 받아오는 함수를 등록합니다.
        프로젝트를 추가/삭제해도 런처를 다시 켜지 않고 메뉴가 최신 상태가 되게 합니다."""
        self._items_provider = provider

    def _default_menu_items(self):
        return [{
            "label": "QA",
            "icon": "fa5s.flask",
            "color": self.QA_COLOR,
            "on_click": self.open_main_requested.emit,
            "show_label": False,
        }]

    def _rebuild_badges(self):
        for badge in self._badges:
            badge.hide()
            badge.deleteLater()
        self._badges = []

        items = self._menu_items if self._menu_items is not None else self._default_menu_items()
        for item in items:
            badge = LauncherBadge(
                item.get("label", "?"),
                item.get("color", self.QA_COLOR),
                self.BADGE_SIZE,
                icon_name=item.get("icon", "fa5s.link"),
                show_label=item.get("show_label", True),
            )
            handler = item.get("on_click")
            badge.clicked.connect(lambda _=False, fn=handler: self._on_item_clicked(fn))
            self._badges.append(badge)

        self._layout_badges()
        for badge in self._badges:
            badge.setVisible(self._badges_visible)

    def _on_item_clicked(self, handler):
        self._collapse()
        if callable(handler):
            handler()

    # ---------- 위치 / 펼침 애니메이션 ----------
    def _move_to_screen_corner(self, margin=24):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        self.move(geo.right() - self.width() - margin, geo.bottom() - self.height() - margin)

    def _expanded_positions(self):
        """펼쳤을 때 각 메뉴 박스가 놓일 좌표(런처 아이콘 왼쪽으로 나란히)."""
        positions = []
        x = self.x()
        for badge in self._badges:
            x -= badge.width() + self.BADGE_GAP
            y = self.y() + (self.height() - badge.height()) // 2
            positions.append(QPoint(x, y))
        return positions

    def _collapsed_position(self, badge):
        """접혔을 때 좌표: 런처 아이콘 뒤에 겹쳐 숨는 위치."""
        return QPoint(
            self.x() + (self.width() - badge.width()) // 2,
            self.y() + (self.height() - badge.height()) // 2,
        )

    def _layout_badges(self):
        for badge, pos in zip(self._badges, self._expanded_positions()):
            badge.move(pos)

    def _animate(self, targets, on_finished=None):
        if self._anim_group is not None:
            self._anim_group.stop()
        group = QParallelAnimationGroup(self)
        for badge, target in zip(self._badges, targets):
            anim = QPropertyAnimation(badge, b"pos", self)
            anim.setDuration(self.ANIM_MS)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.setStartValue(badge.pos())
            anim.setEndValue(target)
            group.addAnimation(anim)
        if on_finished is not None:
            group.finished.connect(on_finished)
        self._anim_group = group
        group.start()

    def _expand(self):
        if callable(self._items_provider):
            self.set_menu_items(self._items_provider())
        self._badges_visible = True
        for badge in self._badges:
            badge.move(self._collapsed_position(badge))
            badge.show()
        self._animate(self._expanded_positions())

    def _collapse(self):
        if not self._badges_visible:
            return
        self._badges_visible = False
        targets = [self._collapsed_position(badge) for badge in self._badges]

        def hide_all():
            if not self._badges_visible:
                for badge in self._badges:
                    badge.hide()

        self._animate(targets, on_finished=hide_all)

    def _toggle_badges(self):
        if self._badges_visible:
            self._collapse()
        else:
            self._expand()

    # ---------- 그리기 / 입력 ----------
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
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        s = self._size
        shadow_pad = self.SHADOW_PAD
        body = QRectF(shadow_pad, shadow_pad, s, s)
        radius = s * self.CORNER_RATIO
        bg = QColor(self.ICON_BG_COLOR)
        if self._hover:
            bg = bg.lighter(112)
        painter.setPen(Qt.NoPen)
        _paint_soft_shadow(painter, body, radius, shadow_pad)
        painter.setBrush(bg)
        painter.drawRoundedRect(body, radius, radius)

        inset = s * 0.24
        icon_rect = body.adjusted(inset, inset, -inset, -inset)
        if not self._icon.isNull():
            painter.drawPixmap(icon_rect.toRect(), self._icon)
