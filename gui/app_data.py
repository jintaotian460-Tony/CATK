# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2025-2026 Dinakaran Ganesan
# Copyright (c) 2026 Tony Tian (CATK)

r"""Where CATK keeps its logs, settings, and caches.

The packaged application keeps them per user::

    %LOCALAPPDATA%\CATK\
        osvanta_user_settings.json      preferences
        osvanta_temp_plot_config.json   the last plot layout
        logs\
            busloganalyzer_applog.log   the Log panel, warnings, errors
            BLA_crash.log               why the application ended

The logs name every measurement and database opened, and the plot layout
names their signals. Next to the executable, anyone who could read that
folder could read them: a shared tools folder or a network share is common.
Windows lets only the user, and administrators, read their own
%LOCALAPPDATA%. It is also writable without elevation, so an installation in
Program Files no longer sends the logs to the temp folder.

CATK_DATA_DIR (or legacy OSVANTA_DATA_DIR) names another folder, for an IT
department that keeps user data somewhere central. Run from source, everything
stays next to app.py, where developers look for it.

On first launch in %LOCALAPPDATA%\CATK, files from an earlier
%LOCALAPPDATA%\Osvanta\BusLogAnalyzer installation are seeded read-only (copied
without modifying or deleting the original folder), and any legacy files next
to the executable are moved in as before.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

DATA_DIR_ENV_VAR = 'CATK_DATA_DIR'
LEGACY_DATA_DIR_ENV_VAR = 'OSVANTA_DATA_DIR'

_APP_FOLDER = 'CATK'
_LEGACY_VENDOR = 'Osvanta'
_LEGACY_PRODUCT = 'BusLogAnalyzer'
_LOGS = 'logs'

# What versions up to v00.02.02 kept next to the executable, and the folder
# (relative to the data folder) each now belongs in.
_EARLIER_FILES = {
    'osvanta_user_settings.json': '',
    'osvanta_temp_plot_config.json': '',
    'busloganalyzer_applog.log': _LOGS,
    'busloganalyzer_applog.log.1': _LOGS,
    'BLA_crash.log': _LOGS,
    'BLA_crash.log.1': _LOGS,
}

# Settings and caches copied (never moved) from the legacy per-user folder on
# first start so upgrading users keep their preferences without collisions.
_LEGACY_SEED_FILES = (
    'osvanta_user_settings.json',
    'osvanta_temp_plot_config.json',
    'osvanta_last_session.json',
    'assistant-codex-project.txt',
    'assistant-project-agents.json',
    'verified-desktop-versions.json',
)


def _executable_folder() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _local_app_data_root() -> Path:
    local = os.environ.get('LOCALAPPDATA')
    return Path(local) if local else Path.home() / 'AppData' / 'Local'


def legacy_per_user_folder() -> Path:
    """Previous per-user data path from upstream/earlier CATK builds."""
    return _local_app_data_root() / _LEGACY_VENDOR / _LEGACY_PRODUCT


_legacy_per_user_folder = legacy_per_user_folder


def per_user_folder() -> Path:
    """Per-user data path, including for features run from a source checkout."""
    override = os.environ.get(DATA_DIR_ENV_VAR) or os.environ.get(LEGACY_DATA_DIR_ENV_VAR)
    if override:
        return Path(override)
    return _local_app_data_root() / _APP_FOLDER


def folder() -> Path:
    """The settings folder, created, with earlier versions' files migrated.

    Next to app.py when run from source, unless CATK_DATA_DIR / OSVANTA_DATA_DIR is set.
    """
    override = os.environ.get(DATA_DIR_ENV_VAR) or os.environ.get(LEGACY_DATA_DIR_ENV_VAR)
    if not getattr(sys, 'frozen', False) and not override:
        return _executable_folder()
    path = per_user_folder()
    # The logs folder marks the first start, not the folder itself: the
    # licence and add-on folders sit in it too, made by whichever came first.
    if not (path / _LOGS).is_dir():
        try:
            (path / _LOGS).mkdir(parents=True, exist_ok=True)
        except OSError:
            return path  # opening a file there fails, and the caller copes
        if getattr(sys, 'frozen', False):
            _move_earlier_files(_executable_folder(), path)
        if not override:
            _seed_from_legacy_folder(legacy_per_user_folder(), path)
    return path


def logs_folder() -> Path:
    """The logs' folder, created; next to app.py when run from source."""
    base = folder()
    if base == _executable_folder():
        return base
    path = base / _LOGS
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return path


def _seed_from_legacy_folder(legacy: Path, target: Path) -> None:
    """Copy existing preferences/caches from the legacy per-user folder. Never raises."""
    if not legacy.is_dir():
        return
    for name in _LEGACY_SEED_FILES:
        src = legacy / name
        dst = target / name
        try:
            if src.is_file() and not dst.exists():
                shutil.copy2(src, dst)
        except OSError:
            pass


def _move_earlier_files(source: Path, target: Path) -> None:
    """Move what an earlier version left next to the executable. Never raises.

    A file another running copy holds open stays where it is. A move, not a
    rename: the executable may be on another drive than %LOCALAPPDATA%.
    """
    for name, subfolder in _EARLIER_FILES.items():
        old = source / name
        new = target / subfolder / name
        try:
            if not old.is_file() or new.exists():
                continue
            old.replace(new)
        except OSError:
            # Another drive, or held open: copy, and keep the copy only
            # if the original goes, so that each file is in one place.
            try:
                shutil.copy2(old, new)
                old.unlink()
            except OSError:
                new.unlink(missing_ok=True)
