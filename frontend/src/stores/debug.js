import { defineStore } from 'pinia'
import { debugApi } from '../api/index.js'

export function createDebugStoreDefinition({
  id = 'debug',
  apiClient = debugApi,
} = {}) {
  return defineStore(id, {
    state: () => ({
      result: null,
      loading: false,
      error: null,
    }),

    actions: {
      async search({ kbId, kb_id, query, topK, top_k } = {}) {
        const normalizedKbId = normalizeText(kb_id ?? kbId)
        const normalizedQuery = normalizeText(query)
        const normalizedTopK = top_k ?? topK

        if (!normalizedKbId || !normalizedQuery) {
          this.result = null
          this.loading = false
          this.error = null
          return null
        }

        return runWithState(this, async () => {
          const result = await apiClient.search({
            kbId: normalizedKbId,
            query: normalizedQuery,
            topK: normalizedTopK,
          })
          this.result = result
          return result
        })
      },
    },
  })
}

export const useDebugStore = createDebugStoreDefinition()

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

function normalizeText(value) {
  return String(value ?? '').trim()
}
