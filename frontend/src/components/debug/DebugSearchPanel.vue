<script setup>
import { computed } from 'vue'
import { Search } from '@element-plus/icons-vue'

const query = defineModel('query', {
  type: String,
  default: '',
})
const topK = defineModel('topK', {
  type: Number,
  default: 10,
})

const props = defineProps({
  activeKnowledgeBaseLabel: {
    type: String,
    default: '',
  },
  canSearch: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['submit'])

const queryPlaceholder = computed(() =>
  props.disabled ? '请先选择知识库' : '输入要调试的检索问题',
)
</script>

<template>
  <section class="debug-search">
    <div class="debug-search__header">
      <div>
        <p class="debug-search__kicker">Retrieval Debug</p>
        <h2>检索调试台</h2>
      </div>

      <el-tag v-if="!disabled" type="success" effect="light">
        {{ activeKnowledgeBaseLabel }}
      </el-tag>
      <el-tag v-else type="warning" effect="light">
        未选择知识库
      </el-tag>
    </div>

    <form class="debug-search__form" @submit.prevent="emit('submit')">
      <el-input
        v-model="query"
        class="debug-search__query"
        clearable
        :disabled="disabled || loading"
        :placeholder="queryPlaceholder"
        size="large"
      />

      <label class="debug-search__topk">
        <span>Top K</span>
        <el-input-number
          v-model="topK"
          :disabled="disabled || loading"
          :max="50"
          :min="1"
          :step="1"
          controls-position="right"
          step-strictly
          size="large"
        />
      </label>

      <el-button
        native-type="submit"
        type="primary"
        size="large"
        :disabled="!canSearch"
        :icon="Search"
        :loading="loading"
      >
        检索
      </el-button>
    </form>
  </section>
</template>

<style scoped>
.debug-search {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--panel-shadow);
}

.debug-search__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.debug-search__kicker {
  margin: 0 0 6px;
  color: var(--primary);
  font-size: 13px;
  font-weight: 700;
}

.debug-search h2 {
  margin: 0;
  color: var(--text);
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0;
}

.debug-search__form {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto auto;
  align-items: end;
  gap: 12px;
}

.debug-search__query {
  min-width: 0;
}

.debug-search__topk {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text-soft);
  font-size: 13px;
  font-weight: 600;
}

.debug-search__topk :deep(.el-input-number) {
  width: 132px;
}

@media (max-width: 780px) {
  .debug-search__header,
  .debug-search__form {
    align-items: stretch;
    grid-template-columns: 1fr;
  }

  .debug-search__header {
    flex-direction: column;
  }

  .debug-search__topk :deep(.el-input-number) {
    width: 100%;
  }
}
</style>
