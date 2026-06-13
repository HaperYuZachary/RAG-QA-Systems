import assert from 'node:assert/strict'
import { beforeEach, test } from 'node:test'
import { createPinia, setActivePinia } from 'pinia'
import { createDebugStoreDefinition } from './debug.js'

function makeResult(overrides = {}) {
  return {
    query: '年假',
    hits: [
      {
        id: 'chunk_1',
        text: '员工满一年享有五天年假。',
        metadata: {
          document_id: 'doc_1',
          document_name: '员工手册.md',
          page: 3,
        },
        vector_rank: 1,
        vector_distance: 0.12,
        bm25_rank: null,
        bm25_score: null,
        rrf_score: 0.031,
        rerank_score: 0.92,
      },
    ],
    timings: {
      embedding_ms: 1.2,
      retrieval_ms: 3.4,
      rerank_ms: 5.6,
      total_ms: 10.2,
    },
    ...overrides,
  }
}

function createFakeApi(result = makeResult()) {
  const api = {
    calls: [],

    async search(payload) {
      api.calls.push(payload)
      return result
    },
  }

  return api
}

function createStore(api) {
  setActivePinia(createPinia())
  const useStore = createDebugStoreDefinition({
    apiClient: api,
    id: `debug-test-${Math.random()}`,
  })

  return useStore()
}

beforeEach(() => {
  setActivePinia(createPinia())
})

test('search sends the selected knowledge base, trimmed query, and topK then stores the result', async () => {
  const result = makeResult()
  const api = createFakeApi(result)
  const store = createStore(api)

  const returned = await store.search({
    kbId: ' kb_1 ',
    query: ' 年假 ',
    topK: 7,
  })

  assert.deepEqual(api.calls, [
    {
      kbId: 'kb_1',
      query: '年假',
      topK: 7,
    },
  ])
  assert.deepEqual(returned, result)
  assert.deepEqual(store.result, result)
  assert.equal(store.loading, false)
  assert.equal(store.error, null)
})

test('search blocks blank query and missing knowledge base without calling the api', async () => {
  const api = createFakeApi()
  const store = createStore(api)
  store.result = makeResult({ query: 'stale' })
  store.error = new Error('stale')

  const blankQueryResult = await store.search({
    kbId: 'kb_1',
    query: '   ',
    topK: 5,
  })
  const missingKbResult = await store.search({
    kbId: '',
    query: '年假',
    topK: 5,
  })

  assert.equal(blankQueryResult, null)
  assert.equal(missingKbResult, null)
  assert.deepEqual(api.calls, [])
  assert.equal(store.result, null)
  assert.equal(store.loading, false)
  assert.equal(store.error, null)
})

test('search exposes failures through error and clears loading without replacing the previous result', async () => {
  const previousResult = makeResult({ query: '之前的问题' })
  const error = new Error('network down')
  const api = {
    calls: [],

    async search(payload) {
      api.calls.push(payload)
      throw error
    },
  }
  const store = createStore(api)
  store.result = previousResult

  await assert.rejects(
    store.search({
      kbId: 'kb_1',
      query: '年假',
      topK: 3,
    }),
    /network down/,
  )

  assert.deepEqual(api.calls, [
    {
      kbId: 'kb_1',
      query: '年假',
      topK: 3,
    },
  ])
  assert.deepEqual(store.result, previousResult)
  assert.equal(store.loading, false)
  assert.equal(store.error, error)
})
