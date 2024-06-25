from pathlib import Path

import anyio
from anyio.streams.memory import MemoryObjectSendStream
from pycrdt import TransactionEvent


def put_updates(update_send_stream: MemoryObjectSendStream, event: TransactionEvent) -> None:
    try:
        update = event.update
        update_send_stream.send_nowait(update)
    except Exception:
        pass


async def get_new_path(path: str) -> str:
    p = Path(path)
    ext = p.suffix
    p_noext = p.with_suffix("")
    i = 1
    while True:
        new_path = f"{p_noext}({i}){ext}"
        if not await anyio.Path(new_path).exists():
            break
        i += 1
    return new_path
