import pytest
from anyio import Event, move_on_after
from pycrdt import Array, Doc, Map
from websockets import connect

from pycrdt_websocket import WebsocketProvider


class YClient:
    """
    A representation of a `pycrdt` client. The constructor accepts a YDoc
    instance, defines a shared YMap type named `ymap`, and binds it to
    `self.ymap`.
    """

    def __init__(self, ydoc: Doc):
        self.ydoc = ydoc
        self.ymap = Map()
        self.ydoc["ymap"] = self.ymap
        self.ymap["clock"] = 0.0

    @property
    def clock(self):
        return self.ymap["clock"]

    def inc_clock(self):
        """
        Increments `ymap["clock"]`.
        """
        self.ymap["clock"] = self.clock + 1

    async def wait_for_reply(self):
        """
        Wait for the JS client to reply in response to a previous `inc_clock()`
        call by also incrementing `ymap["clock"]`.
        """
        change = Event()

        def callback(event):
            if "clock" in event.keys:
                change.set()

        subscription_id = self.ymap.observe(callback)
        # wait up to 1000ms for a reply
        with move_on_after(1.0):
            await change.wait()
        self.ymap.unobserve(subscription_id)


@pytest.mark.anyio
@pytest.mark.parametrize("yjs_client", "0", indirect=True)
async def test_pycrdt_yjs_0(yws_server, yjs_client):
    """
    The JS client (`yjs_client_0.js`) should set `ymap["out"] := ymap["in"] + 1`
    whenever the clock is incremented via `yclient.inc_clock()`.
    """
    MSG_COUNT = 10
    ydoc = Doc()
    yclient = YClient(ydoc)
    ymap = yclient.ymap

    async with connect("ws://127.0.0.1:1234/my-roomname") as websocket, WebsocketProvider(
        ydoc, websocket
    ):
        for msg_num in range(1, MSG_COUNT + 1):
            # set `ymap["in"]`
            ymap["in"] = float(msg_num)
            yclient.inc_clock()
            await yclient.wait_for_reply()

            # assert JS client increments `ymap["out"]` in response
            assert ymap["out"] == ymap["in"] + 1.0

    assert yclient.clock == MSG_COUNT * 2


@pytest.mark.anyio
@pytest.mark.parametrize("yjs_client", "1", indirect=True)
async def test_pycrdt_yjs_1(yws_server, yjs_client):
    """
    The JS client (`yjs_client_1.js`) should set `ydoc["cells"]` and
    `ydoc["state"]` whenever the clock is incremented via `yclient.inc_clock()`.
    """
    yroom = await yws_server.get_room("/my-roomname")
    ydoc = yroom.ydoc
    yclient = YClient(ydoc)

    yclient.inc_clock()
    await yclient.wait_for_reply()

    # TODO: remove the need to set a root type before accessing it
    ydoc["cells"] = Array()
    ydoc["state"] = Map()
    assert ydoc["cells"].to_py() == [{"metadata": {"foo": "bar"}, "source": "1 + 2"}]
    assert ydoc["state"].to_py() == {"state": {"dirty": False}}
