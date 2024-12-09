A client connects their `Doc` through a [WebsocketProvider](../reference/WebSocket_provider.md).

Here is a code example using the [websockets](https://websockets.readthedocs.io) library:
```py
import asyncio
from websockets import connect
from pycrdt import Doc, Map
from pycrdt_websocket import WebsocketProvider

async def client():
    ydoc = Doc()
    ymap = ydoc.get("map", type=Map)
    async with (
        connect("ws://localhost:1234/my-roomname") as websocket,
        WebsocketProvider(ydoc, websocket),
    ):
        # Changes to remote ydoc are applied to local ydoc.
        # Changes to local ydoc are sent over the WebSocket and
        # broadcast to all clients.
        ymap["key"] = "value"

        await asyncio.Future()  # run forever

asyncio.run(client())
```
