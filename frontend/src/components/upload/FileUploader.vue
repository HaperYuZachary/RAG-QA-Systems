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
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.84);
}

.file-uploader--disabled {
  background: rgba(248, 250, 252, 0.72);
}

.file-uploader__dropzone {
  width: 100%;
}

.file-uploader__dropzone :deep(.el-upload) {
  width: 100%;
}

.file-uploader__dropzone :deep(.el-upload-dragger) {
  width: 100%;
  min-height: 220px;
  border-radius: 8px;
}

.file-uploader__icon {
  color: #0f766e;
  font-size: 48px;
}

.file-uploader__text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #64748b;
}

.file-uploader__text strong {
  color: #111827;
  font-size: 18px;
}

.file-uploader__tip {
  margin-top: 10px;
  color: #64748b;
  font-size: 13px;
}

.file-uploader__guard {
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 14px;
  font-weight: 700;
}

.file-uploader__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 18px;
}

.file-uploader__footer span {
  color: #526070;
  font-size: 14px;
  font-weight: 700;
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
