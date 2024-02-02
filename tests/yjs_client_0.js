const Y = require("yjs");
const WebsocketProvider = require("y-websocket").WebsocketProvider;

const ydoc = new Y.Doc();
const ymap = ydoc.getMap("ymap");
const ws = require("ws");

const wsProvider = new WebsocketProvider(
  "ws://127.0.0.1:1234",
  "my-roomname",
  ydoc,
  { WebSocketPolyfill: ws }
);

wsProvider.on("status", (event) => {
  console.log(event.status);
});

ymap.observe((event) => {
  // only do something when another client updates `ymap.clock`
  if (event.transaction.local || !event.changes.keys.has("clock")) {
    return;
  }

  const clock = ymap.get("clock");
  ymap.set("out", ymap.get("in") + 1);
  ymap.set("clock", clock + 1);
});
