import pytest
from anyio import sleep
from httpx_ws import aconnect_ws
from pycrdt import Doc, Map
from utils import Websocket

from pycrdt_websocket import WebsocketProvider

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("yws_server", [{"auto_clean_rooms": False}], indirect=True)
async def test_asgi(yws_server):
    port = yws_server
    # client 1
    ydoc1 = Doc()
    ydoc1["map"] = ymap1 = Map()
    ymap1["key"] = "value"
    async with aconnect_ws(
        f"http://localhost:{port}/my-roomname"
    ) as websocket1, WebsocketProvider(ydoc1, Websocket(websocket1, "my-roomname")):
        await sleep(0.1)

    # client 2
    ydoc2 = Doc()
    async with aconnect_ws(
        f"http://localhost:{port}/my-roomname"
    ) as websocket2, WebsocketProvider(ydoc2, Websocket(websocket2, "my-roomname")):
        await sleep(0.1)

    ydoc2["map"] = ymap2 = Map()
    assert str(ymap2) == '{"key":"value"}'
