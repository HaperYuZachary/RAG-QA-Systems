<script setup>
import { computed } from 'vue'
import { formatMs } from '../../utils/formatters.js'

const props = defineProps({
  timings: {
    type: Object,
    default: null,
  },
})

const stats = computed(() => [
  {
    key: 'embedding',
    label: 'Embedding',
    value: formatMs(props.timings?.embedding_ms),
  },
  {
    key: 'retrieval',
    label: 'Retrieval',
    value: formatMs(props.timings?.retrieval_ms),
  },
  {
    key: 'rerank',
    label: 'Rerank',
    value: formatMs(props.timings?.rerank_ms),
  },
  {
    key: 'total',
    label: 'Total',
    value: formatMs(props.timings?.total_ms),
  },
])
</script>

<template>
  <section class="debug-timing" aria-label="检索耗时">
    <article
      v-for="stat in stats"
      :key="stat.key"
      class="debug-timing__card"
    >
      <span>{{ stat.label }}</span>
      <strong>{{ stat.value }}</strong>
    </article>
  </section>
</template>

<style scoped>
.debug-timing {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.debug-timing__card {
  display: flex;
  min-height: 92px;
  flex-direction: column;
  justify-content: space-between;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--panel-shadow);
}

.debug-timing__card span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.debug-timing__card strong {
  color: var(--text);
  font-size: 22px;
  letter-spacing: 0;
  line-height: 1.1;
}

@media (max-width: 960px) {
  .debug-timing {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .debug-timing {
    grid-template-columns: 1fr;
  }
}
</style>
