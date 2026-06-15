<script setup>
import { computed } from 'vue'
import { Check, Delete, Edit } from '@element-plus/icons-vue'

const props = defineProps({
  active: {
    type: Boolean,
    default: false,
  },
  item: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['edit', 'remove', 'select'])

const createdAtLabel = computed(() => formatDate(props.item.created_at))
const description = computed(() => props.item.description || '暂无描述')

function formatDate(value) {
  if (!value) {
    return '未知'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}
</script>

<template>
  <article class="kb-card" :class="{ 'kb-card--active': active }">
    <div class="kb-card__header">
      <div>
        <h3>{{ item.name }}</h3>
        <p>{{ description }}</p>
      </div>

      <el-tag v-if="active" type="success" effect="light">当前</el-tag>
    </div>

    <dl class="kb-card__meta">
      <div>
        <dt>文档数</dt>
        <dd>{{ item.document_count ?? 0 }}</dd>
      </div>
      <div>
        <dt>创建时间</dt>
        <dd>{{ createdAtLabel }}</dd>
      </div>
    </dl>

    <div class="kb-card__actions">
      <el-button
        :icon="Check"
        :type="active ? 'success' : 'primary'"
        :plain="!active"
        :disabled="active"
        @click="emit('select')"
      >
        {{ active ? '已选中' : '选为当前' }}
      </el-button>
      <el-button :icon="Edit" plain @click="emit('edit')">编辑</el-button>
      <el-popconfirm
        title="删除后相关文档和对话也会被清理，确认删除？"
        confirm-button-text="删除"
        cancel-button-text="取消"
        confirm-button-type="danger"
        width="260"
        @confirm="emit('remove')"
      >
        <template #reference>
          <el-button :icon="Delete" type="danger" plain>删除</el-button>
        </template>
      </el-popconfirm>
    </div>
  </article>
</template>

<style scoped>
.kb-card {
  display: flex;
  min-height: 220px;
  flex-direction: column;
  justify-content: space-between;
  gap: 20px;
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--panel-shadow);
  transition:
    border-color 0.18s ease,
    background-color 0.18s ease;
}

.kb-card:hover {
  border-color: var(--border-strong);
  background: #fbfcfd;
}

.kb-card--active {
  border-color: var(--primary-border);
  background: var(--surface);
  box-shadow: inset 3px 0 0 var(--primary);
}

.kb-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.kb-card h3 {
  margin: 0;
  color: var(--text);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0;
  overflow-wrap: anywhere;
}

.kb-card p {
  display: -webkit-box;
  min-height: 44px;
  margin: 8px 0 0;
  overflow: hidden;
  color: var(--muted);
  font-size: 14px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.kb-card__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
}

.kb-card__meta div {
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface-muted);
}

.kb-card__meta dt,
.kb-card__meta dd {
  margin: 0;
}

.kb-card__meta dt {
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

.kb-card__meta dd {
  margin-top: 4px;
  color: var(--text);
  font-size: 15px;
  font-weight: 700;
}

.kb-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
