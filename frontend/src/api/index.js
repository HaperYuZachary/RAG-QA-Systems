import axios from 'axios'

export const API_BASE_URL = '/api/v1'

export class ApiError extends Error {
  constructor(message, { status, statusText, data } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.statusText = statusText
    this.data = data
  }
}

export const http = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

function unwrap(response) {
  return response.data
}

function withKbParam(kbId) {
  return {
    kb_id: kbId,
  }
}

function compactPayload(payload) {
  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => value !== undefined),
  )
}

export const healthApi = {
  get() {
    return http.get('/health').then(unwrap)
  },
}

export const kbApi = {
  list() {
    return http.get('/knowledge-bases').then(unwrap)
  },

  create(payload) {
    return http.post('/knowledge-bases', payload).then(unwrap)
  },

  update(kbId, payload) {
    return http.patch(`/knowledge-bases/${encodeURIComponent(kbId)}`, payload).then(unwrap)
  },

  remove(kbId) {
    return http.delete(`/knowledge-bases/${encodeURIComponent(kbId)}`).then(unwrap)
  },
}

export const uploadApi = {
  uploadDocuments({ kbId, files }, config = {}) {
    const formData = new FormData()
    formData.append('kb_id', kbId)

    for (const file of Array.from(files)) {
      formData.append('files', file)
    }

    return http.post('/upload', formData, config).then(unwrap)
  },
}

export const docsApi = {
  list(kbId) {
    return http
      .get('/docs', {
        params: withKbParam(kbId),
      })
      .then(unwrap)
  },

  get(documentId) {
    return http.get(`/docs/${encodeURIComponent(documentId)}`).then(unwrap)
  },

  getStatus(documentId) {
    return http.get(`/docs/${encodeURIComponent(documentId)}/status`).then(unwrap)
  },

  remove(documentId) {
    return http.delete(`/docs/${encodeURIComponent(documentId)}`).then(unwrap)
  },
}

export const debugApi = {
  search({ kbId, kb_id, query, topK, top_k }) {
    return http
      .post(
        '/debug/search',
        compactPayload({
          kb_id: kb_id ?? kbId,
          query,
          top_k: top_k ?? topK,
        }),
      )
      .then(unwrap)
  },
}

export function parseSseFrame(frameText) {
  const event = {
    event: 'message',
    data: '',
  }
  const dataLines = []

  for (const rawLine of frameText.split(/\r\n|\n|\r/)) {
    if (!rawLine || rawLine.startsWith(':')) {
      continue
    }

    const separatorIndex = rawLine.indexOf(':')
    const field =
      separatorIndex === -1 ? rawLine : rawLine.slice(0, separatorIndex)
    let value = separatorIndex === -1 ? '' : rawLine.slice(separatorIndex + 1)

    if (value.startsWith(' ')) {
      value = value.slice(1)
    }

    if (field === 'event') {
      event.event = value || 'message'
      continue
    }

    if (field === 'data') {
      dataLines.push(value)
    }
  }

  const dataText = dataLines.join('\n')
  event.data = parseSseData(dataText)

  return event
}

export function splitSseBuffer(buffer) {
  const frames = []
  let rest = buffer

  while (rest.length > 0) {
    const separatorMatch = rest.match(/\r\n\r\n|\n\n|\r\r/)

    if (!separatorMatch || separatorMatch.index === undefined) {
      break
    }

    frames.push(rest.slice(0, separatorMatch.index))
    rest = rest.slice(separatorMatch.index + separatorMatch[0].length)
  }

  return {
    frames,
    buffer: rest,
  }
}

export async function streamChat(request, callbacks = {}, options = {}) {
  const fetchImpl = options.fetch ?? globalThis.fetch

  if (typeof fetchImpl !== 'function') {
    throw new ApiError('Fetch API is not available in this runtime')
  }

  const response = await fetchImpl(`${options.baseURL ?? API_BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
      ...options.headers,
    },
    body: JSON.stringify(buildChatPayload(request)),
    signal: options.signal,
  })

  await assertStreamResponseOk(response)
  await readSseStream(response.body, callbacks)
}

export const chatApi = {
  stream: streamChat,
}

export async function readSseStream(stream, callbacks = {}) {
  if (!stream?.getReader) {
    throw new ApiError('Readable stream is not available on the response body')
  }

  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { value, done } = await reader.read()

      if (done) {
        break
      }

      buffer += decoder.decode(value, { stream: true })
      const result = splitSseBuffer(buffer)
      buffer = result.buffer

      for (const frame of result.frames) {
        dispatchSseEvent(parseSseFrame(frame), callbacks)
      }
    }

    buffer += decoder.decode()
    const result = splitSseBuffer(buffer)
    buffer = result.buffer

    for (const frame of result.frames) {
      dispatchSseEvent(parseSseFrame(frame), callbacks)
    }

    if (buffer.trim()) {
      dispatchSseEvent(parseSseFrame(buffer), callbacks)
    }
  } finally {
    reader.releaseLock()
  }
}

function dispatchSseEvent(event, callbacks) {
  callbacks.onEvent?.(event)

  if (event.event === 'chunk') {
    callbacks.onChunk?.(event.data?.delta ?? '', event.data)
    return
  }

  if (event.event === 'sources') {
    callbacks.onSources?.(event.data?.sources ?? [], event.data)
    return
  }

  if (event.event === 'done') {
    callbacks.onDone?.(event.data)
    return
  }

  if (event.event === 'error') {
    callbacks.onError?.(event.data)
    throw new ApiError(event.data?.message ?? 'Chat stream failed', {
      data: event.data,
    })
  }

  callbacks.onUnknownEvent?.(event)
}

function buildChatPayload({ kbId, kb_id, question, conversationId, conversation_id }) {
  return compactPayload({
    kb_id: kb_id ?? kbId,
    question,
    conversation_id: conversation_id ?? conversationId,
  })
}

function parseSseData(dataText) {
  if (!dataText) {
    return ''
  }

  try {
    return JSON.parse(dataText)
  } catch {
    return dataText
  }
}

async function assertStreamResponseOk(response) {
  if (response.ok) {
    return
  }

  const responseText = await safeReadResponseText(response)

  throw new ApiError(
    `Chat stream request failed (${response.status} ${response.statusText})`,
    {
      status: response.status,
      statusText: response.statusText,
      data: parseSseData(responseText),
    },
  )
}

async function safeReadResponseText(response) {
  try {
    return await response.text()
  } catch {
    return ''
  }
}
