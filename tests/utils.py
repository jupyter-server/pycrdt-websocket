import subprocess
from contextlib import contextmanager

from anyio import Lock, connect_tcp


class Websocket:
    def __init__(self, websocket, path: str):
        self._websocket = websocket
        self._path = path
        self._send_lock = Lock()

    @property
    def path(self) -> str:
        return self._path

    def __aiter__(self):
        return self

    async def __anext__(self) -> bytes:
        try:
            message = await self.recv()
        except Exception:
            raise StopAsyncIteration()
        return message

    async def send(self, message: bytes):
        async with self._send_lock:
            await self._websocket.send_bytes(message)

    async def recv(self) -> bytes:
        b = await self._websocket.receive_bytes()
        return bytes(b)


@contextmanager
def yjs_client(client_id: int, port: int):
    p = subprocess.Popen(["node", f"tests/yjs_client_{client_id}.js", str(port)])
    yield p
    p.kill()


async def ensure_server_running(host: str, port: int) -> None:
    while True:
        try:
            await connect_tcp(host, port)
        except OSError:
            pass
        else:
            break
