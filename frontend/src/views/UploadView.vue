<script setup>
import { computed, onMounted, shallowRef, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import DocumentList from '../components/upload/DocumentList.vue'
import FileUploader from '../components/upload/FileUploader.vue'
import { useDocsStore } from '../stores/docs.js'
import { useKbStore } from '../stores/kb.js'

const kbStore = useKbStore()
const docsStore = useDocsStore()
const { activeKb, activeKbId, items: knowledgeBases } = storeToRefs(kbStore)
const {
  items: docsItems,
  loading: docsLoading,
  uploading,
} = storeToRefs(docsStore)

const uploadResults = shallowRef([])
const uploadError = shallowRef('')

const hasActiveKnowledgeBase = computed(() => Boolean(activeKbId.value))
const activeKnowledgeBaseLabel = computed(
  () => activeKb.value?.name ?? activeKbId.value,
)

onMounted(async () => {
  const initialActiveKbId = activeKbId.value

  try {
    if (knowledgeBases.value.length === 0) {
      await kbStore.fetchAll()
    }

    if (activeKbId.value && activeKbId.value === initialActiveKbId) {
      await fetchDocumentsByKb(activeKbId.value)
    }
  } catch (error) {
    uploadError.value = formatError(error)
    ElMessage.error(uploadError.value)
  }
})

watch(activeKbId, async (newId) => {
  uploadError.value = ''
  uploadResults.value = []

  try {
    await fetchDocumentsByKb(newId)
  } catch (error) {
    uploadError.value = formatError(error)
    ElMessage.error(uploadError.value)
  }
})

async function handleUpload(files) {
  uploadError.value = ''

  if (!activeKbId.value) {
    uploadError.value = '请先在知识库页选择或创建一个知识库'
    ElMessage.warning(uploadError.value)
    return
  }

  if (files.length === 0) {
    uploadError.value = '请选择要上传的文件'
    ElMessage.warning(uploadError.value)
    return
  }

  try {
    const response = await docsStore.upload({
      kbId: activeKbId.value,
      files,
    })
    uploadResults.value = response?.documents ?? []
    ElMessage.success('上传完成')
  } catch (error) {
    uploadError.value = formatError(error)
    ElMessage.error(uploadError.value)
  }
}

async function handleRemove(doc) {
  uploadError.value = ''

  try {
    await docsStore.remove(doc.id)
    ElMessage.success('文档已删除')
  } catch (error) {
    uploadError.value = formatError(error)
    ElMessage.error(uploadError.value)
  }
}

function fetchDocumentsByKb(kbId) {
  return docsStore.fetchByKb(kbId)
}

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

function formatError(error) {
  if (!error) {
    return ''
  }

  if (error.response?.data?.detail) {
    return error.response.data.detail
  }

  if (error.data?.detail) {
    return error.data.detail
  }

  return error.message ?? '上传失败，请稍后重试'
}
</script>

<template>
  <section class="upload-page">
    <div class="upload-page__header">
      <div>
        <p class="upload-page__kicker">Documents</p>
        <h2>上传文档</h2>
      </div>

      <el-tag v-if="hasActiveKnowledgeBase" type="success" effect="light">
        {{ activeKnowledgeBaseLabel }}
      </el-tag>
      <el-tag v-else type="warning" effect="light">
        未选择知识库
      </el-tag>
    </div>

    <el-alert
      v-if="!hasActiveKnowledgeBase"
      title="请先在知识库页选择或创建一个知识库"
      type="warning"
      show-icon
      :closable="false"
    />

    <el-alert
      v-if="uploadError"
      :title="uploadError"
      type="error"
      show-icon
      :closable="false"
    />

    <FileUploader
      :disabled="!hasActiveKnowledgeBase"
      :uploading="uploading"
      @upload="handleUpload"
    />

    <section v-if="uploadResults.length > 0" class="upload-results">
      <div class="upload-results__header">
        <h3>上传结果</h3>
        <span>{{ uploadResults.length }} 个文件</span>
      </div>

      <el-table :data="uploadResults" border>
        <el-table-column label="文件名" min-width="340" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="upload-results__filename">
              {{ row.filename }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" effect="light">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chunk_count" label="分块数" width="100" />
        <el-table-column label="重复" width="90">
          <template #default="{ row }">
            {{ row.duplicate ? '是' : '否' }}
          </template>
        </el-table-column>
        <el-table-column prop="error_msg" label="错误信息" min-width="220">
          <template #default="{ row }">
            <span class="upload-results__error">
              {{ row.error_msg || '-' }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <DocumentList
      :items="docsItems"
      :loading="docsLoading"
      @remove="handleRemove"
    />
  </section>
</template>

<style scoped>
.upload-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.upload-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.upload-page__kicker {
  margin: 0 0 6px;
  color: #0f766e;
  font-size: 13px;
  font-weight: 700;
}

.upload-page h2,
.upload-results h3 {
  margin: 0;
  color: #111827;
  letter-spacing: 0;
}

.upload-page h2 {
  font-size: 24px;
}

.upload-results {
  padding: 20px;
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.84);
}

.upload-results__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.upload-results h3 {
  font-size: 18px;
}

.upload-results__header span {
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

.upload-results__error {
  color: #b42318;
}

.upload-results__filename {
  display: block;
  overflow: hidden;
  max-width: 100%;
  white-space: nowrap;
  text-overflow: ellipsis;
  word-break: keep-all;
}

@media (max-width: 700px) {
  .upload-page__header,
  .upload-results__header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
