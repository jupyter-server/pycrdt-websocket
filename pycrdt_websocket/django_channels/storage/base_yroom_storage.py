from abc import ABC, abstractmethod
from typing import Optional

from pycrdt import Doc


class BaseYRoomStorage(ABC):
    """Base class for YRoom storage.
    This class is responsible for storing, retrieving, updating and persisting the Ypy document.
    Each Django Channels Consumer should have its own YRoomStorage instance, although all consumers
    and rooms with the same room name will be connected to the same document in the end.
    Updates to the document should be sent to the shared storage, instead of each
    consumer having its own version of the YDoc.

    A full example of a Redis as temporary storage and Postgres as persistent storage is:
    ```py
    from typing import Optional
    from django.db import models
    from ypy_websocket.django_channels.yroom_storage import RedisYRoomStorage

    class YDocSnapshotManager(models.Manager):
        async def aget_snapshot(self, name) -> Optional[bytes]:
            try:
                instance: YDocSnapshot = await self.aget(name=name)
                result = instance.data
                if not isinstance(result, bytes):
                    # Postgres on psycopg2 returns memoryview
                    return bytes(result)
            except YDocSnapshot.DoesNotExist:
                return None
            else:
                return result

        async def asave_snapshot(self, name, data):
            return await self.aupdate_or_create(name=name, defaults={"data": data})

    class YDocSnapshot(models.Model):
        name = models.CharField(max_length=255, primary_key=True)
        data = models.BinaryField()
        objects = YDocSnapshotManager()

    class CustomRoomStorage(RedisYRoomStorage):
        async def load_snapshot(self) -> Optional[bytes]:
            return await YDocSnapshot.objects.aget_snapshot(self.room_name)

        async def save_snapshot(self):
            current_snapshot = await self.redis.get(self.redis_key)
            if not current_snapshot:
                return
            await YDocSnapshot.objects.asave_snapshot(
                self.room_name,
                current_snapshot,
            )
    ```
    """

    def __init__(self, room_name: str) -> None:
        self.room_name = room_name

    @abstractmethod
    async def get_document(self) -> Doc:
        """Gets the document from the storage.
        Ideally it should be retrieved first from temporary storage (e.g. Redis) and then from
        persistent storage (e.g. a database).
        Returns:
            The document with the latest changes.
        """
        ...

    @abstractmethod
    async def update_document(self, update: bytes) -> None:
        """Updates the document in the storage.
        Updates could be received by Yjs client (e.g. from a WebSocket) or from the server
        (e.g. from a Django Celery job).
        Args:
            update: The update to apply to the document.
        """
        ...

    @abstractmethod
    async def load_snapshot(self) -> Optional[bytes]:
        """Gets the document encoded as update from the database. Override this method to
        implement a persistent storage.
        Defaults to None.
        Returns:
            The latest document snapshot.
        """
        ...

    @abstractmethod
    async def save_snapshot(self) -> None:
        """Saves the document encoded as update to the database."""
        ...

    async def close(self) -> None:
        """Closes the storage connection.

        Useful for cleaning up resources like closing a database
        connection or saving the document before exiting.
        """
        pass
