import pytest
import uvicorn
from anyio import create_task_group, sleep
from pycrdt import Doc, Map
from websockets import connect

from pycrdt_websocket import ASGIServer, WebsocketProvider, WebsocketServer

websocket_server = WebsocketServer(auto_clean_rooms=False)
app = ASGIServer(websocket_server)


@pytest.mark.anyio
async def test_asgi(unused_tcp_port):
    # server
    config = uvicorn.Config("test_asgi:app", port=unused_tcp_port, log_level="info")
    server = uvicorn.Server(config)
    async with create_task_group() as tg, websocket_server:
        tg.start_soon(server.serve)
        while not server.started:
            await sleep(0)

        # clients
        # client 1
        ydoc1 = Doc()
        ydoc1["map"] = ymap1 = Map()
        ymap1["key"] = "value"
        async with connect(
            f"ws://localhost:{unused_tcp_port}/my-roomname"
        ) as websocket1, WebsocketProvider(ydoc1, websocket1):
            await sleep(0.1)

        # client 2
        ydoc2 = Doc()
        async with connect(
            f"ws://localhost:{unused_tcp_port}/my-roomname"
        ) as websocket2, WebsocketProvider(ydoc2, websocket2):
            await sleep(0.1)

        ydoc2["map"] = ymap2 = Map()
        assert str(ymap2) == '{"key":"value"}'

        tg.cancel_scope.cancel()
