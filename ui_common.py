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
    QFrame,
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


FONT_FAMILY = "Noto Sans KR"


def load_custom_font():
    """폰트가 안 깔린 PC를 위해 번들해 둔 NotoSansKR-Regular.ttf를 등록합니다.

    이미 시스템에 FONT_FAMILY가 깔려 있으면 등록하지 않습니다. Regular 하나뿐인
    파일을 등록하면 Qt가 그 패밀리를 Regular만 가진 것으로 덮어써서, 시스템에 같이
    깔려 있던 진짜 Bold 자족까지 가려집니다. 그러면 굵은 글씨가 전부 '가짜 볼드'로
    그려져 작은 크기에서 뭉개집니다(자세한 건 아래 kfont 주석)."""
    if FONT_FAMILY in QFontDatabase.families():
        return

    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_path, "assets", "fonts", "NotoSansKR-Regular.ttf")
    if os.path.exists(font_path):
        QFontDatabase.addApplicationFont(font_path)


FONT_SCALE = 0.85

# 굵은 글씨에 진짜 굵은 자족(Bold/Medium)을 쓰기 위한 장치.
#
# 쓸 수 있는 자족이 없는데 setBold(True)를 하면 Qt가 획을 옆으로 덧그려 '가짜 볼드'를
# 만듭니다. FONT_SCALE 때문에 8~10pt까지 작아진 글자에서는 획끼리 붙고 속공간이 메워져
# 뭉개지고 흐릿해 보입니다(작은 버튼 글자, 단말 정보 카드 등).
#
# FONT_FAMILY("Noto Sans KR")에 진짜 Bold가 있는지는 실행 환경마다 다릅니다. 시스템에
# Noto Sans KR 전체 굵기가 깔려 있으면 있고, assets/fonts의 Regular 하나만 등록된
# 상태(폰트 미설치 PC, 빌드 배포본)면 없습니다. 그래서 고정하지 않고 실행 시점에
# 확인해서 정합니다.
#
# 아래는 FONT_FAMILY에 Bold가 없을 때 대신 쓸 (패밀리, setBold를 걸어야 하는지) 후보로,
# 앞에서부터 시스템에 있는 첫 번째를 씁니다.
BOLD_FAMILY_CANDIDATES = (
    # Noto Sans KR의 진짜 Medium 자족. 자폭이 Regular와 같아 레이아웃이 그대로입니다.
    # 굵기가 패밀리 자체에 들어 있어서 setBold를 또 걸면 안 됩니다(다시 가짜 볼드).
    ("Noto Sans KR Medium", False),
    # Noto 굵은 자족이 하나도 없는 PC용 대비책. 윈도우에 항상 있고 진짜 Bold가 있습니다.
    ("Malgun Gothic", True),
)

_UNRESOLVED = object()
_bold_family = _UNRESOLVED


def _has_real_bold(family):
    return any(QFontDatabase.bold(family, style) for style in QFontDatabase.styles(family))


def _bold_font_family():
    """굵은 글씨에 쓸 (패밀리, setBold 여부).

    QFontDatabase는 QApplication이 만들어진 뒤에만 쓸 수 있어서(=import 시점엔 못 씀)
    처음 필요할 때 한 번만 찾아 캐시합니다. 아무 후보도 없으면 FONT_FAMILY + 가짜
    볼드로 떨어집니다(예전 동작)."""
    global _bold_family
    if _bold_family is _UNRESOLVED:
        if _has_real_bold(FONT_FAMILY):
            # 이게 제일 좋습니다. 같은 패밀리의 진짜 Bold(700)를 그대로 씁니다.
            _bold_family = (FONT_FAMILY, True)
        else:
            available = set(QFontDatabase.families())
            _bold_family = next(
                ((fam, needs_bold) for fam, needs_bold in BOLD_FAMILY_CANDIDATES if fam in available),
                (FONT_FAMILY, True),
            )
    return _bold_family


def kfont(size, bold=False):
    family, synthesize_bold = _bold_font_family() if bold else (FONT_FAMILY, False)

    f = QFont(family, max(8, round(size * FONT_SCALE)))
    f.setBold(synthesize_bold)
    # 예전에 쓰던 Pretendard-Regular.otf(자체 힌팅 명령이 없는 CFF 윤곽선)에서, 작은
    # 크기에서 "그"의 "ㅡ" 같은 얇은 가로 획이 그리드 피팅 과정에서 통째로 사라지는
    # 문제가 있었습니다. 안티앨리어싱 전략만으로는 부족해서(그리드 피팅 자체가 얇은
    # 획을 픽셀 경계 밖으로 밀어내 버림), 힌팅(그리드 피팅)을 아예 꺼서 윤곽선을 있는
    # 그대로(살짝 흐릿하더라도) 그리도록 합니다. 지금 쓰는 NotoSansKR-Regular.ttf에도
    # 안전하게 유지합니다.
    #
    # (NoAntialias로 바꿔서 색번짐을 없애보려 한 적이 있는데, 실제 화면 DPI
    # 스케일링에서 글씨가 찌그러져 보여서 되돌렸습니다 — 스크린샷 테스트만으론
    # 못 잡아낸 회귀였습니다. 색번짐 자체는 남아있을 수 있습니다.)
    f.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
    f.setHintingPreference(QFont.PreferNoHinting)
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
# 🌐 [Navy Web Theme] — 웹 어드민 느낌의 네이비 톤
# ==========================================
class Navy:
    """'웹 같은 느낌 + 네이비톤'으로 새로 입힌 화면들이 공통으로 쓰는 색/치수 토큰.

    밝은 회청색 바닥(bg) 위에 흰 카드(surface)를 올리고, 제목·선택 상태·기본
    버튼에만 진한 네이비(navy)를 쓰는 구성입니다. 지금은 모든 화면과 창 껍데기가
    이 토큰을 쓰며, 아래의 Palette(예전 파스텔 라벤더)는 참조하는 코드가 없습니다."""

    bg = "#F5F7FA"              # 페이지 바닥
    surface = "#FFFFFF"         # 카드
    surface_alt = "#F8FAFC"     # 카드 안에서 한 단 가라앉는 영역(코드 뷰 등)
    surface_sunken = "#F1F5F9"  # hover / 연한 구분 배경
    border = "#E3E8F0"
    border_strong = "#CBD5E1"

    navy = "#1B2A4A"            # 제목·기본 버튼
    navy_hover = "#24375F"
    navy_pressed = "#14203A"

    accent = "#2E5AAC"          # 링크/활성 표시용 파랑
    accent_hover = "#26509B"
    accent_soft = "#EEF3FB"     # 선택된 행 배경
    accent_soft_hover = "#E2EAF8"

    text = "#1B2A4A"
    text_sub = "#5A6B85"
    text_muted = "#93A0B5"
    text_on_navy = "#FFFFFF"

    danger = "#C2405A"
    danger_soft = "#FCF0F3"
    success = "#1E8A60"

    disabled_bg = "#E8EDF4"
    disabled_fg = "#A8B4C6"

    radius = 12
    radius_sm = 8

    mono_families = ["JetBrains Mono", "Cascadia Mono", "D2Coding", "Consolas"]


def navy_card_css(bg=Navy.surface, border=Navy.border, radius=Navy.radius):
    """그림자 없이 1px 테두리로만 떠 있는 평평한 카드(요즘 웹 어드민 스타일)."""
    return f"background-color:{bg}; border:1px solid {border}; border-radius:{radius}px;"


def navy_card(bg=Navy.surface, border=Navy.border, radius=Navy.radius):
    """웹 어드민 카드 하나(QFrame).

    스타일시트를 #navyCard로 좁혀두는 게 핵심입니다. 선택자 없이 그냥 주면 Qt가
    카드 안의 자식 위젯들에게까지 같은 배경/테두리를 물려줘서, 속에 넣은 빈
    컨테이너(QWidget)마다 네모 테두리가 생기고 버튼 색까지 덮어쓰입니다."""
    card = QFrame()
    card.setObjectName("navyCard")
    return styled(card, f"QFrame#navyCard {{ {navy_card_css(bg, border, radius)} }}")


def navy_mono_font(size=11, bold=False):
    f = QFont()
    f.setFamilies(Navy.mono_families)
    f.setPointSize(size)
    f.setBold(bold)
    return f


def navy_btn_css(kind="primary", radius=Navy.radius_sm, padding="0 14px"):
    """웹 버튼 느낌의 QPushButton QSS.

    primary : 단색 네이비 채움 (저장 등 주액션)
    accent  : 파란 채움 (같은 화면에서 primary와 구분해야 하는 실행성 액션)
    ghost   : 흰 바탕 + 테두리 (보조 액션)
    quiet   : 배경 없이 글자만 (hover에서만 살짝)
    danger  : 삭제성 액션
    """
    if kind == "accent":
        bg, fg, hover, pressed, border = (
            Navy.accent, Navy.text_on_navy, Navy.accent_hover, "#1F447F", "transparent")
    elif kind == "ghost":
        bg, fg, hover, pressed, border = (
            Navy.surface, Navy.text, Navy.accent_soft, Navy.accent_soft_hover, Navy.border_strong)
    elif kind == "quiet":
        bg, fg, hover, pressed, border = (
            "transparent", Navy.text_sub, Navy.surface_sunken, Navy.border, "transparent")
    elif kind == "danger":
        bg, fg, hover, pressed, border = (
            Navy.danger_soft, Navy.danger, "#F8E2E7", "#F2D5DC", "#F0D2D9")
    else:
        bg, fg, hover, pressed, border = (
            Navy.navy, Navy.text_on_navy, Navy.navy_hover, Navy.navy_pressed, "transparent")

    # 굵기는 navy_button이 setFont(kfont(..., True))로 정합니다. 여기서 font-weight를
    # 또 지정하면 QSS가 이겨서, kfont가 골라둔 진짜 굵은 자족 대신 가짜 볼드가 그려집니다.
    return (
        f"QPushButton {{ background-color:{bg}; color:{fg}; border:1px solid {border}; "
        f"border-radius:{radius}px; padding:{padding}; }}"
        f"QPushButton:hover {{ background-color:{hover}; }}"
        f"QPushButton:pressed {{ background-color:{pressed}; }}"
        f"QPushButton:disabled {{ background-color:{Navy.disabled_bg}; color:{Navy.disabled_fg}; "
        f"border-color:transparent; }}"
    )


def navy_button(text, kind="primary", height=32, icon_name=None, icon_color=None, icon_size=13):
    btn = QPushButton(text)
    btn.setFixedHeight(height)
    btn.setFont(kfont(11, True))
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(navy_btn_css(kind))
    if icon_name:
        default_icon_color = Navy.text_on_navy if kind == "primary" else Navy.navy
        btn.setIcon(qta.icon(icon_name, color=icon_color or default_icon_color))
        btn.setIconSize(QSize(icon_size, icon_size))
    return btn


class NavListButton(QPushButton):
    """웹 사이드 메뉴의 목록 행처럼 생긴 토글 버튼.

    글자는 왼쪽 정렬이고, 선택되면 연한 파랑 배경이 깔리면서 왼쪽에 네이비 막대가
    생깁니다. border-left를 평소에도 3px(투명)로 잡아두고 색만 바꿔서, 선택할 때
    글자가 옆으로 밀리지 않게 했습니다."""

    def __init__(self, text, height=34, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(height)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(kfont(11))
        self.setStyleSheet(
            f"QPushButton {{ background-color:transparent; color:{Navy.text_sub}; border:none; "
            f"border-left:3px solid transparent; border-radius:{Navy.radius_sm}px; "
            f"padding-left:10px; padding-right:8px; text-align:left; font-weight:500; }}"
            f"QPushButton:hover {{ background-color:{Navy.surface_sunken}; color:{Navy.text}; }}"
            f"QPushButton:checked {{ background-color:{Navy.accent_soft}; color:{Navy.navy}; "
            f"border-left-color:{Navy.navy}; font-weight:700; }}"
            f"QPushButton:checked:hover {{ background-color:{Navy.accent_soft_hover}; }}"
        )


def navy_pill(text, fg=Navy.accent, bg=Navy.accent_soft):
    """개수 배지처럼 쓰는 작은 알약 라벨."""
    lbl = QLabel(str(text))
    lbl.setFont(kfont(9, True))
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setMinimumWidth(22)
    lbl.setFixedHeight(18)
    return styled(lbl, f"background-color:{bg}; color:{fg}; border-radius:9px; padding:0 6px;")


def navy_hline(color=Navy.border, thickness=1):
    line = QWidget()
    line.setFixedHeight(thickness)
    return styled(line, f"background-color:{color}; border:none;")


def navy_page_css(object_name):
    """페이지 위젯 자기 자신만 칠하는 배경 QSS.

    선택자 없이 배경색을 주면 Qt가 그 페이지 안의 자식 위젯까지 같이 칠해버려서,
    카드 안 빈 컨테이너마다 배경이 덧씌워집니다. id 선택자로 좁혀둡니다."""
    return f"#{object_name} {{ background-color:{Navy.bg}; }}"


def navy_page_header(title_text, subtitle_text=None, actions=None, center_actions=None, right_actions=None):
    """페이지 맨 위 [큰 제목 + 설명] [actions...] .... [center_actions...] .... [right_actions...]
    [오른쪽 breadcrumb] 줄. (holder, breadcrumb_label)을 돌려주며, breadcrumb 라벨은 화면
    쪽에서 채웁니다.

    actions는 제목 바로 오른쪽에 붙일 위젯들입니다. center_actions는 제목과 right_actions
    사이 빈 공간(스트레치 두 개 사이)에 놓여, 그 사이 공간 가운데쯤에 위치합니다(예:
    기기 연결 버튼). right_actions는 줄 맨 오른쪽(breadcrumb 바로 왼쪽)에 붙일 위젯들입니다
    (예: 화면 오른쪽 끝에 두고 싶은 드롭다운). 셋 다 제목과 세로 가운데를 맞춰 붙습니다."""
    holder = QWidget()
    row = QHBoxLayout(holder)
    row.setContentsMargins(2, 0, 2, 0)
    row.setSpacing(12)

    col = QVBoxLayout()
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(2)

    title = QLabel(title_text)
    title.setFont(kfont(20, True))
    title.setStyleSheet(f"color:{Navy.navy};")
    col.addWidget(title)

    if subtitle_text:
        subtitle = QLabel(subtitle_text)
        subtitle.setFont(kfont(10))
        subtitle.setStyleSheet(f"color:{Navy.text_sub};")
        col.addWidget(subtitle)

    row.addLayout(col)
    for widget in (actions or []):
        row.addWidget(widget, 0, Qt.AlignVCenter)
    row.addStretch(1)
    for widget in (center_actions or []):
        row.addWidget(widget, 0, Qt.AlignVCenter)
    row.addStretch(1)
    for widget in (right_actions or []):
        row.addWidget(widget, 0, Qt.AlignVCenter)

    breadcrumb = QLabel("")
    breadcrumb.setFont(kfont(10, True))
    breadcrumb.setStyleSheet(f"color:{Navy.text_muted};")
    row.addWidget(breadcrumb, 0, Qt.AlignVCenter)
    return holder, breadcrumb


def navy_card_header(text, badge=None, actions=None):
    """카드 맨 위 [작은 제목 + 개수 배지 ... (오른쪽 버튼들)] + 밑줄 한 줄.
    (header_widget, badge_label)을 돌려주고, badge=None이면 배지는 만들지 않습니다."""
    holder = QWidget()
    box = QVBoxLayout(holder)
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(10)

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)

    title = QLabel(text)
    font = kfont(10, True)
    font.setLetterSpacing(QFont.AbsoluteSpacing, 0.6)
    title.setFont(font)
    title.setStyleSheet(f"color:{Navy.text_muted};")
    row.addWidget(title)

    badge_lbl = None
    if badge is not None:
        badge_lbl = navy_pill(badge)
        row.addWidget(badge_lbl)
    row.addStretch(1)
    for widget in (actions or []):
        row.addWidget(widget)

    box.addLayout(row)
    box.addWidget(navy_hline())
    return holder, badge_lbl


class FolderHeaderRow(QWidget):
    """폴더로 묶은 목록(저장된 객체 / 저장된 시나리오)에서 폴더 한 줄.

    평소엔 펼침/접힘 화살표와 이름만 보이다가, 마우스를 올리면 오른쪽에 수정/삭제
    버튼이 나타납니다. 기본 폴더는 이름은 바꿀 수 있지만(계속 기본 폴더 역할은
    유지) 삭제는 못 하므로, 부르는 쪽에서 can_delete=False를 줍니다."""

    toggled = Signal()
    editRequested = Signal(str)
    deleteRequested = Signal(str)

    def __init__(self, folder, label_text, can_edit=True, can_delete=True,
                 delete_tooltip="폴더 삭제 (하위 항목 포함)", collapsed=False, parent=None):
        super().__init__(parent)
        self._folder = folder
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)

        # 예전엔 펼침/접힘을 ▶/▼ 화살표 글자로 표시했지만, 폴더라는 걸 바로 알아보게
        # 폴더 아이콘으로 바꿨습니다(접힘: 닫힌 폴더, 펼침: 열린 폴더).
        icon_lbl = QLabel()
        icon_lbl.setPixmap(
            qta.icon("fa5s.folder" if collapsed else "fa5s.folder-open", color=Navy.text).pixmap(14, 14)
        )
        layout.addWidget(icon_lbl)

        self._label = QLabel(label_text)
        # 폴더 이름은 목록을 훑을 때 제일 먼저 읽는 글자입니다. 예전엔 text_muted
        # (#93A0B5)라 흰 배경에서 대비가 거의 없어 잘 안 보였습니다.
        # (FONT_SCALE 0.85 때문에 9와 10은 둘 다 8pt로 떨어집니다. 한 단계 키우려면 11.)
        self._label.setFont(kfont(11, True))
        self._label.setStyleSheet(f"color:{Navy.text};")
        self._label.setToolTip(label_text)
        layout.addWidget(self._label, 1)

        self._can_edit = can_edit
        self._can_delete = can_delete

        self._btn_edit = navy_button("", kind="ghost", height=22, icon_name="fa5s.pen", icon_size=10)
        self._btn_edit.setFixedWidth(24)
        self._btn_edit.setToolTip("폴더 이름 수정")
        self._btn_edit.clicked.connect(lambda: self.editRequested.emit(self._folder))
        self._btn_edit.setVisible(False)
        layout.addWidget(self._btn_edit)

        self._btn_delete = navy_button("", kind="danger", height=22, icon_name="fa5s.trash-alt", icon_size=10)
        self._btn_delete.setFixedWidth(24)
        self._btn_delete.setToolTip(delete_tooltip)
        self._btn_delete.clicked.connect(lambda: self.deleteRequested.emit(self._folder))
        self._btn_delete.setVisible(False)
        layout.addWidget(self._btn_delete)

    def enterEvent(self, event):
        if self._can_edit:
            self._btn_edit.setVisible(True)
        if self._can_delete:
            self._btn_delete.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._btn_edit.setVisible(False)
        self._btn_delete.setVisible(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            event.accept()
            self.toggled.emit()
            return
        super().mousePressEvent(event)


def navy_section_header(text):
    """목록 안에서 묶음을 나누는 작은 구분 제목(라벨 + 남는 폭을 채우는 가는 선)."""
    holder = QWidget()
    row = QHBoxLayout(holder)
    row.setContentsMargins(3, 10, 3, 4)
    row.setSpacing(8)

    lbl = QLabel(text)
    # 묶음 이름도 폴더 이름과 같은 이유로 옅은 회색(text_muted) 대신 본문 색을 씁니다.
    font = kfont(11, True)
    font.setLetterSpacing(QFont.AbsoluteSpacing, 0.5)
    lbl.setFont(font)
    lbl.setStyleSheet(f"color:{Navy.text};")
    row.addWidget(lbl)
    row.addWidget(navy_hline(), 1)
    return holder


def navy_scrollbar_css():
    """전역 QSS(ui_logic._global_qss의 예전 라벤더 톤) 위에 덮어씌우는 네이비 스크롤바.
    위젯 단위 스타일시트에 이어붙여 씁니다."""
    return (
        f"QScrollBar:vertical {{ background:transparent; width:10px; margin:6px 4px 6px 0; }}"
        f"QScrollBar::handle:vertical {{ background:{Navy.border_strong}; border-radius:5px; min-height:28px; }}"
        f"QScrollBar::handle:vertical:hover {{ background:{Navy.text_muted}; }}"
        f"QScrollBar:horizontal {{ background:transparent; height:10px; margin:0 6px 4px 6px; }}"
        f"QScrollBar::handle:horizontal {{ background:{Navy.border_strong}; border-radius:5px; min-width:28px; }}"
        f"QScrollBar::handle:horizontal:hover {{ background:{Navy.text_muted}; }}"
        f"QScrollBar::add-line, QScrollBar::sub-line {{ width:0; height:0; }}"
        f"QScrollBar::add-page, QScrollBar::sub-page {{ background:none; }}"
    )


def navy_input_css(radius=Navy.radius_sm):
    """QLineEdit / QComboBox / QPlainTextEdit 공통 입력 상자 스타일."""
    return (
        f"QLineEdit, QComboBox, QPlainTextEdit {{ background-color:{Navy.surface}; color:{Navy.text}; "
        f"border:1px solid {Navy.border_strong}; border-radius:{radius}px; padding:5px 10px; }}"
        f"QLineEdit:hover, QComboBox:hover, QPlainTextEdit:hover {{ border-color:{Navy.accent}; }}"
        f"QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{ border:1px solid {Navy.accent}; }}"
        f"QLineEdit:disabled, QComboBox:disabled, QPlainTextEdit:disabled {{ background-color:{Navy.surface_sunken}; "
        f"color:{Navy.text_muted}; border-color:{Navy.border}; }}"
        f"QComboBox::drop-down {{ border:none; width:22px; }}"
        f"QComboBox QAbstractItemView {{ background-color:{Navy.surface}; color:{Navy.text}; "
        f"border:1px solid {Navy.border}; border-radius:{radius}px; outline:none; padding:2px; "
        f"selection-background-color:{Navy.accent_soft}; selection-color:{Navy.navy}; }}"
    )


def navy_list_css(radius=Navy.radius_sm):
    """QListWidget 목록 스타일(행 hover / 선택 표시까지)."""
    return (
        f"QListWidget {{ background-color:{Navy.surface}; color:{Navy.text}; "
        f"border:1px solid {Navy.border}; border-radius:{radius}px; padding:4px; outline:none; }}"
        f"QListWidget::item {{ padding:3px 8px; border-radius:6px; }}"
        f"QListWidget::item:hover {{ background-color:{Navy.surface_sunken}; }}"
        f"QListWidget::item:selected {{ background-color:{Navy.accent_soft}; color:{Navy.navy}; }}"
    ) + navy_scrollbar_css()


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
    groups_ready = Signal(list)


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
        width = min(1280, max(900, geo.width() - launcher_lane - margin * 2))
        height = min(860, max(600, geo.height() - margin * 2))
        window.resize(width, height)
        y = geo.top() + max(margin, (geo.height() - height) // 2)
        window.move(geo.left() + margin, y)
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
    """런처 아이콘 옆으로 펼쳐지는 메뉴 박스 하나. 메인 런처 아이콘과 같은 56x56
    정사각형(살짝만 둥근 네모)에 같은 네이비 배경을 쓰고, 라벨이 있으면 아이콘
    아래에 흰 글씨로 적습니다. 프레임 없는 항상-위 위젯이라 화면 위에 독립적으로
    떠 있습니다.

    예전에는 글자를 아이콘 오른쪽에 붙여서 박스가 이름 길이만큼 가로로 늘어났는데,
    메뉴가 여러 개일 때 길이가 제각각이라 메인 런처와 크기를 맞춰 정사각형으로
    통일했습니다. 좁은 폭에 안 들어가는 이름은 잘라서 표시하고(툴팁에 전체 이름),
    두 줄까지 접어 씁니다.

    QGraphicsDropShadowEffect는 반투명 최상위 창에서 Windows의
    UpdateLayeredWindowIndirect 오류를 내므로, 그림자는 paintEvent에서 직접 그립니다."""

    clicked = Signal()

    CORNER_RATIO = 0.12
    SHADOW_PAD = 3
    TEXT_H_PADDING = 4    # 글자가 박스 모서리에 닿지 않도록 두는 좌우 여백
    ICON_TEXT_GAP = 3
    TOP_PADDING_RATIO = 0.14

    def __init__(self, text, color=None, size=56, icon_name=None, show_label=True):
        super().__init__(None)
        self._size = size
        self._color = QColor(color or Navy.navy)
        self._hover = False
        self._text = text
        self._show_label = bool(show_label and text)
        self._font = kfont(8, True)

        # 아이콘 없이 이름만 보여주는 박스도 있습니다(icon_name=None). 그때는 글자가
        # 박스 전체를 쓰므로 긴 이름도 좀 더 들어갑니다.
        # 글자를 같이 넣는 박스는 아이콘을 조금 줄여 위쪽에 놓고 아래를 글자에 내줍니다.
        if icon_name:
            icon_px = round(size * (0.30 if self._show_label else 0.42))
            self._icon = qta.icon(icon_name, color="#FFFFFF").pixmap(QSize(icon_px, icon_px))
        else:
            icon_px = 0
            self._icon = None
        self._icon_px = icon_px
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
        icon_x = pad + (self._box_w - icon_px) / 2
        if not self._show_label:
            if self._icon is not None:
                painter.drawPixmap(
                    QRectF(icon_x, pad + (self._size - icon_px) / 2, icon_px, icon_px).toRect(),
                    self._icon,
                )
            return

        if self._icon is not None:
            icon_y = pad + self._size * self.TOP_PADDING_RATIO
            painter.drawPixmap(QRectF(icon_x, icon_y, icon_px, icon_px).toRect(), self._icon)
            text_top = icon_y + icon_px + self.ICON_TEXT_GAP
            text_align = Qt.AlignHCenter | Qt.AlignTop
        else:
            # 아이콘이 없으면 글자를 박스 한가운데에 놓습니다.
            text_top = pad + 4
            text_align = Qt.AlignCenter

        text_rect = QRectF(
            pad + self.TEXT_H_PADDING,
            text_top,
            self._box_w - self.TEXT_H_PADDING * 2,
            body.bottom() - text_top - 2,
        )
        painter.setFont(self._font)
        painter.setPen(QColor("#FFFFFF"))
        # 두 줄까지만 쓰도록 미리 잘라둡니다. 안 자르면 넘치는 글자가 박스 밖에서
        # 잘려 반 토막 난 글리프가 보입니다(전체 이름은 툴팁에 있습니다).
        metrics = QFontMetrics(self._font)
        max_lines = 2 if self._icon is not None else 3
        elided = metrics.elidedText(
            self._text, Qt.ElideRight, int(text_rect.width() * max_lines)
        )
        # TextWrapAnywhere까지 주는 이유: "450connect"처럼 띄어쓰기가 없는 이름은
        # 단어 경계만 보는 줄바꿈으로는 줄이 안 나눠져 박스 밖으로 넣어나가 양쪽이 잘립니다.
        painter.drawText(
            text_rect,
            text_align | Qt.TextWordWrap | Qt.TextWrapAnywhere,
            elided,
        )


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

    QA_COLOR = Navy.navy   # 메뉴 박스는 메인 런처와 같은 네이비로 통일
    BADGE_SIZE = 56
    BADGE_GAP = 3
    ANIM_MS = 180

    ICON_BG_COLOR = Navy.navy
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
                icon_name=item.get("icon"),   # None이면 아이콘 없이 이름만
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
