<script setup>
import { computed, onMounted, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import DebugResultTable from '../components/debug/DebugResultTable.vue'
import DebugSearchPanel from '../components/debug/DebugSearchPanel.vue'
import DebugTimingStats from '../components/debug/DebugTimingStats.vue'
import { useDebugSearchForm } from '../composables/useDebugSearchForm.js'
import { useDebugStore } from '../stores/debug.js'
import { useKbStore } from '../stores/kb.js'

const kbStore = useKbStore()
const debugStore = useDebugStore()

const { activeKb, activeKbId, items: knowledgeBases } = storeToRefs(kbStore)
const { error, loading, result } = storeToRefs(debugStore)

const kbLoadError = shallowRef('')

const activeKnowledgeBaseLabel = computed(
  () => activeKb.value?.name ?? activeKbId.value,
)
const visibleError = computed(() => kbLoadError.value || formatError(error.value))

const {
  canSearch,
  handleSearch,
  hasActiveKnowledgeBase,
  query,
  topK,
} = useDebugSearchForm({
  activeKbId,
  loading,
  search(payload) {
    return debugStore.search(payload)
  },
  notifyError(message) {
    ElMessage.error(message)
  },
  notifyWarning(message) {
    ElMessage.warning(message)
  },
})

onMounted(async () => {
  if (knowledgeBases.value.length > 0) {
    return
  }

  try {
    await kbStore.fetchAll()
  } catch (loadError) {
    kbLoadError.value = formatError(loadError)
    ElMessage.error(kbLoadError.value)
  }
})

async function submitSearch() {
  try {
    await handleSearch()
  } catch {
    // The store and message toast already expose the failure.
  }
}

function formatError(value) {
  if (!value) {
    return ''
  }

  if (value.response?.data?.detail) {
    return value.response.data.detail
  }

  if (value.data?.detail) {
    return value.data.detail
  }

  return value.message ?? '检索失败，请稍后重试'
}
</script>

<template>
  <section class="debug-view">
    <DebugSearchPanel
      v-model:query="query"
      v-model:top-k="topK"
      :active-knowledge-base-label="activeKnowledgeBaseLabel"
      :can-search="canSearch"
      :disabled="!hasActiveKnowledgeBase"
      :loading="loading"
      @submit="submitSearch"
    />

    <el-alert
      v-if="!hasActiveKnowledgeBase"
      title="请先在知识库页选择或创建一个知识库"
      type="warning"
      show-icon
      :closable="false"
    />

    <el-alert
      v-if="visibleError"
      :title="visibleError"
      type="error"
      show-icon
      :closable="false"
    />

    <DebugTimingStats :timings="result?.timings" />

    <section class="debug-view__result-shell">
      <el-skeleton v-if="loading && !result" animated :rows="5" />

      <el-empty
        v-else-if="!result"
        description="输入问题查看检索过程"
      />

      <DebugResultTable
        v-else
        :hits="result.hits"
        :loading="loading"
        :query="result.query"
      />
    </section>
  </section>
</template>

<style scoped>
.debug-view {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.debug-view__result-shell {
  min-height: 260px;
  padding: 20px;
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.76);
}

.debug-view__result-shell :deep(.el-empty) {
  min-height: 220px;
}

</style>
