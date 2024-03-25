from __future__ import annotations

from functools import partial

import pytest
from anyio import Event, fail_after
from httpx_ws import aconnect_ws
from pycrdt import Array, Doc, Map
from utils import Websocket, yjs_client

from pycrdt_websocket import WebsocketProvider

pytestmark = pytest.mark.anyio


class Change:
    def __init__(self, event, timeout, ydata, sid, key):
        self.event = event
        self.timeout = timeout
        self.ydata = ydata
        self.sid = sid
        self.key = key

    async def wait(self):
        with fail_after(self.timeout):
            await self.event.wait()
        self.ydata.unobserve(self.sid)
        if self.key is None:
            return
        return self.ydata[self.key]


def callback(change_event, key, event):
    if key is None or key in event.keys:
        change_event.set()


def watch(ydata, key: str | None = None, timeout: float = 1.0):
    change_event = Event()
    sid = ydata.observe(partial(callback, change_event, key))
    return Change(change_event, timeout, ydata, sid, key)


async def test_pycrdt_yjs_0(yws_server):
    port = yws_server
    with yjs_client(0, port):
        ydoc = Doc()
        async with aconnect_ws(
            f"http://localhost:{port}/my-roomname"
        ) as websocket, WebsocketProvider(ydoc, Websocket(websocket, "my-roomname")):
            ydoc["map"] = ymap = Map()
            for v_in in range(10):
                ymap["in"] = float(v_in)
                v_out = await watch(ymap, "out").wait()
                assert v_out == v_in + 1.0


async def test_pycrdt_yjs_1(yws_server):
    port = yws_server
    with yjs_client(1, port):
        ydoc = Doc()
        ydoc["cells"] = ycells = Array()
        ydoc["state"] = ystate = Map()
        ycells_change = watch(ycells)
        ystate_change = watch(ystate)
        async with aconnect_ws(
            f"http://localhost:{port}/my-roomname"
        ) as websocket, WebsocketProvider(ydoc, Websocket(websocket, "my-roomname")):
            await ycells_change.wait()
            await ystate_change.wait()
            assert ycells.to_py() == [{"metadata": {"foo": "bar"}, "source": "1 + 2"}]
            assert ystate.to_py() == {"state": {"dirty": False}}
