<script setup>
import { computed } from 'vue'
import { ChatDotRound } from '@element-plus/icons-vue'
import ChatMessage from './ChatMessage.vue'

const props = defineProps({
  messages: {
    type: Array,
    default: () => [],
  },
  streaming: {
    type: Boolean,
    default: false,
  },
})

const hasMessages = computed(() => props.messages.length > 0)
</script>

<template>
  <div class="chat-message-list">
    <div v-if="!hasMessages" class="chat-message-list__empty">
      <el-icon>
        <ChatDotRound />
      </el-icon>
      <h3>问点什么吧</h3>
      <p>选中知识库后，可以直接围绕已上传文档提问。</p>
    </div>

    <ol v-else class="chat-message-list__items">
      <ChatMessage
        v-for="message in messages"
        :key="message.id"
        :message="message"
      />
    </ol>

    <div v-if="streaming && hasMessages" class="chat-message-list__streaming">
      正在接收回答...
    </div>
  </div>
</template>

<style scoped>
.chat-message-list {
  min-height: 100%;
}

.chat-message-list__empty {
  display: grid;
  min-height: 360px;
  place-items: center;
  align-content: center;
  gap: 10px;
  color: #64748b;
  text-align: center;
}

.chat-message-list__empty .el-icon {
  color: #0f766e;
  font-size: 42px;
}

.chat-message-list__empty h3,
.chat-message-list__empty p {
  margin: 0;
}

.chat-message-list__empty h3 {
  color: #111827;
  font-size: 20px;
  letter-spacing: 0;
}

.chat-message-list__empty p {
  max-width: 360px;
  font-size: 14px;
}

.chat-message-list__items {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.chat-message-list__streaming {
  margin-top: 16px;
  color: #0f766e;
  font-size: 13px;
  font-weight: 700;
}

</style>
