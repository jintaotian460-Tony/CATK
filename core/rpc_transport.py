# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Tony Tian (CATK)

"""Bounded stdio JSON-RPC transport for desktop assistant IPC."""
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time


class BridgeError(RuntimeError):
    pass


class Cancelled(BridgeError):
    pass


MAX_MESSAGE_BYTES = 4 * 1024 * 1024


class StdioTransport:
    """One owned process, bounded JSON lines, and no shell command wrapper."""

    def __init__(self, command, *, cwd, env=None):
        self._queue = queue.Queue(maxsize=128)
        self._outgoing = queue.Queue(maxsize=1)
        self.cancel = lambda: False
        self._closed = threading.Event()
        self._process = subprocess.Popen(
            list(command), cwd=cwd, env=env, stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0),
        )
        self._readers = [
            threading.Thread(target=self._read_stdout, daemon=True),
            threading.Thread(target=self._drain_stderr, daemon=True),
            threading.Thread(target=self._write_stdin, daemon=True),
        ]
        for reader in self._readers:
            reader.start()

    def _put(self, value):
        while not self._closed.is_set():
            try:
                self._queue.put(value, timeout=0.1)
                return
            except queue.Full:
                pass

    def _read_stdout(self):
        try:
            while not self._closed.is_set():
                line = self._process.stdout.readline(MAX_MESSAGE_BYTES + 1)
                if not line:
                    self._put(BridgeError('Codex 进程已退出。'))
                    break
                if len(line) > MAX_MESSAGE_BYTES:
                    raise BridgeError('Codex 协议消息超过安全上限。')
                message = json.loads(line)
                if not isinstance(message, dict):
                    raise ValueError('expected JSON object')
                self._put(message)
        except (ValueError, OSError):
            self._put(BridgeError('Codex 返回无效的协议数据。'))
        except BridgeError as exc:
            self._put(exc)

    def _drain_stderr(self):
        # Codex may emit credentials or provider diagnostics here. Drain, do
        # not copy them into the application log, transcript, or model input.
        try:
            while not self._closed.is_set():
                if not self._process.stderr.read(4096):
                    break
        except OSError:
            pass

    def _write_stdin(self):
        while not self._closed.is_set():
            try:
                data, result = self._outgoing.get(timeout=0.1)
            except queue.Empty:
                continue
            if self._closed.is_set() or self.cancel():
                result.put(Cancelled('已取消。'))
                continue
            try:
                self._process.stdin.write(data)
                self._process.stdin.flush()
            except (OSError, ValueError):
                result.put(BridgeError('无法写入 Codex 连接。'))
                return
            else:
                result.put(None)

    def send(self, message):
        if self._closed.is_set():
            raise BridgeError('Codex 连接已关闭。')
        if self.cancel():
            raise Cancelled('已取消。')
        data = (json.dumps(message, ensure_ascii=False, allow_nan=False)
                + '\n').encode('utf-8')
        if len(data) > MAX_MESSAGE_BYTES:
            raise BridgeError('请求超过协议消息上限。')
        result = queue.Queue(maxsize=1)
        try:
            self._outgoing.put_nowait((data, result))
        except queue.Full as exc:
            raise BridgeError('Codex 写入队列已满。') from exc
        deadline = time.monotonic() + 10.0
        while True:
            if self.cancel():
                raise Cancelled('已取消。')
            left = deadline - time.monotonic()
            if left <= 0:
                raise BridgeError('写入 Codex 连接超时。')
            try:
                error = result.get(timeout=min(left, 0.1))
                break
            except queue.Empty:
                continue
        if error is not None:
            raise error

    def receive(self, timeout):
        try:
            value = self._queue.get(timeout=max(0.0, timeout))
        except queue.Empty:
            return None
        if isinstance(value, Exception):
            raise value
        return value

    def finish(self):
        """Close stdin after the last reply and wait for persistence to flush."""
        self._process.stdin.close()
        try:
            if self._process.wait(timeout=5):
                raise BridgeError('Codex 本地聊天保存失败。')
        except subprocess.TimeoutExpired as exc:
            raise BridgeError('Codex 本地聊天保存超时。') from exc

    def close(self):
        if self._closed.is_set():
            return
        self._closed.set()
        process = self._process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)
        for thread, stream in zip(self._readers, (process.stdout, process.stderr, process.stdin)):
            thread.join(timeout=0.5)
            if not thread.is_alive():
                stream.close()


class JsonRpc:
    def __init__(self, transport, *, on_event=None, on_request=None,
                 cancel=None):
        self.transport = transport
        self.on_event = on_event or (lambda method, params: None)
        self.on_request = on_request or self._deny_request
        self.cancel = cancel or (lambda: False)
        if isinstance(transport, StdioTransport):
            transport.cancel = lambda: self.cancel()
        self._next_id = 0
        self._responses = {}

    @staticmethod
    def _deny_request(method, params):
        raise BridgeError('不允许的服务端请求。')

    def _send(self, message):
        if self.cancel():
            raise Cancelled('已取消。')
        self.transport.send(message)

    def notify(self, method, params=None):
        self._send({'method': method, 'params': params or {}})

    def send_request(self, method, params):
        self._next_id += 1
        request_id = self._next_id
        self._send({'id': request_id, 'method': method, 'params': params})
        return request_id

    def request(self, method, params, *, timeout=30.0):
        request_id = self.send_request(method, params)
        deadline = time.monotonic() + timeout
        while request_id not in self._responses:
            if self.cancel():
                raise Cancelled('已停止。')
            left = deadline - time.monotonic()
            if left <= 0:
                raise BridgeError(f'Codex 请求超时：{method}。')
            self.pump(min(left, 0.1))
        response = self._responses.pop(request_id)
        if 'error' in response:
            error = response['error']
            code = error.get('code') if isinstance(error, dict) else None
            raise BridgeError(f'Codex 拒绝请求 {method}（{code}）；请检查版本和登录状态。')
        return response.get('result', {})

    def pump(self, timeout=0.1):
        message = self.transport.receive(timeout)
        if message is None:
            return
        method = message.get('method')
        if isinstance(method, str):
            params = message.get('params') or {}
            if not isinstance(params, dict):
                raise BridgeError('服务端参数格式无效。')
            if 'id' in message:
                try:
                    result = self.on_request(method, params)
                    reply = {'id': message['id'], 'result': result}
                except (ValueError, BridgeError):
                    reply = {'id': message['id'], 'error': {
                        'code': -32601, 'message': 'Not permitted by CATK'}}
                self._send(reply)
            else:
                self.on_event(method, params)
        elif 'id' in message:
            if len(self._responses) >= 128:
                raise BridgeError('Codex 回包队列超过上限。')
            self._responses[message['id']] = message
        else:
            raise BridgeError('无法识别的 Codex 消息。')
