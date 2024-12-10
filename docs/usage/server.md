A server connects multiple `Doc` through a [WebsocketServer](../reference/WebSocket_server.md).

Pycrdt-websocket can be used with an [ASGI](https://asgi.readthedocs.io) server. Here is a code example using [Hypercorn](https://hypercorn.readthedocs.io):
```py
import asyncio
from hypercorn import Config
from hypercorn.asyncio import serve
from pycrdt_websocket import ASGIServer, WebsocketServer

websocket_server = WebsocketServer()
app = ASGIServer(websocket_server)

async def main():
    websocket_server = WebsocketServer()
    app = ASGIServer(websocket_server)
    config = Config()
    config.bind = ["localhost:1234"]
    async with websocket_server:
        await serve(app, config, mode="asgi")

asyncio.run(main())
```
