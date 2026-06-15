<script setup>
import { computed, onMounted, shallowRef } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import KnowledgeBaseCard from '../components/knowledge-base/KnowledgeBaseCard.vue'
import KnowledgeBaseFormDialog from '../components/knowledge-base/KnowledgeBaseFormDialog.vue'
import { useKbStore } from '../stores/kb.js'

const kbStore = useKbStore()
const { activeKbId, error, items, loading } = storeToRefs(kbStore)

const dialogVisible = shallowRef(false)
const dialogMode = shallowRef('create')
const editingKnowledgeBase = shallowRef(null)
const submitting = shallowRef(false)

const errorMessage = computed(() => formatError(error.value))

onMounted(() => {
  refresh({ notify: false })
})

function openCreateDialog() {
  dialogMode.value = 'create'
  editingKnowledgeBase.value = null
  dialogVisible.value = true
}

function openEditDialog(item) {
  dialogMode.value = 'edit'
  editingKnowledgeBase.value = item
  dialogVisible.value = true
}

async function handleSubmit(payload) {
  submitting.value = true

  try {
    if (dialogMode.value === 'edit' && editingKnowledgeBase.value) {
      await kbStore.update(editingKnowledgeBase.value.id, payload)
      ElMessage.success('知识库已更新')
    } else {
      await kbStore.create(payload)
      ElMessage.success('知识库已创建')
    }

    dialogVisible.value = false
  } catch (submitError) {
    ElMessage.error(formatError(submitError))
  } finally {
    submitting.value = false
  }
}

async function refresh({ notify = true } = {}) {
  try {
    await kbStore.fetchAll()
  } catch (fetchError) {
    if (notify) {
      ElMessage.error(formatError(fetchError))
    }
  }
}

async function handleRemove(item) {
  try {
    await kbStore.remove(item.id)
    ElMessage.success('知识库已删除')
  } catch (removeError) {
    ElMessage.error(formatError(removeError))
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

  if (value.response?.status) {
    return `请求失败（${value.response.status}），请确认后端服务是否正常运行`
  }

  return value.message ?? '请求失败，请稍后重试'
}
</script>

<template>
  <section class="kb-page">
    <div class="kb-page__toolbar">
      <div>
        <p class="kb-page__kicker">Knowledge Bases</p>
        <h2>管理知识库</h2>
      </div>

      <div class="kb-page__actions">
        <el-button
          :icon="Refresh"
          :loading="loading"
          plain
          @click="refresh"
        >
          刷新
        </el-button>
        <el-button :icon="Plus" type="primary" @click="openCreateDialog">
          新建知识库
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="errorMessage"
      class="kb-page__alert"
      :title="errorMessage"
      type="error"
      show-icon
      :closable="false"
    />

    <div v-if="loading && items.length === 0" class="kb-page__grid">
      <el-skeleton v-for="index in 4" :key="index" animated>
        <template #template>
          <div class="kb-card kb-card--skeleton">
            <el-skeleton-item variant="h3" class="kb-card__skeleton-title" />
            <el-skeleton-item variant="text" />
            <el-skeleton-item variant="text" />
            <div class="kb-card__skeleton-footer">
              <el-skeleton-item variant="button" />
              <el-skeleton-item variant="button" />
            </div>
          </div>
        </template>
      </el-skeleton>
    </div>

    <el-empty
      v-else-if="items.length === 0"
      class="kb-page__empty"
      description="还没有知识库，先建一个"
    >
      <el-button :icon="Plus" type="primary" @click="openCreateDialog">
        新建知识库
      </el-button>
    </el-empty>

    <div v-else class="kb-page__grid">
      <KnowledgeBaseCard
        v-for="item in items"
        :key="item.id"
        :item="item"
        :active="item.id === activeKbId"
        @select="kbStore.setActive(item.id)"
        @edit="openEditDialog(item)"
        @remove="handleRemove(item)"
      />
    </div>

    <KnowledgeBaseFormDialog
      v-model="dialogVisible"
      :mode="dialogMode"
      :initial-value="editingKnowledgeBase"
      :submitting="submitting"
      @submit="handleSubmit"
    />
  </section>
</template>

<style scoped>
.kb-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.kb-page__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.kb-page__kicker {
  margin: 0 0 6px;
  color: var(--primary);
  font-size: 13px;
  font-weight: 700;
}

.kb-page h2 {
  margin: 0;
  color: var(--text);
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0;
}

.kb-page__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.kb-page__alert {
  border-radius: var(--radius-md);
}

.kb-page__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.kb-page__empty {
  min-height: 360px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--panel-shadow);
}

.kb-card--skeleton {
  min-height: 220px;
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--panel-shadow);
}

.kb-card__skeleton-title {
  width: 70%;
  margin-bottom: 18px;
}

.kb-card__skeleton-footer {
  display: flex;
  gap: 10px;
  margin-top: 34px;
}

@media (max-width: 700px) {
  .kb-page__toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .kb-page__actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
