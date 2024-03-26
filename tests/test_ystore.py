import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from anyio import create_task_group
from sqlite_anyio import connect
from utils import StartStopContextManager, YDocTest

from pycrdt_websocket.ystore import SQLiteYStore, TempFileYStore

pytestmark = pytest.mark.anyio

MY_SQLITE_YSTORE_DB_PATH = str(Path(tempfile.mkdtemp(prefix="test_sql_")) / "ystore.db")


class MetadataCallback:
    def __init__(self):
        self.i = 0

    async def __call__(self):
        res = str(self.i).encode()
        self.i += 1
        return res


class MyTempFileYStore(TempFileYStore):
    prefix_dir = "test_temp_"

    def __init__(self, *args, delete=False, **kwargs):
        super().__init__(*args, **kwargs)
        if delete:
            Path(self.path).unlink(missing_ok=True)


class MySQLiteYStore(SQLiteYStore):
    db_path = MY_SQLITE_YSTORE_DB_PATH
    document_ttl = 1000

    def __init__(self, *args, delete=False, **kwargs):
        if delete:
            Path(self.db_path).unlink(missing_ok=True)
        super().__init__(*args, **kwargs)


@pytest.mark.parametrize("YStore", (MyTempFileYStore, MySQLiteYStore))
@pytest.mark.parametrize("ystore_api", ("ystore_context_manager", "ystore_start_stop"))
async def test_ystore(YStore, ystore_api):
    async with create_task_group() as tg:
        store_name = f"my_store_with_api_{ystore_api}"
        ystore = YStore(store_name, metadata_callback=MetadataCallback(), delete=True)
        if ystore_api == "ystore_start_stop":
            ystore = StartStopContextManager(ystore, tg)

        async with ystore as ystore:
            data = [b"foo", b"bar", b"baz"]
            for d in data:
                await ystore.write(d)

            if YStore == MyTempFileYStore:
                assert (Path(MyTempFileYStore.base_dir) / store_name).exists()
            elif YStore == MySQLiteYStore:
                assert Path(MySQLiteYStore.db_path).exists()
            i = 0
            async for d, m, t in ystore.read():
                assert d == data[i]  # data
                assert m == str(i).encode()  # metadata
                i += 1

            assert i == len(data)


@pytest.mark.parametrize("ystore_api", ("ystore_context_manager", "ystore_start_stop"))
async def test_document_ttl_sqlite_ystore(ystore_api):
    async with create_task_group() as tg:
        test_ydoc = YDocTest()
        store_name = f"my_store_with_api_{ystore_api}"
        ystore = MySQLiteYStore(store_name, delete=True)
        if ystore_api == "ystore_start_stop":
            ystore = StartStopContextManager(ystore, tg)

        async with ystore as ystore:
            now = time.time()
            db = await connect(ystore.db_path)
            cursor = await db.cursor()

            for i in range(3):
                # assert that adding a record before document TTL doesn't delete document history
                with patch("time.time") as mock_time:
                    mock_time.return_value = now
                    await ystore.write(test_ydoc.update())
                    assert (
                        await (await cursor.execute("SELECT count(*) FROM yupdates")).fetchone()
                    )[0] == i + 1

            # assert that adding a record after document TTL deletes previous document history
            with patch("time.time") as mock_time:
                mock_time.return_value = now + ystore.document_ttl + 1
                await ystore.write(test_ydoc.update())
                # two updates in DB: one squashed update and the new update
                assert (await (await cursor.execute("SELECT count(*) FROM yupdates")).fetchone())[
                    0
                ] == 2

            await db.close()


@pytest.mark.parametrize("YStore", (MyTempFileYStore, MySQLiteYStore))
@pytest.mark.parametrize("ystore_api", ("ystore_context_manager", "ystore_start_stop"))
async def test_version(YStore, ystore_api, caplog):
    async with create_task_group() as tg:
        store_name = f"my_store_with_api_{ystore_api}"
        prev_version = YStore.version
        YStore.version = -1
        ystore = YStore(store_name)
        if ystore_api == "ystore_start_stop":
            ystore = StartStopContextManager(ystore, tg)

        async with ystore as ystore:
            await ystore.write(b"foo")
            assert "YStore version mismatch" in caplog.text

        YStore.version = prev_version
        async with ystore as ystore:
            await ystore.write(b"bar")
