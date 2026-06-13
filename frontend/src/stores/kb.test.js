import assert from 'node:assert/strict'
import { beforeEach, test } from 'node:test'
import { createPinia, setActivePinia } from 'pinia'
import {
  ACTIVE_KB_STORAGE_KEY,
  createKbStoreDefinition,
} from './kb.js'

function makeKb(id, overrides = {}) {
  return {
    id,
    name: `知识库 ${id}`,
    description: '',
    created_at: '2026-06-11T00:00:00',
    updated_at: '2026-06-11T00:00:00',
    document_count: 0,
    ...overrides,
  }
}

function createMemoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial))

  return {
    getItem(key) {
      return values.has(key) ? values.get(key) : null
    },
    setItem(key, value) {
      values.set(key, String(value))
    },
    removeItem(key) {
      values.delete(key)
    },
  }
}

function createFakeApi(initialItems = []) {
  const api = {
    calls: [],
    items: [...initialItems],

    async list() {
      api.calls.push(['list'])
      return [...api.items]
    },

    async create(payload) {
      api.calls.push(['create', payload])
      const item = makeKb(payload.id ?? `kb_${api.items.length + 1}`, payload)
      api.items = [item, ...api.items]
      return item
    },

    async update(id, payload) {
      api.calls.push(['update', id, payload])
      const item = {
        ...api.items.find((candidate) => candidate.id === id),
        ...payload,
        id,
      }
      api.items = api.items.map((candidate) =>
        candidate.id === id ? item : candidate,
      )
      return item
    },

    async remove(id) {
      api.calls.push(['remove', id])
      const item = api.items.find((candidate) => candidate.id === id)
      api.items = api.items.filter((candidate) => candidate.id !== id)
      return item
    },
  }

  return api
}

function createStore({ api, storage }) {
  setActivePinia(createPinia())
  const useStore = createKbStoreDefinition({
    apiClient: api,
    storage,
    id: `kb-test-${Math.random()}`,
  })

  return useStore()
}

beforeEach(() => {
  setActivePinia(createPinia())
})

test('fetchAll restores a persisted active knowledge base when it still exists', async () => {
  const kb1 = makeKb('kb_1')
  const kb2 = makeKb('kb_2')
  const api = createFakeApi([kb1, kb2])
  const storage = createMemoryStorage({
    [ACTIVE_KB_STORAGE_KEY]: 'kb_2',
  })
  const store = createStore({ api, storage })

  await store.fetchAll()

  assert.deepEqual(store.items, [kb1, kb2])
  assert.equal(store.activeKbId, 'kb_2')
  assert.equal(store.activeKb.id, kb2.id)
  assert.equal(storage.getItem(ACTIVE_KB_STORAGE_KEY), 'kb_2')
})

test('fetchAll falls back to the first item when persisted active id is stale', async () => {
  const kb1 = makeKb('kb_1')
  const kb2 = makeKb('kb_2')
  const api = createFakeApi([kb1, kb2])
  const storage = createMemoryStorage({
    [ACTIVE_KB_STORAGE_KEY]: 'ghost',
  })
  const store = createStore({ api, storage })

  await store.fetchAll()

  assert.equal(store.activeKbId, 'kb_1')
  assert.equal(store.activeKb.id, kb1.id)
  assert.equal(storage.getItem(ACTIVE_KB_STORAGE_KEY), 'kb_1')
})

test('create inserts the new knowledge base and makes it active', async () => {
  const api = createFakeApi([makeKb('kb_1')])
  const storage = createMemoryStorage()
  const store = createStore({ api, storage })

  const created = await store.create({
    id: 'kb_new',
    name: '产品知识库',
    description: '产品文档',
  })

  assert.equal(created.id, 'kb_new')
  assert.equal(store.items[0].id, 'kb_new')
  assert.equal(store.activeKbId, 'kb_new')
  assert.equal(storage.getItem(ACTIVE_KB_STORAGE_KEY), 'kb_new')
})

test('update replaces an existing knowledge base without changing active id', async () => {
  const kb1 = makeKb('kb_1')
  const api = createFakeApi([kb1])
  const storage = createMemoryStorage()
  const store = createStore({ api, storage })
  await store.fetchAll()
  store.setActive('kb_1')

  await store.update('kb_1', {
    name: '新名字',
  })

  assert.equal(store.items[0].name, '新名字')
  assert.equal(store.activeKbId, 'kb_1')
  assert.deepEqual(api.calls.at(-1), ['update', 'kb_1', { name: '新名字' }])
})

test('remove resets active id to the first remaining item after deleting current kb', async () => {
  const api = createFakeApi([makeKb('kb_1'), makeKb('kb_2')])
  const storage = createMemoryStorage()
  const store = createStore({ api, storage })
  await store.fetchAll()
  store.setActive('kb_1')

  await store.remove('kb_1')

  assert.deepEqual(
    store.items.map((item) => item.id),
    ['kb_2'],
  )
  assert.equal(store.activeKbId, 'kb_2')
  assert.equal(storage.getItem(ACTIVE_KB_STORAGE_KEY), 'kb_2')
})

test('remove clears active id and storage when no knowledge bases remain', async () => {
  const api = createFakeApi([makeKb('kb_1')])
  const storage = createMemoryStorage({
    [ACTIVE_KB_STORAGE_KEY]: 'kb_1',
  })
  const store = createStore({ api, storage })
  await store.fetchAll()

  await store.remove('kb_1')

  assert.deepEqual(store.items, [])
  assert.equal(store.activeKbId, '')
  assert.equal(storage.getItem(ACTIVE_KB_STORAGE_KEY), null)
})
