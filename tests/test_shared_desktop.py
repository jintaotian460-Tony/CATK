# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import sys
import threading

import pytest

from core.assistant_analysis import AnalysisContext, capture_snapshot
from core.assistant_tools import AnalysisTools
from core.rpc_transport import Cancelled
from core.shared_capture import CaptureLease, UNAVAILABLE, query_capture
from tests.test_assistant_agent_ui import _wait
from tests.test_assistant_tools import ACTUATOR_KEYS, _actuator_store


@pytest.fixture
def snapshot():
    context = AnalysisContext('not-shared.csv', tuple(ACTUATOR_KEYS.values()), 0, 4, '区间')
    return capture_snapshot(_actuator_store(), context)


@pytest.fixture
def capture_listener(monkeypatch):
    from core import shared_capture

    class IdleListener:
        def __init__(self, *args, **kwargs):
            pass

        def accept(self):
            raise OSError

        def close(self):
            pass

    # This isolates lifecycle tests from the Windows pipe sandbox. The
    # native App Server smoke test exercises the real pipe and stdio MCP.
    monkeypatch.setattr(shared_capture, 'Listener', IdleListener)


def test_shared_snapshot_only_issues_scoped_evidence(snapshot, capture_listener, tmp_path):
    lease = CaptureLease(AnalysisTools(snapshot), tmp_path)
    try:
        def call(operation, **arguments):
            return lease._dispatch({'operation': operation, 'arguments': arguments})

        described = call('describe')['data']
        assert 'osvanta_lookup_reference' not in {tool['name'] for tool in described['tools']}
        assert 'not-shared.csv' not in str(call('osvanta_list_signals'))
        assert 'error' in call('osvanta_read_samples', key='other-log::signal')
        assert 'error' in call('osvanta_analyze', start=-1)
        evidence = call('osvanta_compare_events', **ACTUATOR_KEYS)['data']['evidence']
        assert lease.evidence([evidence[0]['id'], 'ev-9999'])[0].source_id == snapshot.context.source_id
        assert lease.evidence(['ev-9999']) == ()
    finally:
        lease.close()
    assert call('describe') == {'error': UNAVAILABLE}
    assert not tuple(tmp_path.iterdir())
    with pytest.raises(ValueError, match=UNAVAILABLE):
        query_capture(tmp_path, lease.scope, 'describe', {})


@pytest.mark.skipif(sys.platform != 'win32', reason='The shared UI is Windows-only')
@pytest.mark.parametrize('reason', ['cancel', 'switch', 'project', 'shutdown'])
def test_shared_chat_revokes_on_scope_exit(qapp, monkeypatch, tmp_path, snapshot, capture_listener,
                                         reason):
    from gui import assistant
    from core.desktop_chats import DesktopProject

    entered = threading.Event()
    proceed = threading.Event()
    thread_id = '12345678-1234-1234-1234-123456789abc'
    opened = []
    monkeypatch.setattr(assistant.QDesktopServices, 'openUrl', lambda url: opened.append(url.toString()) or True)

    def create(_, scope, question, cancel, *, project=None):
        entered.set()
        proceed.wait(3)
        if cancel():
            raise Cancelled('已取消。')
        return thread_id

    monkeypatch.setattr(assistant.DesktopChats, 'create', create)
    panel = assistant.AssistantPanel(project_home=tmp_path)
    try:
        panel.begin_shared(snapshot, '目标变了，执行器为什么没跟上？', None)
        assert entered.wait(2)
        lease = panel._shared_lease
        if reason == 'cancel':
            panel.cancel_codex_btn.click()
        elif reason == 'switch':
            panel.invalidate_context('测量已切换')
        elif reason == 'project':
            panel._fill_codex_projects([DesktopProject('demo', 'Demo', (tmp_path,))])
            panel.codex_project_combo.setCurrentIndex(1)
        else:
            panel.shutdown(wait_ms=0)
        assert panel._shared_lease is None
        with pytest.raises(ValueError, match=UNAVAILABLE):
            query_capture(tmp_path / 'codex-captures', lease.scope, 'describe', {})
        proceed.set()
        _wait(qapp, lambda: panel._desktop_request is None)
        qapp.processEvents()
        assert not opened
    finally:
        proceed.set()
        panel.shutdown()

@pytest.mark.skipif(sys.platform != 'win32', reason='The Codex desktop UI is Windows-only')
def test_selected_project_reaches_native_chat_and_evidence_returns_to_plot(
        qapp, monkeypatch, tmp_path, capture_listener):
    from PySide6.QtWidgets import QMessageBox
    from core.desktop_chats import DesktopProject
    from gui import app_data, assistant
    from gui.main_window import MainWindow

    project = DesktopProject('p702', '04_Software', (tmp_path / '702',))
    project.roots[0].mkdir()
    question = '目标变了，执行器为什么没跟上？'
    thread_id = '12345678-1234-1234-1234-123456789abc'
    created, opened, confirmed = [], [], []
    monkeypatch.setattr(app_data, 'per_user_folder', lambda: tmp_path)
    monkeypatch.setattr(MainWindow, '_settings_folder', staticmethod(lambda: tmp_path))
    monkeypatch.setattr(assistant.DesktopChats, 'projects', lambda _self, cancel: [project])
    monkeypatch.setattr(assistant.QDesktopServices, 'openUrl',
                        lambda url: opened.append(url.toString()) or True)

    def consent(prompt):
        confirmed.append(prompt.informativeText())
        return QMessageBox.StandardButton.Yes

    def create(_, scope, question, cancel, *, project=None):
        created.append((scope, question, project))
        return thread_id

    evidence_holder = {}

    def read(_, chat, cancel):
        assert chat == thread_id
        if not evidence_holder:
            return '（证据编号尚未生成…）', ()
        return (f'延迟 0.25 s [{evidence_holder["identifier"]}]',
                (evidence_holder['identifier'], 'ev-9999'))

    monkeypatch.setattr(QMessageBox, 'exec', consent)
    monkeypatch.setattr(assistant.DesktopChats, 'create', create)
    monkeypatch.setattr(assistant.DesktopChats, 'read', read)

    window = MainWindow('CATK', '00.00.99')
    panel = window.assistant_panel
    try:
        window.store = _actuator_store()
        window.measurement_path = 'private-log.csv'
        window.add_signals_to_plot(list(ACTUATOR_KEYS.values()))
        window._assistant_first_show(True)
        _wait(qapp, lambda: panel._desktop_request is None)
        assert panel.ref_project_combo.currentData() is None
        panel.codex_project_combo.setCurrentIndex(1)
        panel.question_input.setPlainText(question)
        panel.share_btn.click()
        _wait(qapp, lambda: panel._desktop_request is None)
        lease = panel._shared_lease
        assert created == [(lease.scope, question, project)]
        described = lease._dispatch({'operation': 'describe', 'arguments': {}})['data']
        assert 'osvanta_lookup_reference' not in {t['name'] for t in described['tools']}
        assert '本次授权' in panel.privacy_label.text()
        assert opened == [f'codex://threads/{thread_id}']
        assert project.name in confirmed[0] and str(project.roots[0]) in confirmed[0]
        response = lease._dispatch({'operation': 'osvanta_compare_events', 'arguments': ACTUATOR_KEYS})
        evidence_holder['identifier'] = response['data']['evidence'][0]['id']

        panel.read_chat_btn.click()
        _wait(qapp, lambda: panel._desktop_request is None)
        assert panel.codex_evidence_list.count() == 1
        evidence = panel.codex_evidence_list.item(0)
        calls = []
        monkeypatch.setattr(window.plot_panel, 'center_on_time',
                            lambda time, span, **kwargs: calls.append((time, span)))
        panel.codex_evidence_list.itemActivated.emit(evidence)
        assert len(calls) == 1
        window._release_store()
        assert panel.codex_project_combo.currentData() == project
        assert panel.codex_evidence_list.count() == 0
        assert panel._shared_lease is None
        assert panel.privacy_label.text() == panel.PRIVACY_NOTE
    finally:
        panel.shutdown()
        window.deleteLater()
        qapp.processEvents()


@pytest.mark.skipif(sys.platform != 'win32', reason='The Codex desktop UI is Windows-only')
def test_project_agent_ui_binds_shares_and_renders_reference_evidence(
        qapp, monkeypatch, tmp_path, capture_listener):
    from hashlib import sha256
    import json
    from PySide6.QtWidgets import QMessageBox
    from core.desktop_chats import DesktopProject
    from core.project_agent import ReferenceEvidence
    from gui import app_data, assistant
    from gui.main_window import MainWindow

    src_c = tmp_path / 'climate.c'
    src_c.write_text('if (ok) {\n    DemoMotorCmd = 42;\n}\n', encoding='utf-8')
    catalog = {
        'agents': [{
            'name': 'E702',
            'version_pattern': r'_(V\d{4})(?:\.|$)',
            'releases': {
                'V1335': [{
                    'kind': 'c',
                    'path': str(src_c),
                    'sha256': sha256(src_c.read_bytes()).hexdigest(),
                }],
            },
        }],
    }
    (tmp_path / 'assistant-project-agents.json').write_text(
        json.dumps(catalog), encoding='utf-8')

    project = DesktopProject('p702', '04_Software', (tmp_path / '702',))
    project.roots[0].mkdir()
    question = '目标变了，为什么指令写成了 42？'
    thread_id = '12345678-1234-1234-1234-123456789abc'
    dialogs, create_calls = [], []

    monkeypatch.setattr(app_data, 'per_user_folder', lambda: tmp_path)
    monkeypatch.setattr(MainWindow, '_settings_folder', staticmethod(lambda: tmp_path))
    monkeypatch.setattr(assistant.DesktopChats, 'projects', lambda _self, cancel: [project])
    monkeypatch.setattr(assistant.QDesktopServices, 'openUrl', lambda _url: True)

    def fake_exec(box):
        title = box.windowTitle()
        dialogs.append((title, box.text(), box.informativeText()))
        if title == '共享到 Codex 桌面端':
            return QMessageBox.StandardButton.Yes
        return QMessageBox.StandardButton.Close

    def create(_, scope, question, cancel, *, project=None, has_references=False):
        create_calls.append((scope, question, project, has_references))
        return thread_id

    evidence_holder = {}

    def read(_, chat, cancel):
        return (f'代码给出 {evidence_holder["id"]}', (evidence_holder['id'],))

    monkeypatch.setattr(QMessageBox, 'exec', fake_exec)
    monkeypatch.setattr(assistant.DesktopChats, 'create', create)
    monkeypatch.setattr(assistant.DesktopChats, 'read', read)

    window = MainWindow('CATK', '00.00.99')
    panel = window.assistant_panel
    try:
        window.store = _actuator_store()
        window.measurement_path = 'road_V1335.csv'
        window.add_signals_to_plot(list(ACTUATOR_KEYS.values()))
        window._assistant_first_show(True)
        _wait(qapp, lambda: panel._desktop_request is None)

        assert panel.ref_project_combo.count() == 2
        panel.ref_project_combo.setCurrentIndex(1)
        assert panel.ref_version_combo.isEnabled()
        assert 'E702' in panel.ref_status_label.text()
        assert 'V1335' in panel.ref_status_label.text()

        panel.codex_project_combo.setCurrentIndex(1)
        panel.question_input.setPlainText(question)
        panel.share_btn.click()
        _wait(qapp, lambda: panel._desktop_request is None)

        assert '项目参考资料：E702 · V1335' in dialogs[0][2]
        assert create_calls and create_calls[0][3] is True

        lease = panel._shared_lease
        described = lease._dispatch({'operation': 'describe', 'arguments': {}})['data']
        assert 'osvanta_lookup_reference' in {t['name'] for t in described['tools']}
        ref_res = lease._dispatch({
            'operation': 'osvanta_lookup_reference',
            'arguments': {'kind': 'c', 'query': 'DemoMotorCmd'},
        })
        evidence_holder['id'] = ref_res['data']['matches'][0]['id']

        from PySide6.QtCore import Qt
        panel.read_chat_btn.click()
        _wait(qapp, lambda: panel._desktop_request is None)
        assert panel.codex_evidence_list.count() == 1
        item = panel.codex_evidence_list.item(0)
        assert item.text().startswith('[src-1]')
        assert isinstance(item.data(Qt.ItemDataRole.UserRole), ReferenceEvidence)

        panel.codex_evidence_list.itemActivated.emit(item)
        viewer = [row for row in dialogs if row[0] == '项目参考资料证据']
        assert len(viewer) == 1
        assert 'climate.c' in viewer[0][1]
        assert 'DemoMotorCmd = 42' in viewer[0][2]
    finally:
        panel.shutdown()
        window.deleteLater()
        qapp.processEvents()


def test_desktop_chats_capture_directory_falls_back_to_legacy_registration(tmp_path):
    from core.desktop_chats import DesktopChats

    codex_home = tmp_path / '.codex'
    codex_home.mkdir()
    legacy_dir = (tmp_path / 'legacy' / 'codex-captures').resolve()
    new_dir = (tmp_path / 'catk' / 'codex-captures').resolve()
    chats = DesktopChats(new_dir, home=codex_home, legacy_directory=legacy_dir)
    adapter = chats._adapter_path.resolve()
    import sys as _sys
    exe = _sys.executable.replace('\\', '\\\\')
    adp = str(adapter).replace('\\', '\\\\')
    leg = str(legacy_dir).replace('\\', '\\\\')
    (codex_home / 'config.toml').write_text(
        f'[mcp_servers.osvanta_capture]\ncommand = "{exe}"\nargs = ["-B", "{adp}", "{leg}"]\n',
        encoding='utf-8',
    )
    assert chats.capture_directory() == legacy_dir

    cur = str(new_dir).replace('\\', '\\\\')
    (codex_home / 'config.toml').write_text(
        f'[mcp_servers.osvanta_capture]\ncommand = "{exe}"\nargs = ["-B", "{adp}", "{cur}"]\n',
        encoding='utf-8',
    )
    assert chats.capture_directory() == new_dir
