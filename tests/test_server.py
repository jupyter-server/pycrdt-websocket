import pytest
from anyio import sleep

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("websocket_server_api", ["websocket_server_start_stop"], indirect=True)
@pytest.mark.parametrize("yws_server", [{"auto_restart": True}], indirect=True)
async def test_server_restart(yws_server):
    port, server = yws_server

    async def raise_error():
        raise RuntimeError("foo")

    server._task_group.start_soon(raise_error)
    await sleep(0.1)
