# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025-2026 Dinakaran Ganesan
# Copyright (c) 2026 Tony Tian (CATK)

"""
The CATK brand mark at the right end of the status bar, rendered in the colours
of the light or dark window theme. Because the top row replaces the window title
bar, this badge identifies the application and shows its version in a tooltip.

Original CATK vector artwork ("CAN bus steps -> decoded waveform" beside bold
geometric CATK letterforms), defined inline so every build stays self-contained
without relying on external image assets or upstream brand marks.
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QProxyStyle, QStatusBar, QStyle, QStyleFactory, QWidget

# Palette entries for dark and light themes: frame ring, step trace & wordmark
# ink, decoded signal accent, and telemetry indicator bars.
DARK_COLOURS = {'ring': '#5E7A96', 'ink': '#E8EEF5', 'signal': '#3FB6FF', 'tagline': '#7FA6C8'}
LIGHT_COLOURS = {'ring': '#9FB1C4', 'ink': '#0D1B2A', 'signal': '#1F7AE0', 'tagline': '#5B6B7C'}

# Proportions from the SVG viewBox.
_WIDTH, _HEIGHT = 440, 76
# Horizontal margin on each side of the drawing.
_MARGIN = 6

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 76" width="1760" height="304">'
    '<title>CATK</title>'
    '<rect x="10" y="10" width="72" height="56" rx="14" ry="14" '
    'fill="none" stroke="{ring}" stroke-width="5.5"/>'
    '<path d="M20 50 H28 V34 H36 V50 H44 V34 H48" '
    'fill="none" stroke="{ink}" stroke-width="5.5" stroke-linejoin="round" stroke-linecap="round"/>'
    '<path d="M48 34 C54 34 56 23 62 23 C68 23 68 50 74 50" '
    'fill="none" stroke="{signal}" stroke-width="5.5" stroke-linejoin="round" stroke-linecap="round"/>'
    '<path fill="{ink}" d="'
    'M150 14 H104 V62 H150 V51 H116 V25 H150 Z '
    'M164 62 L182 14 H196 L214 62 H201 L197 49 H181 L177 62 Z '
    'M184 39 H194 L189 24 Z '
    'M224 14 H274 V25 H255 V62 H243 V25 H224 Z '
    'M288 14 H300 V33 L325 14 H341 L311 38 L341 62 H325 L300 43 V62 H288 Z"/>'
    '<rect x="358" y="18" width="4" height="40" rx="2" fill="{tagline}"/>'
    '<rect x="372" y="20" width="56" height="8" rx="4" fill="{tagline}"/>'
    '<rect x="372" y="34" width="42" height="8" rx="4" fill="{signal}"/>'
    '<rect x="372" y="48" width="50" height="8" rx="4" fill="{tagline}"/>'
    '</svg>'
)


def logo_svg(colours: dict[str, str]) -> str:
    """The logo's SVG in *colours*: DARK_COLOURS or LIGHT_COLOURS."""
    return _SVG.format(**colours)


class BrandLogo(QWidget):
    """The logo at a fixed height, in the colours of the window's theme.
    Drawn from the SVG at every paint, so it stays sharp at any display
    scale, and a palette change repaints it in the other theme's colours."""

    def __init__(self, height: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._logo_size = QSize(round(height * _WIDTH / _HEIGHT), height)
        self.setFixedSize(self._logo_size.width() + 2 * _MARGIN, height)
        self.setAccessibleName('CATK logo')
        # One renderer per theme, parsed when that theme is first drawn.
        self._renderers: dict[bool, QSvgRenderer] = {}

    def colours(self) -> dict[str, str]:
        """The colours for the window's theme, as the plot icons judge it."""
        dark = self.palette().color(QPalette.ColorRole.Window).lightness() < 128
        return DARK_COLOURS if dark else LIGHT_COLOURS

    def paintEvent(self, event) -> None:
        colours = self.colours()
        dark = colours is DARK_COLOURS
        renderer = self._renderers.get(dark)
        if renderer is None:
            renderer = QSvgRenderer(QByteArray(logo_svg(colours).encode()))
            self._renderers[dark] = renderer
        painter = QPainter(self)
        renderer.render(painter, QRectF(_MARGIN, 0, self._logo_size.width(),
                                        self._logo_size.height()))


class StatusBarStyle(QProxyStyle):
    """The status bar's style, less the lines beside the logo: the logo
    stands on its own, and with the panels closed a line beside it looked
    out of place. Windows draws each item's line at its right edge, so the
    logo's own line is left out, and that of the item just before it."""

    def drawPrimitive(self, element, option, painter, widget=None) -> None:
        if element == QStyle.PrimitiveElement.PE_FrameStatusBarItem and _beside_logo(widget):
            return
        super().drawPrimitive(element, option, painter, widget)


def _beside_logo(widget: QWidget | None) -> bool:
    """Whether *widget* is the logo or the status bar item right before it."""
    if widget is None or isinstance(widget, BrandLogo):
        return widget is not None
    parent = widget.parentWidget()
    if parent is None:
        return False
    right = widget.geometry().right()
    # The status bar's layout leaves a few pixels between its items.
    return any(logo.isVisible() and 0 < logo.x() - right <= 2 * _MARGIN
               for logo in parent.findChildren(BrandLogo, options=Qt.FindChildOption.FindDirectChildrenOnly))


def leave_logo_unframed(status_bar: QStatusBar) -> None:
    """Give *status_bar* the application's style without the line beside the
    logo. The status bar owns the style; its items keep the application's."""
    base = QStyleFactory.create(QApplication.style().name())
    if base is None:
        return
    style = StatusBarStyle(base)
    style.setParent(status_bar)
    status_bar.setStyle(style)
