A client connects their `Doc` through a [WebsocketProvider](../reference/WebSocket_provider.md).

Here is a code example using the [httpx-ws](https://frankie567.github.io/httpx-ws) library:
```py
import asyncio
from httpx_ws import aconnect_ws
from pycrdt import Doc, Map
from pycrdt_websocket import WebsocketProvider
from pycrdt_websocket.websocket import HttpxWebsocket

async def client():
    ydoc = Doc()
    ymap = ydoc.get("map", type=Map)
    room_name = "my-roomname"
    async with (
        aconnect_ws(f"http://localhost:1234/{room_name}") as websocket,
        WebsocketProvider(ydoc, HttpxWebsocket(websocket, room_name)),
    ):
        # Changes to remote ydoc are applied to local ydoc.
        # Changes to local ydoc are sent over the WebSocket and
        # broadcast to all clients.
        ymap["key"] = "value"

        await asyncio.Future()  # run forever

asyncio.run(client())
```
