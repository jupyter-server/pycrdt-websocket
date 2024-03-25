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
  const ycells = ydoc.getArray('cells')
  const ystate = ydoc.getMap('state')

  const cells = [new Y.Map([['source', new Y.Text('1 + 2')], ['metadata', {'foo': 'bar'}]])]
  const state = {'dirty': false}
  ycells.push(cells)
  ystate.set('state', state)
})
