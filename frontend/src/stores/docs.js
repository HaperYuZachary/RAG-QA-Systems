import { defineStore } from 'pinia'
import { docsApi, uploadApi } from '../api/index.js'

const defaultApiClient = {
  list: docsApi.list,
  remove: docsApi.remove,
  uploadDocuments: uploadApi.uploadDocuments,
}

export function createDocsStoreDefinition({
  id = 'docs',
  apiClient = defaultApiClient,
} = {}) {
  return defineStore(id, {
    state: () => ({
      items: [],
      loading: false,
      uploading: false,
      error: null,
    }),

    actions: {
      async fetchByKb(kbId) {
        if (!kbId) {
          this.items = []
          this.error = null
          return []
        }

        return runWithState(this, 'loading', async () => {
          const items = normalizeListResponse(await apiClient.list(kbId))
          this.items = items
          return items
        })
      },

      async upload({ kbId, files }) {
        return runWithState(this, 'uploading', async () => {
          const response = await apiClient.uploadDocuments({ kbId, files })
          await this.fetchByKb(kbId)
          return response
        })
      },

      async remove(docId) {
        return runWithState(this, 'loading', async () => {
          const existing = this.items.find((item) => item.id === docId)
          const deleted = await apiClient.remove(docId)
          const kbId = existing?.kb_id ?? deleted?.kb_id

          if (kbId) {
            await this.fetchByKb(kbId)
          } else {
            this.items = this.items.filter((item) => item.id !== docId)
          }

          return deleted
        })
      },
    },
  })
}

export const useDocsStore = createDocsStoreDefinition()

async function runWithState(store, flagName, action) {
  store[flagName] = true
  store.error = null

  try {
    return await action()
  } catch (error) {
    store.error = error
    throw error
  } finally {
    store[flagName] = false
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
