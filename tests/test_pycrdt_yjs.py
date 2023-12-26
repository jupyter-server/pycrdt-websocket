import pytest
from anyio import Event, create_task_group, move_on_after, sleep
from pycrdt import Array, Doc, Map
from websockets import connect  # type: ignore

from pycrdt_websocket import WebsocketProvider


class YTest:
    def __init__(self, ydoc: Doc, timeout: float = 1.0):
        self.ydoc = ydoc
        self.timeout = timeout
        self.ydoc["_test"] = self.ytest = Map()
        self.clock = -1.0

    def run_clock(self):
        self.clock = max(self.clock, 0.0)
        self.ytest["clock"] = self.clock

    async def clock_run(self):
        change = Event()

        def callback(event):
            if "clock" in event.keys:
                clk = event.keys["clock"]["newValue"]
                if clk > self.clock:
                    self.clock = clk + 1.0
                    change.set()

        subscription_id = self.ytest.observe(callback)
        async with create_task_group():
            with move_on_after(self.timeout):
                await change.wait()

        self.ytest.unobserve(subscription_id)


@pytest.mark.anyio
@pytest.mark.parametrize("yjs_client", "0", indirect=True)
async def test_pycrdt_yjs_0(yws_server, yjs_client):
    ydoc = Doc()
    ytest = YTest(ydoc)
    async with connect("ws://127.0.0.1:1234/my-roomname") as websocket, WebsocketProvider(
        ydoc, websocket
    ):
        ydoc["map"] = ymap = Map()
        # set a value in "in"
        for v_in in range(10):
            ymap["in"] = float(v_in)
            ytest.run_clock()
            await ytest.clock_run()
            v_out = ymap["out"]
            assert v_out == v_in + 1.0


@pytest.mark.anyio
@pytest.mark.parametrize("yjs_client", "1", indirect=True)
async def test_pycrdt_yjs_1(yws_server, yjs_client):
    # wait for the JS client to connect
    tt, dt = 0, 0.1
    while True:
        await sleep(dt)
        if "/my-roomname" in yws_server.rooms:
            break
        tt += dt
        if tt >= 1:
            raise RuntimeError("Timeout waiting for client to connect")
    ydoc = yws_server.rooms["/my-roomname"].ydoc
    ytest = YTest(ydoc)
    ytest.run_clock()
    await ytest.clock_run()
    ydoc["cells"] = ycells = Array()
    ydoc["state"] = ystate = Map()
    assert ycells.to_py() == [{"metadata": {"foo": "bar"}, "source": "1 + 2"}]
    assert ystate.to_py() == {"state": {"dirty": False}}
