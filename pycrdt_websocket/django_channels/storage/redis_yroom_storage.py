import time
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

    def __init__(
        self,
        room_name: str,
        save_throttle_interval: int | None = None,
        redis_expiration_seconds: int | None = 60 * 10,  # 10 minutes,
    ):
        super().__init__(room_name)

        self.save_throttle_interval = save_throttle_interval
        self.last_saved_at = time.time()

        self.redis_key = f"document:{self.room_name}"
        self.redis = self.make_redis()
        self.redis_expiration_seconds = redis_expiration_seconds

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
                        pipe.set(
                            name=self.redis_key,
                            value=updated_snapshot,
                            ex=self.redis_expiration_seconds,
                        )

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

    async def save_snapshot(self) -> None:
        return None

    async def throttled_save_snapshot(self) -> None:
        """Saves the document encoded as update to the database, throttled."""

        if (
            not self.save_throttle_interval
            or time.time() - self.last_saved_at <= self.save_throttle_interval
        ):
            return

        await self.save_snapshot()

        self.last_saved_at = time.time()

    def make_redis(self):
        """Makes a Redis client.
        Defaults to a local client"""

        return redis.Redis(host="localhost", port=6379, db=0)

    async def close(self):
        await self.save_snapshot()
        await self.redis.close()

    def _apply_update_to_document(self, document: Doc, update: bytes) -> bytes:
        document.apply_update(update)

        return document.get_update()
