const Y = require('yjs')
const WebsocketProvider = require('y-websocket').WebsocketProvider
const ws = require('ws')

const port = process.argv[2]
const ydoc = new Y.Doc()

const wsProvider = new WebsocketProvider(
  `ws://127.0.0.1:${port}`, 'my-roomname',
  ydoc,
  { WebSocketPolyfill: ws }
)

wsProvider.on('sync', () => {
  const map0 = ydoc.getMap('map0')
  const undoManager = new Y.UndoManager(map0, {
    trackedOrigins: new Set([wsProvider]),
  })
  map0.set('key0', 'val0')
  undoManager.clear()

  function undo() {
    undoManager.undo()
  }

  map0.observe((event, transaction) => {
    setTimeout(undo, 100)
  })
})
