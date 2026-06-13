<script setup>
import { computed, nextTick, reactive, shallowRef, watch } from 'vue'

const visible = defineModel({
  type: Boolean,
  default: false,
})

const props = defineProps({
  initialValue: {
    type: Object,
    default: null,
  },
  mode: {
    type: String,
    default: 'create',
    validator(value) {
      return ['create', 'edit'].includes(value)
    },
  },
  submitting: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['submit'])

const formRef = shallowRef(null)
const form = reactive({
  name: '',
  description: '',
})

const title = computed(() =>
  props.mode === 'edit' ? '编辑知识库' : '新建知识库',
)
const submitText = computed(() =>
  props.mode === 'edit' ? '保存修改' : '创建',
)

const rules = {
  name: [
    {
      message: '请输入知识库名称',
      trigger: 'blur',
      validator(_rule, value, callback) {
        if (value?.trim()) {
          callback()
          return
        }

        callback(new Error('请输入知识库名称'))
      },
    },
  ],
}

watch(
  () => [visible.value, props.initialValue, props.mode],
  ([isVisible]) => {
    if (!isVisible) {
      return
    }

    resetForm()
  },
  { immediate: true },
)

function resetForm() {
  form.name = props.initialValue?.name ?? ''
  form.description = props.initialValue?.description ?? ''

  nextTick(() => {
    formRef.value?.clearValidate()
  })
}

async function handleSubmit() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  emit('submit', {
    name: form.name.trim(),
    description: form.description.trim(),
  })
}
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="520px"
    :close-on-click-modal="!submitting"
    :close-on-press-escape="!submitting"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="名称" prop="name">
        <el-input
          v-model="form.name"
          maxlength="40"
          show-word-limit
          placeholder="例如：HR 制度"
          :disabled="submitting"
        />
      </el-form-item>

      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          maxlength="200"
          show-word-limit
          :rows="4"
          placeholder="补充这个知识库包含的文档范围"
          :disabled="submitting"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button :disabled="submitting" @click="visible = false">
        取消
      </el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ submitText }}
      </el-button>
    </template>
  </el-dialog>
</template>
