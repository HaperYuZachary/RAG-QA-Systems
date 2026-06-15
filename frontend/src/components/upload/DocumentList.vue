<script setup>
import { computed } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { formatDate, formatFileSize } from '../../utils/formatters.js'

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['remove'])

const hasItems = computed(() => props.items.length > 0)

function statusType(status) {
  if (status === 'ready') {
    return 'success'
  }

  if (status === 'processing') {
    return 'warning'
  }

  if (status === 'error') {
    return 'danger'
  }

  return 'info'
}

function fileTypeLabel(fileType) {
  return fileType ? fileType.toUpperCase() : '-'
}
</script>

<template>
  <section class="document-list">
    <div class="document-list__header">
      <div>
        <p class="document-list__kicker">Library Files</p>
        <h3>已有文档</h3>
      </div>
      <span>{{ items.length }} 个文档</span>
    </div>

    <el-table
      v-if="hasItems || loading"
      v-loading="loading"
      :data="items"
      row-key="id"
      border
      class="document-list__table"
    >
      <el-table-column label="文件名" min-width="340" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="document-list__filename">
            {{ row.filename }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="类型" width="110">
        <template #default="{ row }">
          <el-tag size="small" effect="light">
            {{ fileTypeLabel(row.file_type) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="大小" width="120">
        <template #default="{ row }">
          {{ formatFileSize(row.file_size) }}
        </template>
      </el-table-column>

      <el-table-column label="状态" width="130">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" effect="light">
            {{ row.status || '-' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="chunk_count" label="分块数" width="100" />

      <el-table-column label="创建时间" min-width="180">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-popconfirm
            title="确认删除这个文档？"
            confirm-button-text="删除"
            cancel-button-text="取消"
            confirm-button-type="danger"
            width="220"
            @confirm="emit('remove', row)"
          >
            <template #reference>
              <el-button :icon="Delete" type="danger" plain>
                删除
              </el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-empty
      v-else
      description="该知识库还没有文档，先上传一个"
      class="document-list__empty"
    />
  </section>
</template>

<style scoped>
.document-list {
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--panel-shadow);
}

.document-list__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.document-list__kicker {
  margin: 0 0 6px;
  color: var(--primary);
  font-size: 13px;
  font-weight: 700;
}

.document-list h3 {
  margin: 0;
  color: var(--text);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0;
}

.document-list__header span {
  color: var(--muted);
  font-size: 13px;
  font-weight: 600;
}

.document-list__table {
  width: 100%;
}

.document-list__filename {
  display: block;
  overflow: hidden;
  max-width: 100%;
  white-space: nowrap;
  text-overflow: ellipsis;
  word-break: keep-all;
}

.document-list__empty {
  min-height: 220px;
}

@media (max-width: 700px) {
  .document-list__header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
