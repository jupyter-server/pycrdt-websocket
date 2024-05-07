from __future__ import annotations

from contextlib import AsyncExitStack
from functools import partial
from inspect import isawaitable
from logging import Logger, getLogger
from typing import Awaitable, Callable

from anyio import (
    TASK_STATUS_IGNORED,
    Event,
    Lock,
    create_memory_object_stream,
    create_task_group,
)
from anyio.abc import TaskGroup, TaskStatus
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pycrdt import Doc, Subscription

from .awareness import Awareness
from .websocket import Websocket
from .ystore import BaseYStore
from .yutils import (
    YMessageType,
    create_update_message,
    process_sync_message,
    put_updates,
    sync,
)


class YRoom:
    clients: list
    ydoc: Doc
    ystore: BaseYStore | None
    ready_event: Event
    _on_message: Callable[[bytes], Awaitable[bool] | bool] | None
    _update_send_stream: MemoryObjectSendStream
    _update_receive_stream: MemoryObjectReceiveStream
    _task_group: TaskGroup | None = None
    _started: Event | None = None
    _stopped: Event
    __start_lock: Lock | None = None
    _subscription: Subscription | None = None

    def __init__(
        self,
        ready: bool = True,
        ystore: BaseYStore | None = None,
        exception_handler: Callable[[Exception, Logger], bool] | None = None,
        log: Logger | None = None,
    ):
        """Initialize the object.

        The YRoom instance should preferably be used as an async context manager:
        ```py
        async with room:
            ...
        ```
        However, a lower-level API can also be used:
        ```py
        task = asyncio.create_task(room.start())
        await room.started.wait()
        ...
        await room.stop()
        ```

        Arguments:
            ready: Whether the internal YDoc is ready to be synchronized right away.
            ystore: An optional store in which to persist document updates.
            exception_handler: An optional callback to call when an exception is raised, that
            returns True if the exception was handled.
            log: An optional logger.
        """
        self.ydoc = Doc()
        self.awareness = Awareness(self.ydoc)
        self.ready_event = Event()
        self.ready = ready
        self.ystore = ystore
        self.log = log or getLogger(__name__)
        self.clients = []
        self._on_message = None
        self.exception_handler = exception_handler
        self._stopped = Event()

    @property
    def _start_lock(self) -> Lock:
        if self.__start_lock is None:
            self.__start_lock = Lock()
        return self.__start_lock

    @property
    def started(self):
        """An async event that is set when the YRoom provider has started."""
        if self._started is None:
            self._started = Event()
        return self._started

    @property
    def ready(self) -> bool:
        """
        Returns:
            True is the internal YDoc is ready to be synchronized.
        """
        return self.ready_event.is_set()

    @ready.setter
    def ready(self, value: bool) -> None:
        """
        Arguments:
            value: True if the internal YDoc is ready to be synchronized, False otherwise."""
        if value and not self.ready_event.is_set():
            self.ready_event.set()

    async def _watch_ready(self):
        await self.ready_event.wait()
        self._subscription = self.ydoc.observe(partial(put_updates, self._update_send_stream))

    @property
    def on_message(self) -> Callable[[bytes], Awaitable[bool] | bool] | None:
        """
        Returns:
            The optional callback to call when a message is received.
        """
        return self._on_message

    @on_message.setter
    def on_message(self, value: Callable[[bytes], Awaitable[bool] | bool] | None):
        """
        Arguments:
            value: An optional callback to call when a message is received.
            If the callback returns True, the message is skipped.
        """
        self._on_message = value

    async def _broadcast_updates(self):
        if self.ystore is not None:
            async with self.ystore.start_lock:
                if not self.ystore.started.is_set():
                    await self._task_group.start(self.ystore.start)

        async with self._update_receive_stream:
            async for update in self._update_receive_stream:
                if self._task_group.cancel_scope.cancel_called:
                    return
                # broadcast internal ydoc's update to all clients, that includes changes from the
                # clients and changes from the backend (out-of-band changes)
                for client in self.clients:
                    try:
                        self.log.debug("Sending Y update to client with endpoint: %s", client.path)
                        message = create_update_message(update)
                        self._task_group.start_soon(client.send, message)
                    except Exception as exception:
                        self._handle_exception(exception)
                if self.ystore:
                    try:
                        self._task_group.start_soon(self.ystore.write, update)
                        self.log.debug("Writing Y update to YStore")
                    except Exception as exception:
                        self._handle_exception(exception)

    async def __aenter__(self) -> YRoom:
        async with self._start_lock:
            if self._task_group is not None:
                raise RuntimeError("YRoom already running")

            async with AsyncExitStack() as exit_stack:
                self._task_group = await exit_stack.enter_async_context(create_task_group())
                self._exit_stack = exit_stack.pop_all()
                await self._task_group.start(partial(self.start, from_context_manager=True))

        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        await self.stop()
        return await self._exit_stack.__aexit__(exc_type, exc_value, exc_tb)

    def _handle_exception(self, exception: Exception) -> None:
        exception_handled = False
        if self.exception_handler is not None:
            exception_handled = self.exception_handler(exception, self.log)
        if not exception_handled:
            raise exception

    async def start(
        self,
        *,
        task_status: TaskStatus[None] = TASK_STATUS_IGNORED,
        from_context_manager: bool = False,
    ):
        """Start the room.

        Arguments:
            task_status: The status to set when the task has started.
        """
        if from_context_manager:
            task_status.started()
            self.started.set()
            self._update_send_stream, self._update_receive_stream = create_memory_object_stream(
                max_buffer_size=65536
            )
            assert self._task_group is not None
            self._task_group.start_soon(self._stopped.wait)
            self._task_group.start_soon(self._watch_ready)
            self._task_group.start_soon(self._broadcast_updates)
            return

        async with self._start_lock:
            if self._task_group is not None:
                raise RuntimeError("YRoom already running")

            while True:
                try:
                    async with create_task_group() as self._task_group:
                        if not self.started.is_set():
                            task_status.started()
                            self.started.set()
                        self._update_send_stream, self._update_receive_stream = (
                            create_memory_object_stream(max_buffer_size=65536)
                        )
                        self._task_group.start_soon(self._stopped.wait)
                        self._task_group.start_soon(self._watch_ready)
                        self._task_group.start_soon(self._broadcast_updates)
                    return
                except Exception as exception:
                    self._handle_exception(exception)

    async def stop(self) -> None:
        """Stop the room."""
        if self._task_group is None:
            raise RuntimeError("YRoom not running")
        self._stopped.set()
        self._task_group.cancel_scope.cancel()
        self._task_group = None
        if self._subscription is not None:
            self.ydoc.unobserve(self._subscription)

    async def serve(self, websocket: Websocket):
        """Serve a client.

        Arguments:
            websocket: The WebSocket through which to serve the client.
        """
        try:
            async with create_task_group() as tg:
                self.clients.append(websocket)
                await sync(self.ydoc, websocket, self.log)
                async for message in websocket:
                    # filter messages (e.g. awareness)
                    skip = False
                    if self.on_message:
                        _skip = self.on_message(message)
                        skip = await _skip if isawaitable(_skip) else _skip
                    if skip:
                        continue
                    message_type = message[0]
                    if message_type == YMessageType.SYNC:
                        # update our internal state in the background
                        # changes to the internal state are then forwarded to all clients
                        # and stored in the YStore (if any)
                        tg.start_soon(
                            process_sync_message, message[1:], self.ydoc, websocket, self.log
                        )
                    elif message_type == YMessageType.AWARENESS:
                        # forward awareness messages from this client to all clients,
                        # including itself, because it's used to keep the connection alive
                        self.log.debug(
                            "Received %s message from endpoint: %s",
                            YMessageType.AWARENESS.name,
                            websocket.path,
                        )
                        for client in self.clients:
                            self.log.debug(
                                "Sending Y awareness from client with endpoint "
                                "%s to client with endpoint: %s",
                                websocket.path,
                                client.path,
                            )
                            tg.start_soon(client.send, message)
                # remove this client
                self.clients = [c for c in self.clients if c != websocket]
        except Exception as exception:
            self._handle_exception(exception)
