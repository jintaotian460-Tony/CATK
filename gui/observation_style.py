# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Tony Tian (CATK)

"""Scoped presentation for the offline graphic windows."""
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


AXIS_WIDTH = 64
LIST_WIDTH = 320
TEXT = '#1e242c'
MUTED = '#8a94a0'

# These selectors are applied only to the graphic legend and its toolbars.
CONTROLS = '''
QToolButton, QPushButton {
    background: #ffffff; color: #1e242c; border: 1px solid #cfd6df;
    border-radius: 5px; padding: 2px 8px; min-height: 22px;
}
QToolButton:hover, QPushButton:hover { background: #edf3f9; border-color: #9eb3c9; }
QToolButton:pressed, QPushButton:pressed { background: #dfeaf4; }
QToolButton:disabled, QPushButton:disabled {
    background: #f1f3f6; color: #8a94a0; border-color: #dde2e8;
}
QToolButton:checked, QPushButton:checked {
    background: #2b5b84; color: #ffffff; border-color: #2b5b84;
}
QToolButton:checked:hover, QPushButton:checked:hover {
    background: #234c6f; border-color: #234c6f;
}
QToolButton[popupMode="2"] { padding-right: 16px; }
QToolButton::menu-indicator { right: 4px; }
'''
LEGEND = CONTROLS + '''
QWidget#observationLegend { background: #f6f7f9; color: #1e242c; }
QToolButton { background: transparent; border: 1px solid transparent; padding: 1px 4px; }
QToolButton:hover { background: #e3ecf5; border-color: #b3cbe0; }
QTreeWidget { background: #f6f7f9; color: #1e242c; border: none; outline: none; }
QTreeWidget::item { min-height: 22px; border-bottom: 1px solid transparent; padding: 1px 2px; }
QTreeWidget::item:selected { background: #e6eff7; color: #1d4363; border-bottom-color: #b3cbe0; }
QTreeWidget::item:hover:!selected { background: #eef2f6; }
QHeaderView::section { background: #f1f3f6; color: #334155; padding: 3px 6px; font-weight: 600;
    border: none; border-bottom: 1px solid #dde2e8; border-right: 1px solid #dde2e8; }
'''


def swatch(color, line_style='solid'):
    """The line sample keeps bright signal colours readable on a light list."""
    pixmap = QPixmap(22, 12)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    # A dark backing keeps a white/yellow signal distinguishable too.
    painter.fillRect(1, 2, 20, 8, QColor('#30383d'))
    style = {'dash': Qt.PenStyle.DashLine, 'dot': Qt.PenStyle.DotLine,
             'dashdot': Qt.PenStyle.DashDotLine}.get(line_style, Qt.PenStyle.SolidLine)
    painter.setPen(QPen(QColor(color), 2, style))
    painter.drawLine(3, 6, 19, 6)
    painter.end()
    return QIcon(pixmap)


def dark(background):
    c = QColor(background)
    return .299*c.redF() + .587*c.greenF() + .114*c.blueF() < .5


class ObservationGrid:
    """Keep ruler/text pens separate from dotted measurement grid pens."""
    observation_background = None

    def drawPicture(self, painter, axis_spec, ticks, texts):
        if self.observation_background is not None and self.grid:
            adjusted = []
            for pen, first, last in ticks:
                color = QColor('#2e6b40' if dark(self.observation_background) else '#478047')
                color.setAlpha(min(180, max(25, round(pen.color().alpha()*1.6))))
                grid_pen = QPen(color, 1, Qt.PenStyle.DotLine)
                grid_pen.setCosmetic(True)
                adjusted.append((grid_pen, first, last))
            ticks = adjusted
        super().drawPicture(painter, axis_spec, ticks, texts)


class ValueAxis(ObservationGrid, pg.AxisItem):
    def resizeEvent(self, event=None):
        super().resizeEvent(event)
        if self.label is not None and self.orientation == 'left':
            # A row reserves space for the widest independent-axis row. Keep
            # this axis's unit beside its own ticks, not under a neighbouring axis.
            self.label.setX(self.size().width()-AXIS_WIDTH-5)


def style_axes(plot, background):
    for direction in ('left', 'bottom'):
        axis = plot.getAxis(direction)
        axis.observation_background = background
        axis.picture = None
        axis.update()
