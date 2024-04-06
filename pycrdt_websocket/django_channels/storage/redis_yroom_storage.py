from typing import Optional

import redis.asyncio as redis
from pycrdt import Doc

from .base_yroom_storage import BaseYRoomStorage


class RedisYRoomStorage(BaseYRoomStorage):
    """A YRoom storage that uses Redis as main storage, without
    persistent storage.
    Args:
        room_name: The name of the room.
    """

    def __init__(self, room_name: str, save_throttle_interval: int | None = None) -> None:
        super().__init__(room_name, save_throttle_interval)

        self.redis_key = f"document:{self.room_name}"
        self.redis = self._make_redis()

    async def get_document(self) -> Doc:
        snapshot = await self.redis.get(self.redis_key)

        if not snapshot:
            snapshot = await self.load_snapshot()

        document = Doc()

        if snapshot:
            document.apply_update(snapshot)

        return document

    async def update_document(self, update: bytes):
        await self.redis.watch(self.redis_key)

        try:
            current_document = await self.get_document()
            updated_snapshot = self._apply_update_to_document(current_document, update)

            async with self.redis.pipeline() as pipe:
                while True:
                    try:
                        pipe.multi()
                        pipe.set(self.redis_key, updated_snapshot)

                        await pipe.execute()

                        break
                    except redis.WatchError:
                        current_document = await self.get_document()
                        updated_snapshot = self._apply_update_to_document(
                            current_document,
                            update,
                        )

                        continue
        finally:
            await self.redis.unwatch()

        await self.throttled_save_snapshot()

    async def load_snapshot(self) -> Optional[bytes]:
        return None

    async def save_snapshot(self) -> Optional[bytes]:
        return None

    async def close(self):
        await self.save_snapshot()
        await self.redis.close()

    def _apply_update_to_document(self, document: Doc, update: bytes) -> bytes:
        document.apply_update(update)

        return document.get_update()

    def _make_redis(self):
        """Makes a Redis client.
        Defaults to a local client"""

        return redis.Redis(host="localhost", port=6379, db=0)
