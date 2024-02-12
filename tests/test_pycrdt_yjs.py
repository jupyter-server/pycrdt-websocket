from __future__ import annotations

from functools import partial

import pytest
from anyio import Event, fail_after
from pycrdt import Array, Doc, Map
from websockets import connect

from pycrdt_websocket import WebsocketProvider


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


@pytest.mark.anyio
@pytest.mark.parametrize("yjs_client", "0", indirect=True)
async def test_pycrdt_yjs_0(yws_server, yjs_client):
    ydoc = Doc()
    async with connect("ws://127.0.0.1:1234/my-roomname") as websocket, WebsocketProvider(
        ydoc, websocket
    ):
        ydoc["map"] = ymap = Map()
        for v_in in range(10):
            ymap["in"] = float(v_in)
            v_out = await watch(ymap, "out").wait()
            assert v_out == v_in + 1.0


@pytest.mark.anyio
@pytest.mark.parametrize("yjs_client", "1", indirect=True)
async def test_pycrdt_yjs_1(yws_server, yjs_client):
    ydoc = Doc()
    ydoc["cells"] = ycells = Array()
    ydoc["state"] = ystate = Map()
    ycells_change = watch(ycells)
    ystate_change = watch(ystate)
    async with connect("ws://127.0.0.1:1234/my-roomname") as websocket, WebsocketProvider(
        ydoc, websocket
    ):
        await ycells_change.wait()
        await ystate_change.wait()
        assert ycells.to_py() == [{"metadata": {"foo": "bar"}, "source": "1 + 2"}]
        assert ystate.to_py() == {"state": {"dirty": False}}
