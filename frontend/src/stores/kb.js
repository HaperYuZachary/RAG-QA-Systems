import { defineStore } from 'pinia'
import { kbApi } from '../api/index.js'

export const ACTIVE_KB_STORAGE_KEY = 'rag.activeKbId'

export function createKbStoreDefinition({
  id = 'kb',
  apiClient = kbApi,
  storage = getBrowserStorage(),
} = {}) {
  return defineStore(id, {
    state: () => ({
      items: [],
      activeKbId: readStoredActiveKbId(storage),
      loading: false,
      error: null,
    }),

    getters: {
      activeKb(state) {
        return (
          state.items.find((item) => item.id === state.activeKbId) ?? null
        )
      },
    },

    actions: {
      async fetchAll() {
        return runWithState(this, async () => {
          const items = normalizeListResponse(await apiClient.list())
          this.items = items
          this.ensureActive()
          return items
        })
      },

      async create(payload) {
        return runWithState(this, async () => {
          const created = await apiClient.create(payload)
          this.items = upsertFirst(this.items, created)
          this.setActive(created.id)
          return created
        })
      },

      async update(id, payload) {
        return runWithState(this, async () => {
          const updated = await apiClient.update(id, payload)
          this.items = this.items.map((item) =>
            item.id === id ? updated : item,
          )
          this.ensureActive()
          return updated
        })
      },

      async remove(id) {
        return runWithState(this, async () => {
          const removed = await apiClient.remove(id)
          this.items = this.items.filter((item) => item.id !== id)

          if (this.activeKbId === id) {
            this.activeKbId = ''
          }

          this.ensureActive()
          return removed
        })
      },

      setActive(id) {
        const nextId = this.items.some((item) => item.id === id) ? id : ''
        this.activeKbId = nextId
        persistActiveKbId(storage, nextId)
      },

      ensureActive() {
        const hasActive = this.items.some((item) => item.id === this.activeKbId)

        if (hasActive) {
          persistActiveKbId(storage, this.activeKbId)
          return
        }

        const fallbackId = this.items[0]?.id ?? ''
        this.activeKbId = fallbackId
        persistActiveKbId(storage, fallbackId)
      },
    },
  })
}

export const useKbStore = createKbStoreDefinition()

async function runWithState(store, action) {
  store.loading = true
  store.error = null

  try {
    return await action()
  } catch (error) {
    store.error = error
    throw error
  } finally {
    store.loading = false
  }
}

function normalizeListResponse(response) {
  if (Array.isArray(response)) {
    return response
  }

  if (Array.isArray(response?.items)) {
    return response.items
  }

  return []
}

function upsertFirst(items, nextItem) {
  return [
    nextItem,
    ...items.filter((item) => item.id !== nextItem.id),
  ]
}

function getBrowserStorage() {
  try {
    return globalThis.localStorage
  } catch {
    return null
  }
}

function readStoredActiveKbId(storage) {
  try {
    return storage?.getItem(ACTIVE_KB_STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

function persistActiveKbId(storage, activeKbId) {
  if (!storage) {
    return
  }

  try {
    if (activeKbId) {
      storage.setItem(ACTIVE_KB_STORAGE_KEY, activeKbId)
    } else {
      storage.removeItem(ACTIVE_KB_STORAGE_KEY)
    }
  } catch {
    // localStorage can be unavailable in private mode; the store remains usable.
  }
}
