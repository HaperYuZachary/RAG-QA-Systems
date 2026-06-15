<script setup>
import { computed, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import { Close, Upload, UploadFilled } from '@element-plus/icons-vue'
import {
  ALLOWED_UPLOAD_EXTENSIONS,
  MAX_UPLOAD_FILE_SIZE,
  validateUploadFile,
} from '../../utils/uploadValidation.js'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
  uploading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['upload'])

const fileList = shallowRef([])

const selectedFiles = computed(() =>
  fileList.value
    .map((file) => file.raw)
    .filter(Boolean),
)
const selectedCount = computed(() => selectedFiles.value.length)
const accept = computed(() => ALLOWED_UPLOAD_EXTENSIONS.join(','))
const disabledReason = computed(() =>
  props.disabled ? '请先在知识库页选择或创建一个知识库' : '',
)

function handleChange(uploadFile, uploadFiles) {
  const validation = validateUploadFile(uploadFile.raw ?? uploadFile)

  if (!validation.valid) {
    ElMessage.warning(`${uploadFile.name}: ${validation.reason}`)
    fileList.value = uploadFiles.filter((file) => file.uid !== uploadFile.uid)
    return
  }

  fileList.value = uploadFiles
}

function handleRemove(_uploadFile, uploadFiles) {
  fileList.value = uploadFiles
}

function clearFiles() {
  fileList.value = []
}

function startUpload() {
  if (props.disabled) {
    ElMessage.warning(disabledReason.value)
    return
  }

  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请选择要上传的文件')
    return
  }

  emit('upload', selectedFiles.value)
}
</script>

<template>
  <section class="file-uploader" :class="{ 'file-uploader--disabled': disabled }">
    <el-upload
      v-model:file-list="fileList"
      class="file-uploader__dropzone"
      drag
      multiple
      action="#"
      :accept="accept"
      :auto-upload="false"
      :disabled="disabled || uploading"
      :on-change="handleChange"
      :on-remove="handleRemove"
    >
      <el-icon class="file-uploader__icon">
        <UploadFilled />
      </el-icon>
      <div class="file-uploader__text">
        <strong>拖拽文件到这里</strong>
        <span>或点击选择文件</span>
      </div>
      <template #tip>
        <div class="file-uploader__tip">
          支持 .pdf / .docx / .md，单文件不超过
          {{ Math.floor(MAX_UPLOAD_FILE_SIZE / 1024 / 1024) }}MB
        </div>
      </template>
    </el-upload>

    <div v-if="disabledReason" class="file-uploader__guard">
      {{ disabledReason }}
    </div>

    <div class="file-uploader__footer">
      <span>{{ selectedCount }} 个文件待上传</span>
      <div class="file-uploader__actions">
        <el-button
          :icon="Close"
          :disabled="selectedCount === 0 || uploading"
          plain
          @click="clearFiles"
        >
          清空
        </el-button>
        <el-button
          :icon="Upload"
          :disabled="disabled || selectedCount === 0"
          :loading="uploading"
          type="primary"
          @click="startUpload"
        >
          开始上传
        </el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.file-uploader {
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--panel-shadow);
}

.file-uploader--disabled {
  background: var(--surface-muted);
}

.file-uploader__dropzone {
  width: 100%;
}

.file-uploader__dropzone :deep(.el-upload) {
  width: 100%;
}

.file-uploader__dropzone :deep(.el-upload-dragger) {
  width: 100%;
  min-height: 188px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-md);
  background: var(--surface-muted);
}

.file-uploader__dropzone :deep(.el-upload-dragger:hover) {
  border-color: var(--primary-border);
  background: #f4fbf9;
}

.file-uploader__icon {
  color: var(--primary);
  font-size: 40px;
}

.file-uploader__text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: var(--muted);
}

.file-uploader__text strong {
  color: var(--text);
  font-size: 17px;
}

.file-uploader__tip {
  margin-top: 10px;
  color: var(--muted);
  font-size: 13px;
}

.file-uploader__guard {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--warning-soft);
  color: var(--warning-text);
  font-size: 14px;
  font-weight: 600;
}

.file-uploader__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 18px;
}

.file-uploader__footer span {
  color: var(--text-soft);
  font-size: 14px;
  font-weight: 600;
}

.file-uploader__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 700px) {
  .file-uploader__footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .file-uploader__actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
