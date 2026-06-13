<script setup>
import { computed, shallowRef } from 'vue'
import CitationPopover from './CitationPopover.vue'
import {
  getCitationByIndex,
  renderAssistantMarkdown,
  sourceDocumentLabel,
  sourcePageLabel,
  sourceSnippet,
} from '../../utils/markdown.js'

const props = defineProps({
  message: {
    type: Object,
    required: true,
  },
})

const activeCitation = shallowRef(null)

const isAssistant = computed(() => props.message.role === 'assistant')
const renderedContent = computed(() =>
  isAssistant.value ? renderAssistantMarkdown(props.message.content) : '',
)
const hasSources = computed(
  () => isAssistant.value && props.message.sources?.length > 0,
)

function roleLabel(role) {
  return role === 'user' ? '你' : '助手'
}

function statusLabel(status) {
  if (status === 'error') {
    return '生成失败'
  }

  if (status === 'stopped') {
    return '已停止'
  }

  if (status === 'streaming') {
    return '生成中'
  }

  return ''
}

function handleRenderedClick(event) {
  const marker = event.target.closest?.('[data-citation-index]')

  if (!marker) {
    return
  }

  const source = getCitationByIndex(
    props.message.sources,
    marker.dataset.citationIndex,
  )

  if (source) {
    activeCitation.value = source
  }
}
</script>

<template>
  <li
    class="chat-message"
    :class="[
      `chat-message--${message.role}`,
      { 'chat-message--error': message.status === 'error' },
    ]"
  >
    <div class="chat-message__meta">
      <span>{{ roleLabel(message.role) }}</span>
      <el-tag
        v-if="statusLabel(message.status)"
        :type="message.status === 'error' ? 'danger' : 'info'"
        effect="light"
        size="small"
      >
        {{ statusLabel(message.status) }}
      </el-tag>
    </div>

    <div class="chat-message__bubble">
      <div
        v-if="isAssistant && message.content"
        class="chat-message__content chat-message__content--markdown"
        v-html="renderedContent"
        @click="handleRenderedClick"
      />
      <p v-else-if="message.content" class="chat-message__content">
        {{ message.content }}
      </p>
      <p v-else-if="message.status === 'streaming'" class="chat-message__typing">
        正在生成...
      </p>
      <p v-else class="chat-message__typing">
        暂无内容
      </p>
    </div>

    <CitationPopover
      v-if="activeCitation"
      :source="activeCitation"
      @close="activeCitation = null"
    />

    <div v-if="hasSources" class="chat-message__sources">
      <h4>来源</h4>
      <ul>
        <li v-for="(source, index) in message.sources" :key="source.id ?? index">
          <button type="button" @click="activeCitation = source">
            <strong>[{{ source.index ?? index + 1 }}] {{ sourceDocumentLabel(source) }}</strong>
            <span v-if="sourcePageLabel(source)">
              {{ sourcePageLabel(source) }}
            </span>
            <small>{{ sourceSnippet(source) }}</small>
          </button>
        </li>
      </ul>
    </div>
  </li>
</template>

<style scoped>
.chat-message {
  display: flex;
  max-width: min(760px, 88%);
  flex-direction: column;
  gap: 7px;
}

.chat-message--user {
  align-self: flex-end;
  align-items: flex-end;
}

.chat-message--assistant {
  align-self: flex-start;
  align-items: flex-start;
}

.chat-message__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.chat-message__bubble {
  padding: 13px 15px;
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.06);
}

.chat-message--user .chat-message__bubble {
  border-color: #0f766e;
  background: #0f766e;
  color: #f8fafc;
}

.chat-message--error .chat-message__bubble {
  border-color: #fecaca;
  background: #fff7f7;
  color: #991b1b;
}

.chat-message__content,
.chat-message__typing {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.chat-message__content--markdown {
  white-space: normal;
}

.chat-message__content--markdown :deep(p),
.chat-message__content--markdown :deep(ul),
.chat-message__content--markdown :deep(ol),
.chat-message__content--markdown :deep(pre),
.chat-message__content--markdown :deep(blockquote) {
  margin: 0 0 10px;
}

.chat-message__content--markdown :deep(p:last-child),
.chat-message__content--markdown :deep(ul:last-child),
.chat-message__content--markdown :deep(ol:last-child),
.chat-message__content--markdown :deep(pre:last-child),
.chat-message__content--markdown :deep(blockquote:last-child) {
  margin-bottom: 0;
}

.chat-message__content--markdown :deep(code) {
  border-radius: 6px;
  background: #eef2f7;
  color: #0f172a;
  font-family: ui-monospace, "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  font-size: 0.92em;
}

.chat-message__content--markdown :deep(pre) {
  overflow-x: auto;
  padding: 12px;
  border-radius: 8px;
  background: #0f172a;
  color: #e5edf6;
}

.chat-message__content--markdown :deep(pre code) {
  background: transparent;
  color: inherit;
}

.chat-message__content--markdown :deep(.citation-marker) {
  display: inline-flex;
  min-width: 24px;
  height: 22px;
  align-items: center;
  justify-content: center;
  margin: 0 2px;
  padding: 0 6px;
  border: 1px solid #99f6e4;
  border-radius: 999px;
  background: #ccfbf1;
  color: #0f766e;
  cursor: pointer;
  font-size: 12px;
  font-weight: 800;
}

.chat-message__content--markdown :deep(.citation-marker:hover) {
  background: #99f6e4;
}

.chat-message__typing {
  color: #64748b;
  font-style: italic;
}

.chat-message__sources {
  width: min(560px, 100%);
  margin-top: 4px;
}

.chat-message__sources h4 {
  margin: 0 0 8px;
  color: #64748b;
  font-size: 12px;
  letter-spacing: 0;
}

.chat-message__sources ul {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.chat-message__sources button {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #dbe4ef;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.78);
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.chat-message__sources button:hover {
  border-color: #99f6e4;
  background: #f0fdfa;
}

.chat-message__sources strong,
.chat-message__sources span,
.chat-message__sources small {
  display: block;
}

.chat-message__sources strong {
  color: #0f172a;
  font-size: 13px;
}

.chat-message__sources span {
  margin-top: 2px;
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
}

.chat-message__sources small {
  display: -webkit-box;
  margin-top: 6px;
  overflow: hidden;
  color: #64748b;
  font-size: 12px;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

@media (max-width: 700px) {
  .chat-message {
    max-width: 100%;
  }
}
</style>
