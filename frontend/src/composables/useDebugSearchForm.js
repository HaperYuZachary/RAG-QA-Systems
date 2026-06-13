import { computed, shallowRef, toValue } from 'vue'

export const DEBUG_TOP_K_MIN = 1
export const DEBUG_TOP_K_MAX = 50
export const DEFAULT_DEBUG_TOP_K = 10

export function useDebugSearchForm({
  activeKbId,
  loading,
  notifyError = () => {},
  notifyWarning = () => {},
  search,
} = {}) {
  const query = shallowRef('')
  const topK = shallowRef(DEFAULT_DEBUG_TOP_K)

  const normalizedQuery = computed(() => normalizeText(query.value))
  const normalizedActiveKbId = computed(() => normalizeText(toValue(activeKbId)))
  const hasActiveKnowledgeBase = computed(() => Boolean(normalizedActiveKbId.value))
  const canSearch = computed(
    () =>
      hasActiveKnowledgeBase.value &&
      Boolean(normalizedQuery.value) &&
      !Boolean(toValue(loading)),
  )

  async function handleSearch() {
    if (!hasActiveKnowledgeBase.value) {
      notifyWarning('请先在知识库页选择或创建一个知识库')
      return null
    }

    if (!normalizedQuery.value || toValue(loading)) {
      return null
    }

    try {
      return await search({
        kbId: normalizedActiveKbId.value,
        query: normalizedQuery.value,
        topK: normalizeTopK(topK.value),
      })
    } catch (error) {
      notifyError(formatError(error))
      throw error
    }
  }

  return {
    canSearch,
    handleSearch,
    hasActiveKnowledgeBase,
    query,
    topK,
  }
}

export function normalizeTopK(value) {
  const numericValue = Number(value)

  if (!Number.isFinite(numericValue)) {
    return DEFAULT_DEBUG_TOP_K
  }

  return Math.min(
    DEBUG_TOP_K_MAX,
    Math.max(DEBUG_TOP_K_MIN, Math.round(numericValue)),
  )
}

function normalizeText(value) {
  return String(value ?? '').trim()
}

function formatError(value) {
  if (!value) {
    return '检索失败，请稍后重试'
  }

  if (value.response?.data?.detail) {
    return value.response.data.detail
  }

  if (value.data?.detail) {
    return value.data.detail
  }

  return value.message ?? '检索失败，请稍后重试'
}
