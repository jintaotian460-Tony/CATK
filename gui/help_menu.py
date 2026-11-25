# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025-2026 Dinakaran Ganesan
# Copyright (c) 2026 Tony Tian (CATK)

"""
The top row's Help menu: the user guide, the keyboard shortcuts, the ways to
reach the project, and About.
"""
from __future__ import annotations

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import QMenu, QWidget

from gui import app_data, app_log

REPO_URL = 'https://github.com/jintaotian460-Tony/CATK'
GUIDE_URL = REPO_URL + '/blob/main/guide/'
GETTING_STARTED_URL = GUIDE_URL + 'getting-started.md'
DISCUSSIONS_URL = REPO_URL + '/discussions'
ISSUES_URL = REPO_URL + '/issues'

GUIDE_TEXT = 'Getting started'
GUIDE_TIP = 'The user guide, in your web browser (F1)'
ASK_TEXT = 'Ask a question or share an idea'
ASK_TIP = 'How-to questions, ideas and anything else about the tool, on GitHub Discussions'
REPORT_TEXT = 'Report a problem or request a feature'
REPORT_TIP = 'Problems and feature requests, on GitHub.'
LOGS_TEXT = 'Open the log folder'
LOGS_TIP = 'The two logs to attach to a problem report, in File Explorer'


def open_page(url: str) -> None:
    """Open one of the project's pages in the web browser."""
    QDesktopServices.openUrl(QUrl(url))


def open_log_folder() -> None:
    """Open the running log's folder: the temp folder when it fell back there."""
    running = app_log.log_path()
    folder = running.parent if running is not None else app_data.logs_folder()
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))


class HelpMenu(QMenu):
    """Opens the project's pages itself; the window shows the rest."""

    shortcutsRequested = Signal()
    aboutRequested = Signal()

    def __init__(self, app_name: str, parent: QWidget | None = None) -> None:
        super().__init__('Help', parent)
        self.setToolTipsVisible(True)
        self.guide_action = self._add(GUIDE_TEXT, lambda: open_page(GETTING_STARTED_URL),
                                      GUIDE_TIP)
        # The window holds it too, so that F1 works while the menu is closed.
        self.guide_action.setShortcut(QKeySequence('F1'))
        self.shortcuts_action = self._add('Keyboard shortcuts', self.shortcutsRequested.emit)
        self.addSeparator()
        self.ask_action = self._add(ASK_TEXT, lambda: open_page(DISCUSSIONS_URL), ASK_TIP)
        self.report_action = self._add(REPORT_TEXT, lambda: open_page(ISSUES_URL), REPORT_TIP)
        self.logs_action = self._add(LOGS_TEXT, open_log_folder, LOGS_TIP)
        self.addSeparator()
        self.about_action = self._add(f'About {app_name}', self.aboutRequested.emit)

    def _add(self, text: str, slot, tip: str = '') -> QAction:
        action = self.addAction(text)
        if tip:
            action.setToolTip(tip)
        action.triggered.connect(slot)
        return action
