<script setup>
import { computed } from 'vue'
import { Promotion, VideoPause } from '@element-plus/icons-vue'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
  placeholder: {
    type: String,
    default: '输入问题，按 Enter 发送',
  },
  streaming: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['submit', 'stop'])
const draft = defineModel({
  type: String,
  default: '',
})

const trimmedDraft = computed(() => draft.value.trim())
const canSubmit = computed(
  () => !props.disabled && !props.streaming && trimmedDraft.value.length > 0,
)

function submit() {
  if (!canSubmit.value) {
    return
  }

  emit('submit', trimmedDraft.value)
}
</script>

<template>
  <section class="chat-composer">
    <el-input
      v-model="draft"
      class="chat-composer__input"
      type="textarea"
      :autosize="{ minRows: 2, maxRows: 6 }"
      :disabled="disabled || streaming"
      :placeholder="placeholder"
      resize="none"
      @keydown.enter.exact.prevent="submit"
    />

    <div class="chat-composer__footer">
      <span v-if="disabled">请先在知识库页选择或创建一个知识库</span>
      <span v-else-if="streaming">正在生成回答</span>
      <span v-else>Enter 发送，Shift+Enter 换行</span>

      <el-button
        v-if="streaming"
        :icon="VideoPause"
        type="danger"
        plain
        @click="emit('stop')"
      >
        停止生成
      </el-button>
      <el-button
        v-else
        :icon="Promotion"
        :disabled="!canSubmit"
        type="primary"
        @click="submit"
      >
        发送
      </el-button>
    </div>
  </section>
</template>

<style scoped>
.chat-composer {
  padding: 16px;
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: 0 -10px 26px rgba(15, 23, 42, 0.05);
}

.chat-composer__input :deep(.el-textarea__inner) {
  border-radius: 8px;
  color: #111827;
  line-height: 1.6;
}

.chat-composer__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
}

.chat-composer__footer span {
  color: #64748b;
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 700px) {
  .chat-composer__footer {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
