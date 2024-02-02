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

var clock = -1;

ymap.observe((event) => {
  event.changes.keys.forEach((change, key) => {
    if (key === "clock") {
      const clk = ymap.get("clock");
      if (clk > clock) {
        ymap.set("out", ymap.get("in") + 1);
        clock = clk + 1;
        ymap.set("clock", clock);
      }
    }
  });
});
