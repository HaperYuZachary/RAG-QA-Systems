<script setup>
import { computed } from 'vue'
import {
  formatDocumentLocation,
  formatNullable,
  formatScore,
  truncateMiddle,
} from '../../utils/formatters.js'

const props = defineProps({
  hits: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  query: {
    type: String,
    default: '',
  },
})

const rows = computed(() =>
  props.hits.map((hit, index) => ({
    ...hit,
    chunkId: formatNullable(hit.id),
    chunkIdShort: truncateMiddle(hit.id, 18),
    documentLocation: formatDocumentLocation(hit.metadata ?? {}),
    rank: index + 1,
    textPreview: formatTextPreview(hit.text),
  })),
)

function formatTextPreview(value) {
  const text = formatNullable(value)

  if (text === '-') {
    return text
  }

  return text.replace(/\s+/g, ' ').trim()
}
</script>

<template>
  <section class="debug-results">
    <div class="debug-results__header">
      <div>
        <p class="debug-results__kicker">Fused Candidates</p>
        <h3>候选分数表</h3>
      </div>

      <div class="debug-results__summary">
        <span :title="query">Query: {{ query || '-' }}</span>
        <strong>{{ rows.length }} hits</strong>
      </div>
    </div>

    <el-table
      v-loading="loading"
      border
      class="debug-results__table"
      :data="rows"
      empty-text="暂无候选"
      row-key="id"
      stripe
    >
      <el-table-column type="expand" width="40">
        <template #default="{ row }">
          <div class="debug-results__expanded">
            <span>完整文本</span>
            <p>{{ formatNullable(row.text) }}</p>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="排名" width="58" align="center">
        <template #default="{ row }">
          <span class="debug-results__rank">#{{ row.rank }}</span>
        </template>
      </el-table-column>

      <el-table-column label="Chunk ID" width="126">
        <template #default="{ row }">
          <code class="debug-results__chunk" :title="row.chunkId">
            {{ row.chunkIdShort }}
          </code>
        </template>
      </el-table-column>

      <el-table-column label="文本" min-width="200">
        <template #default="{ row }">
          <p class="debug-results__text" :title="formatNullable(row.text)">
            {{ row.textPreview }}
          </p>
        </template>
      </el-table-column>

      <el-table-column label="向量 rank / 距离" width="108">
        <template #default="{ row }">
          <div class="debug-results__metric">
            <span>rank {{ formatNullable(row.vector_rank) }}</span>
            <strong>{{ formatScore(row.vector_distance, 'distance') }}</strong>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="BM25 rank / 分" width="108">
        <template #default="{ row }">
          <div class="debug-results__metric">
            <span>rank {{ formatNullable(row.bm25_rank) }}</span>
            <strong>{{ formatScore(row.bm25_score, 'bm25') }}</strong>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="RRF 分" width="82" align="right">
        <template #default="{ row }">
          <span class="debug-results__score debug-results__score--rrf">
            {{ formatScore(row.rrf_score, 'rrf') }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="Rerank 分" width="88" align="right">
        <template #default="{ row }">
          <span class="debug-results__score">
            {{ formatScore(row.rerank_score, 'rerank') }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="文档 / 页" min-width="116">
        <template #default="{ row }">
          <span
            class="debug-results__document"
            :title="row.documentLocation"
          >
            {{ row.documentLocation }}
          </span>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>

<style scoped>
.debug-results {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.debug-results__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.debug-results__kicker {
  margin: 0 0 6px;
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}

.debug-results h3 {
  margin: 0;
  color: var(--text);
  font-size: 18px;
  letter-spacing: 0;
}

.debug-results__summary {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 600;
}

.debug-results__summary span {
  overflow: hidden;
  max-width: 360px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.debug-results__summary strong {
  flex: 0 0 auto;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: var(--primary-soft);
  color: var(--primary-strong);
}

.debug-results__table {
  width: 100%;
}

.debug-results__table :deep(.el-table__cell) {
  vertical-align: top;
}

.debug-results__table :deep(.cell) {
  padding: 0 8px;
}

.debug-results__expanded {
  padding: 14px 18px;
  border-left: 3px solid var(--primary);
  background: var(--surface-muted);
}

.debug-results__expanded span {
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
}

.debug-results__expanded p {
  margin: 8px 0 0;
  color: var(--text);
  line-height: 1.7;
  white-space: pre-wrap;
}

.debug-results__rank {
  color: var(--primary);
  font-weight: 700;
}

.debug-results__chunk,
.debug-results__score,
.debug-results__metric strong {
  font-family:
    "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
}

.debug-results__chunk {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--surface-subtle);
  color: var(--text-soft);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.debug-results__text {
  display: -webkit-box;
  overflow: hidden;
  margin: 0;
  color: var(--text);
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.debug-results__metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}

.debug-results__metric span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

.debug-results__metric strong {
  color: var(--text);
  font-size: 13px;
}

.debug-results__score {
  display: inline-block;
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
}

.debug-results__score--rrf {
  color: var(--primary);
}

.debug-results__document {
  display: block;
  overflow: hidden;
  color: var(--text-soft);
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .debug-results__header {
    flex-direction: column;
  }

  .debug-results__summary {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
