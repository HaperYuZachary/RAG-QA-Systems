import assert from 'node:assert/strict'
import { beforeEach, test } from 'node:test'
import { createPinia, setActivePinia } from 'pinia'
import { createChatStoreDefinition } from './chat.js'

function createControlledStream() {
  let resolveStream
  let rejectStream

  const stream = {
    calls: [],

    streamImpl(request, callbacks, options) {
      stream.calls.push({ request, callbacks, options })

      return new Promise((resolve, reject) => {
        resolveStream = resolve
        rejectStream = reject
      })
    },

    resolve(value) {
      resolveStream?.(value)
    },

    reject(error) {
      rejectStream?.(error)
    },
  }

  return stream
}

function createStore(streamImpl) {
  setActivePinia(createPinia())
  const useStore = createChatStoreDefinition({
    id: `chat-test-${Math.random()}`,
    streamImpl,
  })

  return useStore()
}

beforeEach(() => {
  setActivePinia(createPinia())
})

test('ask streams chunks into an assistant placeholder and stores sources and conversation id', async () => {
  const stream = createControlledStream()
  const store = createStore(stream.streamImpl)

  const askPromise = store.ask({
    kbId: 'kb_1',
    question: '年假有几天？',
  })

  assert.equal(store.streaming, true)
  assert.equal(store.error, null)
  assert.equal(stream.calls.length, 1)
  assert.deepEqual(stream.calls[0].request, {
    kbId: 'kb_1',
    question: '年假有几天？',
    conversationId: undefined,
  })

  assert.equal(store.messages.length, 2)
  assert.equal(store.messages[0].role, 'user')
  assert.equal(store.messages[0].content, '年假有几天？')
  assert.equal(store.messages[1].role, 'assistant')
  assert.equal(store.messages[1].content, '')
  assert.equal(store.messages[1].status, 'streaming')

  stream.calls[0].callbacks.onChunk('年假')
  stream.calls[0].callbacks.onChunk('是 10 天')
  stream.calls[0].callbacks.onSources([
    {
      id: 'chunk_1',
      document_name: 'handbook.md',
      text: '年假是 10 天',
    },
  ])
  stream.calls[0].callbacks.onDone({
    conversation_id: 'conv_1',
  })
  stream.resolve()
  await askPromise

  assert.equal(store.messages[1].content, '年假是 10 天')
  assert.deepEqual(store.messages[1].sources, [
    {
      id: 'chunk_1',
      document_name: 'handbook.md',
      text: '年假是 10 天',
    },
  ])
  assert.equal(store.messages[1].status, 'done')
  assert.equal(store.conversationId, 'conv_1')
  assert.equal(store.streaming, false)
})

test('ask sends the stored conversation id on the next turn', async () => {
  const calls = []
  const store = createStore(async (request, callbacks) => {
    calls.push(request)
    callbacks.onDone({
      conversation_id: request.question === '第一问' ? 'conv_1' : 'conv_2',
    })
  })

  await store.ask({ kbId: 'kb_1', question: '第一问' })
  await store.ask({ kbId: 'kb_1', question: '第二问' })

  assert.equal(calls[0].conversationId, undefined)
  assert.equal(calls[1].conversationId, 'conv_1')
  assert.equal(store.conversationId, 'conv_2')
})

test('ask keeps the assistant placeholder and marks it as error when streaming fails', async () => {
  const error = new Error('stream failed')
  const store = createStore(async () => {
    throw error
  })

  await assert.rejects(
    store.ask({
      kbId: 'kb_1',
      question: '会失败吗？',
    }),
    /stream failed/,
  )

  assert.equal(store.streaming, false)
  assert.equal(store.error, error)
  assert.equal(store.messages.length, 2)
  assert.equal(store.messages[1].role, 'assistant')
  assert.equal(store.messages[1].status, 'error')
})

test('stop aborts the active stream without turning the assistant message into an error', async () => {
  const stream = createControlledStream()
  const store = createStore(stream.streamImpl)

  const askPromise = store.ask({
    kbId: 'kb_1',
    question: '请继续生成',
  })
  const signal = stream.calls[0].options.signal

  store.stop()

  assert.equal(signal.aborted, true)
  assert.equal(store.streaming, false)
  assert.equal(store.error, null)
  assert.equal(store.messages[1].status, 'stopped')

  stream.reject(new DOMException('Aborted', 'AbortError'))
  await askPromise

  assert.equal(store.messages[1].status, 'stopped')
  assert.equal(store.error, null)
})

test('a stopped stream settling late does not clear streaming for the next ask', async () => {
  const firstStream = createControlledStream()
  const secondStream = createControlledStream()
  let callIndex = 0
  const store = createStore((request, callbacks, options) => {
    callIndex += 1

    if (callIndex === 1) {
      return firstStream.streamImpl(request, callbacks, options)
    }

    return secondStream.streamImpl(request, callbacks, options)
  })

  const firstAsk = store.ask({
    kbId: 'kb_1',
    question: '第一问',
  })
  store.stop()

  const secondAsk = store.ask({
    kbId: 'kb_1',
    question: '第二问',
  })

  assert.equal(store.streaming, true)

  firstStream.reject(new DOMException('Aborted', 'AbortError'))
  await firstAsk

  assert.equal(store.streaming, true)
  assert.equal(store.messages[1].status, 'stopped')
  assert.equal(store.messages[3].status, 'streaming')

  secondStream.calls[0].callbacks.onDone({ conversation_id: 'conv_2' })
  secondStream.resolve()
  await secondAsk

  assert.equal(store.streaming, false)
  assert.equal(store.messages[3].status, 'done')
})

test('reset aborts in-flight generation and clears the conversation', async () => {
  const stream = createControlledStream()
  const store = createStore(stream.streamImpl)

  const askPromise = store.ask({
    kbId: 'kb_1',
    question: '先问一轮',
  })
  stream.calls[0].callbacks.onDone({ conversation_id: 'conv_1' })

  store.reset()

  assert.equal(stream.calls[0].options.signal.aborted, true)
  assert.deepEqual(store.messages, [])
  assert.equal(store.conversationId, '')
  assert.equal(store.streaming, false)
  assert.equal(store.error, null)

  stream.reject(new DOMException('Aborted', 'AbortError'))
  await askPromise
})
