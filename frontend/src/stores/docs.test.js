import assert from 'node:assert/strict'
import { beforeEach, test } from 'node:test'
import { createPinia, setActivePinia } from 'pinia'
import { createDocsStoreDefinition } from './docs.js'

function makeDoc(id, overrides = {}) {
  return {
    id,
    kb_id: 'kb_1',
    filename: `${id}.md`,
    file_type: 'md',
    file_size: 100,
    chunk_count: 3,
    status: 'ready',
    error_msg: null,
    created_at: '2026-06-11T00:00:00',
    ...overrides,
  }
}

function createFakeApi(initialItems = []) {
  const api = {
    calls: [],
    itemsByKb: new Map(),

    async list(kbId) {
      api.calls.push(['list', kbId])
      return [...(api.itemsByKb.get(kbId) ?? [])]
    },

    async uploadDocuments({ kbId, files }) {
      api.calls.push(['uploadDocuments', kbId, Array.from(files).map((file) => file.name)])
      const uploaded = Array.from(files).map((file, index) =>
        makeDoc(`doc_upload_${index + 1}`, {
          kb_id: kbId,
          filename: file.name,
        }),
      )
      api.itemsByKb.set(kbId, uploaded)

      return {
        documents: uploaded.map((doc) => ({
          document_id: doc.id,
          filename: doc.filename,
          status: doc.status,
          chunk_count: doc.chunk_count,
          duplicate: false,
          error_msg: null,
        })),
      }
    },

    async remove(docId) {
      api.calls.push(['remove', docId])

      for (const [kbId, items] of api.itemsByKb.entries()) {
        const deleted = items.find((item) => item.id === docId)
        if (!deleted) {
          continue
        }

        api.itemsByKb.set(
          kbId,
          items.filter((item) => item.id !== docId),
        )
        return deleted
      }

      return makeDoc(docId)
    },
  }

  for (const item of initialItems) {
    api.itemsByKb.set(item.kb_id, [...(api.itemsByKb.get(item.kb_id) ?? []), item])
  }

  return api
}

function createStore(api) {
  setActivePinia(createPinia())
  const useStore = createDocsStoreDefinition({
    apiClient: api,
    id: `docs-test-${Math.random()}`,
  })

  return useStore()
}

beforeEach(() => {
  setActivePinia(createPinia())
})

test('fetchByKb loads documents for the selected knowledge base', async () => {
  const docs = [makeDoc('doc_1'), makeDoc('doc_2')]
  const api = createFakeApi(docs)
  const store = createStore(api)

  const result = await store.fetchByKb('kb_1')

  assert.deepEqual(result, docs)
  assert.deepEqual(store.items, docs)
  assert.equal(store.loading, false)
  assert.equal(store.uploading, false)
  assert.equal(store.error, null)
  assert.deepEqual(api.calls, [['list', 'kb_1']])
})

test('fetchByKb clears documents when kbId is blank', async () => {
  const api = createFakeApi([makeDoc('doc_1')])
  const store = createStore(api)
  store.items = [makeDoc('stale')]

  const result = await store.fetchByKb('')

  assert.deepEqual(result, [])
  assert.deepEqual(store.items, [])
  assert.deepEqual(api.calls, [])
})

test('upload sends all files once and refreshes the current knowledge base documents', async () => {
  const api = createFakeApi()
  const store = createStore(api)
  const files = [{ name: 'hr.md' }, { name: 'benefits.pdf' }]

  const result = await store.upload({
    kbId: 'kb_1',
    files,
  })

  assert.deepEqual(result.documents.map((item) => item.filename), [
    'hr.md',
    'benefits.pdf',
  ])
  assert.deepEqual(
    store.items.map((item) => item.filename),
    ['hr.md', 'benefits.pdf'],
  )
  assert.equal(store.uploading, false)
  assert.equal(store.loading, false)
  assert.deepEqual(api.calls, [
    ['uploadDocuments', 'kb_1', ['hr.md', 'benefits.pdf']],
    ['list', 'kb_1'],
  ])
})

test('remove deletes the document and refreshes using its kb_id from current items', async () => {
  const api = createFakeApi([
    makeDoc('doc_1', { kb_id: 'kb_1' }),
    makeDoc('doc_2', { kb_id: 'kb_1' }),
  ])
  const store = createStore(api)
  await store.fetchByKb('kb_1')

  const deleted = await store.remove('doc_1')

  assert.equal(deleted.id, 'doc_1')
  assert.deepEqual(
    store.items.map((item) => item.id),
    ['doc_2'],
  )
  assert.deepEqual(api.calls, [
    ['list', 'kb_1'],
    ['remove', 'doc_1'],
    ['list', 'kb_1'],
  ])
})

test('remove falls back to the deleted response kb_id when the item is not in state', async () => {
  const api = createFakeApi([makeDoc('doc_ghost', { kb_id: 'kb_2' })])
  const store = createStore(api)

  await store.remove('doc_ghost')

  assert.deepEqual(api.calls, [
    ['remove', 'doc_ghost'],
    ['list', 'kb_2'],
  ])
})

test('actions expose failures through error and reset busy flags', async () => {
  const error = new Error('network down')
  const api = {
    calls: [],
    async list(kbId) {
      api.calls.push(['list', kbId])
      throw error
    },
    async uploadDocuments() {
      api.calls.push(['uploadDocuments'])
      throw error
    },
    async remove() {
      api.calls.push(['remove'])
      throw error
    },
  }
  const store = createStore(api)

  await assert.rejects(store.fetchByKb('kb_1'), /network down/)
  assert.equal(store.error, error)
  assert.equal(store.loading, false)

  await assert.rejects(
    store.upload({
      kbId: 'kb_1',
      files: [{ name: 'bad.md' }],
    }),
    /network down/,
  )
  assert.equal(store.error, error)
  assert.equal(store.uploading, false)
})
