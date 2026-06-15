<script setup>
import {
  sourceDocumentLabel,
  sourcePageLabel,
  sourceSnippet,
} from '../../utils/markdown.js'

defineProps({
  source: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['close'])
</script>

<template>
  <aside class="citation-popover">
    <div class="citation-popover__header">
      <div>
        <strong>{{ sourceDocumentLabel(source) }}</strong>
        <span v-if="sourcePageLabel(source)">
          {{ sourcePageLabel(source) }}
        </span>
      </div>
      <el-button text size="small" @click="emit('close')">
        关闭
      </el-button>
    </div>

    <p>{{ sourceSnippet(source) }}</p>
  </aside>
</template>

<style scoped>
.citation-popover {
  width: min(460px, 100%);
  margin-top: 10px;
  padding: 12px 14px;
  border: 1px solid var(--primary-border);
  border-radius: var(--radius-md);
  background: var(--primary-soft);
  box-shadow: var(--panel-shadow);
}

.citation-popover__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.citation-popover strong,
.citation-popover span {
  display: block;
  letter-spacing: 0;
}

.citation-popover strong {
  color: var(--text);
  font-size: 14px;
}

.citation-popover span {
  margin-top: 2px;
  color: var(--primary);
  font-size: 12px;
  font-weight: 600;
}

.citation-popover p {
  display: -webkit-box;
  margin: 8px 0 0;
  overflow: hidden;
  color: var(--text-soft);
  font-size: 13px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 5;
  white-space: pre-wrap;
}
</style>
