import assert from 'node:assert/strict'
import test from 'node:test'
import { parseSseFrame, streamChat } from './index.js'

function createTextStream(chunks) {
  const encoder = new TextEncoder()

  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk))
      }
      controller.close()
    },
  })
}

test('parseSseFrame parses event name and JSON data payload', () => {
  const frame = [
    'event: sources',
    'data: {"sources":[{"id":"chunk_1"}],"invalid_references":[]}',
  ].join('\n')

  assert.deepEqual(parseSseFrame(frame), {
    event: 'sources',
    data: {
      sources: [{ id: 'chunk_1' }],
      invalid_references: [],
    },
  })
})

test('streamChat posts JSON body and dispatches split SSE frames in order', async () => {
  const received = {
    chunks: [],
    sources: [],
    done: [],
    events: [],
  }
  let request

  const fetchStub = async (url, init) => {
    request = { url, init }

    return new Response(
      createTextStream([
        'event: chunk\ndata: {"delta":"你',
        '好"}\n\n',
        'event: sources\n',
        'data: {"sources":[{"id":"chunk_1"}],"invalid_references":[]}\n\n',
        'event: done\ndata: {"conversation_id":"conv_1","answer":"你好"}\n\n',
      ]),
      {
        status: 200,
        headers: {
          'content-type': 'text/event-stream',
        },
      },
    )
  }

  await streamChat(
    {
      kbId: 'kb_1',
      question: '年假有几天？',
      conversationId: 'conv_1',
    },
    {
      onChunk(delta) {
        received.chunks.push(delta)
      },
      onSources(sources, payload) {
        received.sources.push({ sources, payload })
      },
      onDone(payload) {
        received.done.push(payload)
      },
      onEvent(event) {
        received.events.push(event.event)
      },
    },
    { fetch: fetchStub },
  )

  assert.equal(request.url, '/api/v1/chat')
  assert.equal(request.init.method, 'POST')
  assert.equal(request.init.headers.Accept, 'text/event-stream')
  assert.equal(request.init.headers['Content-Type'], 'application/json')
  assert.equal(
    request.init.body,
    JSON.stringify({
      kb_id: 'kb_1',
      question: '年假有几天？',
      conversation_id: 'conv_1',
    }),
  )

  assert.deepEqual(received.events, ['chunk', 'sources', 'done'])
  assert.deepEqual(received.chunks, ['你好'])
  assert.deepEqual(received.sources, [
    {
      sources: [{ id: 'chunk_1' }],
      payload: {
        sources: [{ id: 'chunk_1' }],
        invalid_references: [],
      },
    },
  ])
  assert.deepEqual(received.done, [
    {
      conversation_id: 'conv_1',
      answer: '你好',
    },
  ])
})

test('streamChat throws a useful error when the server rejects the request', async () => {
  const fetchStub = async () =>
    new Response(JSON.stringify({ detail: 'invalid request' }), {
      status: 422,
      statusText: 'Unprocessable Entity',
      headers: {
        'content-type': 'application/json',
      },
    })

  await assert.rejects(
    streamChat(
      {
        kbId: 'kb_1',
        question: ' ',
      },
      {},
      { fetch: fetchStub },
    ),
    /Chat stream request failed \(422 Unprocessable Entity\)/,
  )
})

test('streamChat rejects when the SSE stream emits an error event', async () => {
  const received = {
    chunks: [],
    errors: [],
  }
  const fetchStub = async () =>
    new Response(
      createTextStream([
        'event: chunk\ndata: {"delta":"处理中"}\n\n',
        'event: error\ndata: {"message":"generator unavailable","type":"RuntimeError"}\n\n',
      ]),
      {
        status: 200,
        headers: {
          'content-type': 'text/event-stream',
        },
      },
    )

  await assert.rejects(
    streamChat(
      {
        kbId: 'kb_1',
        question: '年假有几天？',
      },
      {
        onChunk(delta) {
          received.chunks.push(delta)
        },
        onError(errorPayload) {
          received.errors.push(errorPayload)
        },
      },
      { fetch: fetchStub },
    ),
    /generator unavailable/,
  )

  assert.deepEqual(received.chunks, ['处理中'])
  assert.deepEqual(received.errors, [
    {
      message: 'generator unavailable',
      type: 'RuntimeError',
    },
  ])
})
