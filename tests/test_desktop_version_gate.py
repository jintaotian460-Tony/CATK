# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""The desktop version gate accepts the baseline build outright and any
newer build whose RPC surface passes a live probe; probe results are
cached per machine so a desktop self-update heals without a source edit."""

import json
import subprocess
from pathlib import Path

import pytest

from core.rpc_transport import BridgeError, Cancelled
from core.desktop_chats import VERIFIED_DESKTOP_VERSION, DesktopChats

NEW_VERSION = 'codex-cli 0.167.0-alpha.9.9'
PROJECT_PAGE = {'data': [{'id': 'p1', 'name': 'P', 'roots': [{'path': 'D:/x'}]}]}


class FakeTransport:
    def __init__(self, argv, cwd=None, env=None):
        self.argv = argv

    def close(self):
        pass


class FakeRpc:
    def __init__(self, transport, cancel=None):
        self.transport = transport
        self.calls = []
        self.project_page = {'data': []}
        self.fail_project_list = False

    def request(self, method, params, *, timeout=30):
        self.calls.append(method)
        if method == 'initialize':
            return {}
        if method == 'project/list':
            if self.fail_project_list:
                raise BridgeError('Codex 拒绝请求 project/list（-32601）。')
            return dict(self.project_page)
        raise BridgeError(f'unexpected method {method}')

    def notify(self, method, params=None):
        self.calls.append(method)


@pytest.fixture
def chats(tmp_path):
    (tmp_path / 'codex.exe').write_bytes(b'MZ')
    return DesktopChats(tmp_path / 'captures', home=tmp_path / 'home',
                        executable=str(tmp_path / 'codex.exe'))


@pytest.fixture
def rpc(chats, monkeypatch):
    fake = FakeRpc(FakeTransport([]))

    def fake_run(arguments, **kwargs):
        return subprocess.CompletedProcess(arguments, 0, stdout=f'{NEW_VERSION}\n')

    monkeypatch.setattr('core.desktop_chats.subprocess.run', fake_run)
    monkeypatch.setattr('core.desktop_chats.StdioTransport', FakeTransport)
    monkeypatch.setattr('core.desktop_chats.JsonRpc', lambda transport, cancel=None: fake)
    return fake


def test_baseline_build_skips_probe(chats, rpc, monkeypatch):
    def baseline_run(arguments, **kwargs):
        return subprocess.CompletedProcess(arguments, 0, stdout=f'{VERIFIED_DESKTOP_VERSION}\n')

    monkeypatch.setattr('core.desktop_chats.subprocess.run', baseline_run)

    def refuse(*args):
        raise AssertionError('probe ran for the baseline build')

    monkeypatch.setattr(chats, '_probe_version', refuse)
    assert chats.projects(lambda: False) == []
    assert not chats._version_cache.exists()


def test_new_build_is_probed_cached_and_then_accepted(chats, rpc):
    rpc.project_page = PROJECT_PAGE
    projects = chats.projects(lambda: False)
    assert [project.name for project in projects] == ['P']
    assert rpc.calls.count('project/list') == 2  # probe + the real listing
    assert json_cache(chats) == [NEW_VERSION]

    def refuse(*args):
        raise AssertionError('probe ran although the build is cached')

    chats._probe_version = refuse
    assert [project.id for project in chats.projects(lambda: False)] == ['p1']


def test_failing_probe_refuses_and_caches_nothing(chats, rpc):
    rpc.fail_project_list = True
    with pytest.raises(BridgeError) as raised:
        chats.projects(lambda: False)
    message = str(raised.value)
    assert NEW_VERSION in message and VERIFIED_DESKTOP_VERSION in message
    assert '握手不通过' in message and 'project/list' in message
    assert not chats._version_cache.exists()


@pytest.mark.parametrize('page', [
    {'data': 'all projects'},
    {'data': [{'id': 'p1', 'name': 1, 'roots': []}]},
    {'data': ['not-a-dict']},
    {'no-data': []},
])
def test_broken_rpc_surface_refuses(chats, rpc, page):
    rpc.project_page = page
    with pytest.raises(BridgeError) as raised:
        chats.projects(lambda: False)
    assert NEW_VERSION in str(raised.value)
    assert not chats._version_cache.exists()


def test_cancelled_probe_propagates_unwrapped(chats, rpc):
    def fail(method, params, *, timeout=30):
        rpc.calls.append(method)
        if method == 'project/list':
            raise Cancelled('已取消。')
        return {}

    rpc.request = fail
    with pytest.raises(Cancelled):
        chats.projects(lambda: False)
    assert not chats._version_cache.exists()


def test_corrupt_cache_is_ignored_and_reprobed(chats, rpc):
    chats._version_cache.parent.mkdir(parents=True, exist_ok=True)
    chats._version_cache.write_text('not-json{', encoding='utf-8')
    rpc.project_page = PROJECT_PAGE
    assert [project.name for project in chats.projects(lambda: False)] == ['P']
    assert rpc.calls.count('project/list') == 2  # cache miss → probe ran again
    assert json_cache(chats) == [NEW_VERSION]


def json_cache(chats):
    return json.loads(chats._version_cache.read_text(encoding='utf-8'))
