<script setup>
import { computed } from 'vue'
import { ChatLineRound, Delete, Timer } from '@element-plus/icons-vue'
import { formatDate } from '../../utils/formatters.js'

const props = defineProps({
  conversations: {
    type: Array,
    default: () => [],
  },
  activeId: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['select', 'delete'])

const hasConversations = computed(() => props.conversations.length > 0)

function conversationTitle(conversation) {
  return conversation.title?.trim() || '未命名会话'
}

function messageCountLabel(conversation) {
  const count = Number(conversation.message_count ?? 0)
  return `${Number.isFinite(count) ? count : 0} 条消息`
}
</script>

<template>
  <aside class="conversation-list" aria-label="历史对话">
    <div class="conversation-list__header">
      <div>
        <p>History</p>
        <h3>历史对话</h3>
      </div>
      <el-tag size="small" effect="plain">
        {{ conversations.length }}
      </el-tag>
    </div>

    <div v-if="!hasConversations" class="conversation-list__empty">
      <el-icon>
        <ChatLineRound />
      </el-icon>
      <span>暂无历史对话</span>
    </div>

    <ol v-else class="conversation-list__items">
      <li
        v-for="conversation in conversations"
        :key="conversation.id"
        class="conversation-list__item"
        :class="{ 'is-active': conversation.id === activeId }"
      >
        <button
          class="conversation-list__select"
          type="button"
          @click="emit('select', conversation.id)"
        >
          <strong>{{ conversationTitle(conversation) }}</strong>
          <span>{{ messageCountLabel(conversation) }}</span>
          <small>
            <el-icon>
              <Timer />
            </el-icon>
            {{ formatDate(conversation.updated_at) }}
          </small>
        </button>

        <el-popconfirm
          title="删除这条历史对话？"
          confirm-button-text="删除"
          cancel-button-text="取消"
          width="190"
          @confirm="emit('delete', conversation.id)"
        >
          <template #reference>
            <el-tooltip content="删除会话" placement="right">
              <el-button
                class="conversation-list__delete"
                :icon="Delete"
                circle
                text
                type="danger"
                @click.stop
              />
            </el-tooltip>
          </template>
        </el-popconfirm>
      </li>
    </ol>
  </aside>
</template>

<style scoped>
.conversation-list {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(247, 249, 252, 0.92));
  box-shadow: var(--panel-shadow);
}

.conversation-list__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.conversation-list__header p {
  margin: 0 0 4px;
  color: var(--primary);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.conversation-list__header h3 {
  margin: 0;
  color: var(--text);
  font-size: 16px;
  font-weight: 750;
  letter-spacing: 0;
}

.conversation-list__empty {
  display: grid;
  min-height: 180px;
  place-items: center;
  align-content: center;
  gap: 8px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 650;
  text-align: center;
}

.conversation-list__empty .el-icon {
  color: var(--primary);
  font-size: 24px;
}

.conversation-list__items {
  display: grid;
  gap: 8px;
  min-height: 0;
  margin: 0;
  overflow-y: auto;
  padding: 0;
  list-style: none;
}

.conversation-list__item {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 32px;
  align-items: center;
  gap: 4px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.76);
  transition: border-color 0.18s ease, background-color 0.18s ease,
    box-shadow 0.18s ease;
}

.conversation-list__item:hover {
  border-color: var(--border-strong);
  background: var(--surface);
}

.conversation-list__item.is-active {
  border-color: var(--primary-border);
  background: var(--primary-soft);
  box-shadow: 0 10px 24px -18px rgba(13, 148, 136, 0.55);
}

.conversation-list__select {
  display: grid;
  min-width: 0;
  gap: 4px;
  padding: 11px 4px 11px 12px;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.conversation-list__select strong,
.conversation-list__select span,
.conversation-list__select small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-list__select strong {
  color: var(--text);
  font-size: 13px;
  font-weight: 750;
}

.conversation-list__select span {
  color: var(--text-soft);
  font-size: 12px;
}

.conversation-list__select small {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--muted);
  font-size: 11px;
}

.conversation-list__delete {
  width: 28px;
  height: 28px;
  opacity: 0.72;
}

.conversation-list__item:hover .conversation-list__delete,
.conversation-list__item.is-active .conversation-list__delete {
  opacity: 1;
}

@media (max-width: 760px) {
  .conversation-list {
    max-height: 280px;
  }

  .conversation-list__empty {
    min-height: 110px;
  }
}
</style>
