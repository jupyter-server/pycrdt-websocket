from functools import partial
from socket import socket

import pytest
from anyio import Event, create_task_group
from hypercorn import Config
from pycrdt import Array, Doc
from sniffio import current_async_library
from utils import ensure_server_running

from pycrdt_websocket import ASGIServer, WebsocketServer


class TestYDoc:
    def __init__(self):
        self.ydoc = Doc()
        self.ydoc["array"] = self.array = Array()
        self.state = None
        self.value = 0

    def update(self):
        self.array.append(self.value)
        self.value += 1
        update = self.ydoc.get_update(self.state)
        self.state = self.ydoc.get_state()
        return update


@pytest.fixture
async def yws_server(request, unused_tcp_port):
    try:
        kwargs = request.param
    except AttributeError:
        kwargs = {}
    websocket_server = WebsocketServer(**kwargs)
    app = ASGIServer(websocket_server)
    config = Config()
    config.bind = [f"localhost:{unused_tcp_port}"]
    shutdown_event = Event()
    if current_async_library() == "trio":
        from hypercorn.trio import serve
    else:
        from hypercorn.asyncio import serve
    try:
        async with create_task_group() as tg, websocket_server:
            tg.start_soon(
                partial(serve, app, config, shutdown_trigger=shutdown_event.wait, mode="asgi")
            )
            await ensure_server_running("localhost", unused_tcp_port)
            yield unused_tcp_port
            shutdown_event.set()
    except Exception:
        pass


@pytest.fixture
def test_ydoc():
    return TestYDoc()


@pytest.fixture
def unused_tcp_port() -> int:
    with socket() as sock:
        sock.bind(("localhost", 0))
        return sock.getsockname()[1]
