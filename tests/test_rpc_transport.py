# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Tony Tian (CATK)

"""Tests for bounded stdio JSON-RPC transport."""
from __future__ import annotations

import sys
import threading
import time

import pytest

from core.rpc_transport import Cancelled, JsonRpc, StdioTransport


def test_rpc_wait_routes_notifications_and_replies_to_tool_requests():
    class Transport:
        def __init__(self):
            self.sent = []
            self.incoming = iter([
                {'method': 'item/agentMessage/delta', 'params': {'delta': 'a'}},
                {'id': 'server-1', 'method': 'item/tool/call',
                 'params': {'tool': 'osvanta_analyze'}},
                {'id': 1, 'result': {'thread': {'id': 'new-thread'}}},
            ])

        def send(self, value):
            self.sent.append(value)

        def receive(self, timeout):
            return next(self.incoming)

    transport = Transport()
    updates = []
    rpc = JsonRpc(transport, on_event=lambda m, p: updates.append((m, p)),
                  on_request=lambda m, p: {'success': True})
    assert rpc.request('thread/start', {}) == {'thread': {'id': 'new-thread'}}
    assert transport.sent == [
        {'id': 1, 'method': 'thread/start', 'params': {}},
        {'id': 'server-1', 'result': {'success': True}},
    ]
    assert updates == [('item/agentMessage/delta', {'delta': 'a'})]


def test_external_process_transport_uses_real_json_lines_and_closes(tmp_path):
    child = tmp_path / 'fake_app_server.py'
    child.write_text(
        'import json,sys\n'
        'for line in sys.stdin:\n'
        ' m=json.loads(line)\n'
        ' if "id" in m:\n'
        '  print(json.dumps({"id":m["id"],"result":{"ok":True}}),flush=True)\n',
        encoding='utf-8',
    )
    transport = StdioTransport([sys.executable, str(child)], cwd=str(tmp_path))
    try:
        assert JsonRpc(transport).request('initialize', {}, timeout=5) == {'ok': True}
    finally:
        transport.close()


def test_cancel_releases_a_write_to_a_server_that_never_reads_stdin(tmp_path):
    transport = StdioTransport(
        [sys.executable, '-c', 'import time; time.sleep(60)'], cwd=str(tmp_path))
    cancelled = threading.Event()
    timer = threading.Timer(0.25, cancelled.set)
    timer.start()
    started = time.monotonic()
    try:
        with pytest.raises(Cancelled):
            JsonRpc(transport, cancel=cancelled.is_set).request(
                'test', {'content': 'x' * (1024 * 1024)})
    finally:
        timer.cancel()
        transport.close()
    assert time.monotonic() - started < 5
