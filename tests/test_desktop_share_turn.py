# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The desktop share flow starts the analysis turn itself and waits for it:
the desktop UI stopped rendering injected history, so an empty chat would
otherwise greet the user after every share."""

import json
import subprocess
from pathlib import Path
from uuid import UUID

import pytest

from core.codex_bridge import BridgeError, Cancelled
from core.desktop_chats import DesktopChats

THREAD_ID = '123e4567-e89b-12d3-a456-426614174000'
QUESTION = '吹面出风温度为什么没跟上目标？'


class FakeTransport:
    def __init__(self, argv, cwd=None, env=None):
        self.argv = argv

    def close(self):
        pass

    def finish(self):
        pass


class FakeRpc:
    def __init__(self, transport, cancel=None):
        self.transport = transport
        self.calls = []
        self.fail_turn_start = False
        self.turn_status = 'completed'
        self.error_event = False
        self.deliver_on_pump = 1
        self.on_event = lambda method, params: None
        self._pumps = 0
        self._armed = False

    def request(self, method, params, *, timeout=30):
        self.calls.append(method)
        if method == 'initialize':
            return {}
        if method == 'thread/start':
            assert params['ephemeral'] is False
            return {'thread': {'id': THREAD_ID, 'ephemeral': False,
                               'cwd': params['cwd']}}
        if method == 'turn/start':
            self.calls.append(('turn/start-input', params['input']))
            if self.fail_turn_start:
                raise BridgeError('Codex 拒绝请求 turn/start（-32601）。')
            self._armed = True
            return {'turn': {'id': 't1'}}
        if method in ('thread/inject_items', 'thread/name/set'):
            return {}
        raise BridgeError(f'unexpected method {method}')

    def notify(self, method, params=None):
        self.calls.append(method)

    def pump(self, timeout=0.1):
        self._pumps += 1
        if not self._armed or self._pumps < self.deliver_on_pump:
            return
        if self._pumps == self.deliver_on_pump:
            self._armed = False
            if self.error_event:
                self.on_event('error', {'error': 'boom'})
                return
            self.on_event('turn/completed', {
                'threadId': THREAD_ID, 'turn': {'id': 't1', 'status': self.turn_status}})


@pytest.fixture
def chats(tmp_path):
    captures = tmp_path / 'captures'
    captures.mkdir()
    home = tmp_path / 'home'
    home.mkdir()
    adapter = Path(__file__).resolve().parents[1] / 'tools' / 'osvanta_capture_mcp.py'
    toml_value = json.dumps  # JSON string escaping is valid TOML basic strings
    config = ('[mcp_servers.osvanta_capture]\n'
              f'command = {toml_value(str(Path(sys_executable()).resolve()))}\n'
              f'args = [{toml_value("-B")}, {toml_value(str(adapter))}, '
              f'{toml_value(str(captures))}]\n')
    (home / 'config.toml').write_text(config, encoding='utf-8')
    (tmp_path / 'codex.exe').write_bytes(b'MZ')
    chats = DesktopChats(captures, home=home, executable=str(tmp_path / 'codex.exe'))
    chats.mcp_command = Path(sys_executable()).resolve()
    return chats


def sys_executable():
    import sys
    return sys.executable


@pytest.fixture
def rpc(chats, monkeypatch):
    fake = FakeRpc(FakeTransport([]))

    def fake_run(arguments, **kwargs):
        return subprocess.CompletedProcess(arguments, 0, stdout='codex-cli 0.167.0-alpha.4.1\n')

    monkeypatch.setattr('core.desktop_chats.subprocess.run', fake_run)
    monkeypatch.setattr('core.desktop_chats.StdioTransport', FakeTransport)
    monkeypatch.setattr('core.desktop_chats.JsonRpc', lambda transport, cancel=None: fake)
    return fake


def test_create_fires_the_turn_and_waits(chats, rpc):
    thread_id = chats.create('cap-1', QUESTION, lambda: False)
    assert thread_id == THREAD_ID
    assert UUID(thread_id)
    assert 'thread/inject_items' in rpc.calls and 'thread/name/set' in rpc.calls
    assert 'turn/start' in rpc.calls
    inputs = [entry for entry in rpc.calls if isinstance(entry, tuple)]
    assert inputs and inputs[0][1][0]['text'] == QUESTION


def test_refused_turn_still_returns_the_thread(chats, rpc):
    rpc.fail_turn_start = True
    assert chats.create('cap-1', QUESTION, lambda: False) == THREAD_ID


def test_failed_turn_raises(chats, rpc):
    rpc.turn_status = 'failed'
    with pytest.raises(BridgeError, match='分析未完成'):
        chats.create('cap-1', QUESTION, lambda: False)


def test_model_error_event_raises(chats, rpc):
    rpc.error_event = True
    with pytest.raises(BridgeError, match='Codex 分析出错'):
        chats.create('cap-1', QUESTION, lambda: False)


def test_cancel_during_the_turn_propagates(chats, rpc, monkeypatch):
    rpc.deliver_on_pump = 50
    calls = {'n': 0}

    def cancel():
        calls['n'] += 1
        return calls['n'] >= 2

    with pytest.raises(Cancelled):
        chats.create('cap-1', QUESTION, cancel)


def test_turn_timeout_raises(chats, rpc, monkeypatch):
    rpc.deliver_on_pump = 10 ** 9  # never deliver within the patched deadline
    monkeypatch.setattr('core.desktop_chats.MAX_TURN_SECONDS', 0.05)
    with pytest.raises(BridgeError, match='超时'):
        chats.create('cap-1', QUESTION, lambda: False)
