const Y = require('yjs')
const WebsocketProvider = require('y-websocket').WebsocketProvider
const ws = require('ws')

const port = process.argv[2]
const ydoc = new Y.Doc()
const ymap = ydoc.getMap('map')

function increment(resolve) {
  ymap.set('out', ymap.get('in') + 1);
  resolve();
}

ymap.observe(event => {
  if (event.transaction.local || !event.changes.keys.has('in')) {
    return
  }
  new Promise(increment);
})

const wsProvider = new WebsocketProvider(
  `ws://127.0.0.1:${port}`, 'my-roomname',
  ydoc,
  { WebSocketPolyfill: ws }
)
