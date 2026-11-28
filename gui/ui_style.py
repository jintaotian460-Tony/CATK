# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Tony Tian (CATK)

"""Unified, calm light-chrome visual tokens and scoped QSS for CATK."""
from __future__ import annotations

from gui import observation_style

SURFACE = '#f6f7f9'
SURFACE_ALT = '#f1f3f6'
CARD = '#ffffff'
BORDER = '#dde2e8'
CONTROL_BORDER = '#cfd6df'
CONTROL_HOVER_BORDER = '#9eb3c9'
ACCENT = '#2b5b84'
ACCENT_HOVER = '#234c6f'
ACCENT_SOFT = '#e6eff7'
ACCENT_SOFT_TEXT = '#1d4363'
ACCENT_SOFT_BORDER = '#b3cbe0'
INK = '#1e242c'
INK_SECONDARY = '#576270'
INK_MUTED = '#8a94a0'
DANGER = '#b91c1c'
DANGER_SOFT = '#fef2f2'
DANGER_BORDER = '#fecaca'

_SCROLLBAR_QSS = f'''
QScrollBar:vertical {{
    background: transparent;
    width: 9px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: #94a3b8;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
    height: 0px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 9px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #cbd5e1;
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #94a3b8;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
    width: 0px;
}}
'''

_INPUT_AND_COMBO_QSS = f'''
QLineEdit, QPlainTextEdit, QTextEdit {{
    background: {CARD};
    color: {INK};
    border: 1px solid {CONTROL_BORDER};
    border-radius: 5px;
    padding: 4px 8px;
    selection-background-color: {ACCENT_SOFT};
    selection-color: {INK};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {ACCENT};
}}
QComboBox {{
    background: {CARD};
    color: {INK};
    border: 1px solid {CONTROL_BORDER};
    border-radius: 5px;
    padding: 3px 22px 3px 8px;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: {CONTROL_HOVER_BORDER};
}}
QComboBox:focus {{
    border-color: {ACCENT};
}}
QComboBox:disabled {{
    background: {SURFACE_ALT};
    color: {INK_MUTED};
    border-color: {BORDER};
}}
QComboBox::drop-down {{
    border: none;
    width: 18px;
}}
QComboBox QAbstractItemView {{
    background: {CARD};
    color: {INK};
    border: 1px solid {CONTROL_BORDER};
    selection-background-color: {ACCENT_SOFT};
    selection-color: {ACCENT_SOFT_TEXT};
}}
'''

MAIN_WINDOW_QSS = f'''
QMainWindow {{
    background: {SURFACE};
}}
QMainWindow::separator {{
    width: 1px;
    height: 1px;
    background: {BORDER};
}}
QDockWidget {{
    border: none;
}}
{_SCROLLBAR_QSS}
'''

TITLE_BAR_QSS = f'''
QWidget#titleRow {{
    background: {SURFACE};
    border-bottom: 1px solid {BORDER};
}}
QToolBar {{
    background: transparent;
    border: none;
    spacing: 2px;
    padding: 2px 4px;
}}
QToolBar::separator {{
    background: #d8dfe7;
    width: 1px;
    margin: 6px 5px;
}}
QToolButton {{
    background: transparent;
    color: {INK};
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 4px 8px;
}}
QToolButton:hover {{
    background: #eaf0f6;
    border-color: #cfdbe7;
}}
QToolButton:pressed {{
    background: #dce7f2;
}}
QToolButton:checked {{
    background: {ACCENT_SOFT};
    color: {ACCENT_SOFT_TEXT};
    border: 1px solid {ACCENT_SOFT_BORDER};
}}
QToolButton:checked:hover {{
    background: #d8e7f4;
}}
QToolButton:disabled {{
    color: {INK_MUTED};
}}
QToolButton::menu-indicator {{
    subcontrol-origin: padding;
    subcontrol-position: right center;
    right: 4px;
}}
QToolButton[popupMode="2"] {{
    padding-right: 16px;
}}
'''

DOCK_TITLE_QSS = f'''
QWidget#dockTitleBar {{
    background: {SURFACE_ALT};
    border-bottom: 1px solid {BORDER};
}}
QWidget#dockTitleBar QLabel {{
    color: #334155;
    font-size: 12px;
    font-weight: 600;
    padding: 2px 2px;
}}
QWidget#dockTitleBar QToolButton {{
    background: transparent;
    color: {INK_SECONDARY};
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 1px 5px;
    min-width: 20px;
    min-height: 20px;
}}
QWidget#dockTitleBar QToolButton:hover {{
    background: #e2e8f0;
    color: {INK};
}}
'''

PLOT_TOOLBAR_QSS = observation_style.CONTROLS + f'''
QWidget#plotButtonRow {{
    background: {SURFACE};
    border-bottom: 1px solid {BORDER};
}}
'''

PLAYBACK_BAR_QSS = observation_style.CONTROLS + _INPUT_AND_COMBO_QSS + f'''
QWidget#playbackBar {{
    background: {SURFACE};
    border-bottom: 1px solid #e4e8ee;
}}
QLabel#projectBadge {{
    background: {ACCENT_SOFT};
    color: {ACCENT_SOFT_TEXT};
    border: 1px solid {ACCENT_SOFT_BORDER};
    border-radius: 4px;
    padding: 2px 8px;
    font-weight: 600;
}}
QLabel#timeReadout {{
    color: {INK_SECONDARY};
    padding: 0 2px;
}}
'''

LOG_EXPLORER_QSS = observation_style.CONTROLS + _INPUT_AND_COMBO_QSS + f'''
QWidget#LogExplorerPanel {{
    background: {SURFACE};
}}
QLabel#mutedHint {{
    color: {INK_SECONDARY};
    padding: 2px 2px;
}}
QTreeView {{
    background: {CARD};
    color: {INK};
    border: 1px solid {BORDER};
    border-radius: 6px;
    outline: none;
    padding: 2px;
}}
QTreeView::item {{
    min-height: 22px;
    border-radius: 4px;
    padding: 1px 4px;
}}
QTreeView::item:hover:!selected {{
    background: #eef2f6;
}}
QTreeView::item:selected {{
    background: {ACCENT_SOFT};
    color: {ACCENT_SOFT_TEXT};
}}
'''

SIGNAL_TREE_QSS = observation_style.CONTROLS + _INPUT_AND_COMBO_QSS + f'''
QWidget#SignalTreePanel {{
    background: {SURFACE};
}}
QTreeWidget {{
    background: {CARD};
    color: {INK};
    border: 1px solid {BORDER};
    border-radius: 6px;
    outline: none;
}}
QTreeWidget::item {{
    min-height: 21px;
    padding: 1px 4px;
}}
QTreeWidget::item:hover:!selected {{
    background: #eef2f6;
}}
QTreeWidget::item:selected {{
    background: {ACCENT_SOFT};
    color: {ACCENT_SOFT_TEXT};
}}
QHeaderView::section {{
    background: {SURFACE_ALT};
    color: #334155;
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    font-weight: 600;
}}
'''

BOTTOM_TABS_QSS = f'''
QTabWidget#bottomTabs::pane {{
    border: none;
    border-top: 1px solid {BORDER};
    background: {CARD};
}}
QTabWidget#bottomTabs QTabBar::tab {{
    background: transparent;
    color: {INK_SECONDARY};
    padding: 5px 12px;
    border: none;
    border-bottom: 2px solid transparent;
}}
QTabWidget#bottomTabs QTabBar::tab:hover {{
    color: {INK};
    background: #edf1f5;
}}
QTabWidget#bottomTabs QTabBar::tab:selected {{
    color: {ACCENT};
    font-weight: 600;
    border-bottom: 2px solid {ACCENT};
}}
QTabWidget#bottomTabs QTextEdit {{
    background: {CARD};
    color: {INK};
    border: none;
    padding: 6px 8px;
}}
'''

ASSISTANT_PANEL_QSS = observation_style.CONTROLS + _INPUT_AND_COMBO_QSS + f'''
QWidget#AssistantPanel {{
    background: {SURFACE};
    color: {INK};
}}
QFrame#contextCard, QFrame#refCard {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QLabel#sectionTitle {{
    color: {INK};
    font-weight: 600;
}}
QLabel#mutedCaption {{
    color: {INK_SECONDARY};
    font-size: 11px;
}}
QLabel#statusPill {{
    color: {ACCENT_SOFT_TEXT};
    background: {ACCENT_SOFT};
    border-radius: 4px;
    padding: 3px 7px;
    font-size: 11px;
}}
QPushButton#primaryBtn {{
    background: {ACCENT};
    color: #ffffff;
    border: 1px solid {ACCENT};
    border-radius: 5px;
    font-weight: 600;
    padding: 4px 12px;
    min-height: 22px;
}}
QPushButton#primaryBtn:hover {{
    background: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}
QPushButton#primaryBtn:disabled {{
    background: #cbd5e1;
    border-color: #cbd5e1;
    color: #ffffff;
}}
QPushButton#dangerBtn {{
    background: {CARD};
    color: {DANGER};
    border: 1px solid {DANGER_BORDER};
    border-radius: 5px;
    padding: 3px 10px;
    min-height: 22px;
}}
QPushButton#dangerBtn:hover {{
    background: {DANGER_SOFT};
}}
QTabWidget#assistantTabs::pane {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background: {SURFACE};
    margin-top: -1px;
}}
QTabWidget#assistantTabs QTabBar::tab {{
    background: transparent;
    color: {INK_SECONDARY};
    padding: 5px 14px;
    margin-right: 4px;
    border: 1px solid transparent;
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}}
QTabWidget#assistantTabs QTabBar::tab:hover {{
    color: {INK};
    background: #ebeff4;
}}
QTabWidget#assistantTabs QTabBar::tab:selected {{
    background: {CARD};
    color: {ACCENT};
    font-weight: 600;
    border-color: {BORDER};
}}
QListWidget {{
    background: {CARD};
    color: {INK};
    border: 1px solid {CONTROL_BORDER};
    border-radius: 5px;
    outline: none;
    padding: 2px;
}}
QListWidget::item {{
    padding: 4px 6px;
    border-radius: 4px;
}}
QListWidget::item:hover:!selected {{
    background: #eef2f6;
}}
QListWidget::item:selected {{
    background: {ACCENT_SOFT};
    color: {ACCENT_SOFT_TEXT};
}}
'''
