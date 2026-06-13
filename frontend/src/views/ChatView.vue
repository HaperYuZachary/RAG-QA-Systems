<script setup>
import { computed, nextTick, onMounted, shallowRef, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { Refresh, RefreshRight } from '@element-plus/icons-vue'
import ChatComposer from '../components/chat/ChatComposer.vue'
import ChatMessageList from '../components/chat/ChatMessageList.vue'
import { useChatStore } from '../stores/chat.js'
import { useKbStore } from '../stores/kb.js'

const kbStore = useKbStore()
const chatStore = useChatStore()

const { activeKb, activeKbId, items: knowledgeBases } = storeToRefs(kbStore)
const { error, messages, streaming } = storeToRefs(chatStore)

const draft = shallowRef('')
const kbLoadError = shallowRef('')
const messagesScroller = shallowRef(null)

const hasActiveKnowledgeBase = computed(() => Boolean(activeKbId.value))
const activeKnowledgeBaseLabel = computed(
  () => activeKb.value?.name ?? activeKbId.value,
)
const composerPlaceholder = computed(() =>
  hasActiveKnowledgeBase.value
    ? '围绕当前知识库提问'
    : '请先选择或创建一个知识库',
)
const visibleError = computed(() => kbLoadError.value || formatError(error.value))
const lastFailed = computed(() => {
  const lastMessage = messages.value.at(-1)

  return lastMessage?.role === 'assistant' && lastMessage.status === 'error'
})
const lastUserQuestion = computed(() => {
  if (!lastFailed.value) {
    return ''
  }

  const previousMessage = messages.value.at(-2)

  return previousMessage?.role === 'user' ? previousMessage.content : ''
})
const canRetry = computed(
  () =>
    hasActiveKnowledgeBase.value &&
    !streaming.value &&
    lastFailed.value &&
    lastUserQuestion.value.length > 0,
)
const scrollSignature = computed(() => {
  const lastMessage = messages.value.at(-1)

  return [
    messages.value.length,
    lastMessage?.id ?? '',
    lastMessage?.content ?? '',
    lastMessage?.status ?? '',
  ].join('|')
})

onMounted(async () => {
  if (knowledgeBases.value.length > 0) {
    scrollToBottom()
    return
  }

  try {
    await kbStore.fetchAll()
  } catch (loadError) {
    kbLoadError.value = formatError(loadError)
  } finally {
    scrollToBottom()
  }
})

watch(scrollSignature, () => {
  scrollToBottom()
})

async function handleSubmit(question) {
  if (!hasActiveKnowledgeBase.value) {
    ElMessage.warning('请先在知识库页选择或创建一个知识库')
    return
  }

  const nextQuestion = question.trim()

  if (!nextQuestion || streaming.value) {
    return
  }

  draft.value = ''

  try {
    await chatStore.ask({
      kbId: activeKbId.value,
      question: nextQuestion,
    })
  } catch (askError) {
    ElMessage.error(formatError(askError))
  }
}

function handleStop() {
  if (!streaming.value) {
    return
  }

  chatStore.stop()
  ElMessage.info('已停止生成')
}

async function handleRetry() {
  if (!canRetry.value) {
    return
  }

  try {
    await chatStore.ask({
      kbId: activeKbId.value,
      question: lastUserQuestion.value,
    })
  } catch (retryError) {
    ElMessage.error(formatError(retryError))
  }
}

function startNewConversation() {
  chatStore.reset()
  draft.value = ''
  scrollToBottom()
}

async function scrollToBottom() {
  await nextTick()

  const element = messagesScroller.value

  if (!element) {
    return
  }

  element.scrollTop = element.scrollHeight
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

  return value.message ?? '问答请求失败，请稍后重试'
}
</script>

<template>
  <section class="chat-view">
    <div class="chat-view__header">
      <div>
        <p class="chat-view__kicker">Chat</p>
        <h2>知识库问答</h2>
      </div>

      <div class="chat-view__actions">
        <el-tag v-if="hasActiveKnowledgeBase" type="success" effect="light">
          {{ activeKnowledgeBaseLabel }}
        </el-tag>
        <el-tag v-else type="warning" effect="light">
          未选择知识库
        </el-tag>

        <el-button :icon="Refresh" plain @click="startNewConversation">
          新对话
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="!hasActiveKnowledgeBase"
      title="请先在知识库页选择或创建一个知识库"
      type="warning"
      show-icon
      :closable="false"
    />

    <el-alert
      v-if="visibleError"
      :title="visibleError"
      type="error"
      show-icon
      :closable="false"
    />

    <div ref="messagesScroller" class="chat-view__messages">
      <ChatMessageList :messages="messages" :streaming="streaming" />
    </div>

    <section v-if="lastFailed" class="chat-view__retry">
      <span>上一轮回答失败，可以重新发送同一个问题。</span>
      <el-button
        :icon="RefreshRight"
        :disabled="!canRetry"
        plain
        type="primary"
        @click="handleRetry"
      >
        重试
      </el-button>
    </section>

    <ChatComposer
      v-model="draft"
      :disabled="!hasActiveKnowledgeBase"
      :placeholder="composerPlaceholder"
      :streaming="streaming"
      @submit="handleSubmit"
      @stop="handleStop"
    />
  </section>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 152px);
  min-height: 560px;
  gap: 18px;
}

.chat-view__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.chat-view__kicker {
  margin: 0 0 6px;
  color: #0f766e;
  font-size: 13px;
  font-weight: 700;
}

.chat-view h2 {
  margin: 0;
  color: #111827;
  font-size: 24px;
  letter-spacing: 0;
}

.chat-view__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.chat-view__messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px;
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.68);
}

.chat-view__retry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: #eff6ff;
}

.chat-view__retry span {
  color: #1e3a8a;
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 900px) {
  .chat-view {
    height: auto;
    min-height: calc(100vh - 120px);
  }

  .chat-view__messages {
    min-height: 420px;
  }
}

@media (max-width: 700px) {
  .chat-view__header,
  .chat-view__actions,
  .chat-view__retry {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
