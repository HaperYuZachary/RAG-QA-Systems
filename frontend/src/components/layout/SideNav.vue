<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import {
  ChatDotRound,
  Collection,
  Search,
  Upload,
} from '@element-plus/icons-vue'
import { useKbStore } from '../../stores/kb.js'

const route = useRoute()
const kbStore = useKbStore()
const { activeKbId, items } = storeToRefs(kbStore)

const menuItems = [
  {
    path: '/knowledge-bases',
    label: '知识库',
    icon: Collection,
  },
  {
    path: '/upload',
    label: '上传',
    icon: Upload,
  },
  {
    path: '/chat',
    label: '问答',
    icon: ChatDotRound,
  },
  {
    path: '/debug',
    label: '调试台',
    icon: Search,
  },
]

const activeRoute = computed(() => route.path)
const knowledgeBaseCount = computed(() => items.value.length)
const selectedKnowledgeBaseLabel = computed(() => {
  const selected = items.value.find((item) => item.id === activeKbId.value)

  return selected?.name ?? '未选择知识库'
})
const selectedKnowledgeBase = computed({
  get() {
    const hasSelected = items.value.some((item) => item.id === activeKbId.value)

    return hasSelected ? activeKbId.value : ''
  },
  set(value) {
    kbStore.setActive(value)
  },
})
</script>

<template>
  <nav class="side-nav" aria-label="主导航">
    <div class="side-nav__brand">
      <span class="side-nav__mark">R</span>
      <div>
        <p>RAG Workspace</p>
        <strong>知识库检索</strong>
      </div>
    </div>

    <div class="side-nav__status">
      <span>当前空间</span>
      <strong>{{ selectedKnowledgeBaseLabel }}</strong>
      <small>{{ knowledgeBaseCount }} 个知识库</small>
    </div>

    <div class="side-nav__kb">
      <label for="kb-selector">当前知识库</label>
      <el-select
        id="kb-selector"
        v-model="selectedKnowledgeBase"
        class="side-nav__select"
        :disabled="items.length === 0"
        placeholder="请选择知识库"
        size="large"
      >
        <el-option
          v-for="item in items"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        >
          <span class="side-nav__option-name">{{ item.name }}</span>
          <span class="side-nav__option-count">
            {{ item.document_count ?? 0 }} 文档
          </span>
        </el-option>
      </el-select>
    </div>

    <el-menu
      :default-active="activeRoute"
      router
      class="side-nav__menu"
      background-color="transparent"
      text-color="#475467"
      active-text-color="#0f766e"
    >
      <el-menu-item
        v-for="item in menuItems"
        :key="item.path"
        :index="item.path"
      >
        <el-icon>
          <component :is="item.icon" />
        </el-icon>
        <span>{{ item.label }}</span>
      </el-menu-item>
    </el-menu>
  </nav>
</template>

<style scoped>
.side-nav {
  display: flex;
  height: 100%;
  min-height: 100dvh;
  flex-direction: column;
  padding: 24px 18px;
  color: var(--text);
}

.side-nav__brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 8px 18px;
}

.side-nav__mark {
  display: grid;
  width: 46px;
  height: 46px;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.82);
  border-radius: 14px;
  background:
    linear-gradient(135deg, rgba(20, 184, 166, 0.92), rgba(34, 211, 238, 0.78));
  color: #053b36;
  font-size: 22px;
  font-weight: 800;
  box-shadow:
    0 16px 28px -18px rgba(13, 148, 136, 0.72),
    inset 0 1px 0 rgba(255, 255, 255, 0.62);
}

.side-nav__brand p,
.side-nav__brand strong {
  display: block;
  margin: 0;
  letter-spacing: 0;
}

.side-nav__brand p {
  color: #6b7b8b;
  font-size: 12px;
  font-weight: 750;
}

.side-nav__brand strong {
  color: var(--text);
  font-size: 18px;
  font-weight: 800;
}

.side-nav__status {
  display: grid;
  gap: 4px;
  margin: 0 4px 16px;
  padding: 14px;
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.58));
  box-shadow:
    0 18px 36px -28px rgba(15, 23, 42, 0.38),
    inset 0 1px 0 rgba(255, 255, 255, 0.78);
  backdrop-filter: saturate(160%) blur(16px);
  -webkit-backdrop-filter: saturate(160%) blur(16px);
}

.side-nav__status span,
.side-nav__status small {
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

.side-nav__status strong {
  overflow: hidden;
  color: var(--text);
  font-size: 14px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.side-nav__kb {
  padding: 16px 4px 18px;
  border-top: 1px solid rgba(148, 163, 184, 0.26);
  border-bottom: 1px solid rgba(148, 163, 184, 0.26);
}

.side-nav__kb label {
  display: block;
  margin-bottom: 8px;
  color: #64748b;
  font-size: 13px;
  font-weight: 750;
}

.side-nav__select {
  width: 100%;
}

.side-nav__option-name {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.side-nav__option-count {
  float: right;
  color: var(--muted);
  font-size: 12px;
}

.side-nav__menu {
  flex: 1;
  margin-top: 16px;
  border-right: 0;
}

.side-nav__menu :deep(.el-menu-item) {
  height: 44px;
  margin: 5px 0;
  border-radius: 15px;
  color: #526174;
  font-weight: 720;
  gap: 8px;
  transition: background-color 0.18s ease, box-shadow 0.18s ease,
    color 0.18s ease, transform 0.18s ease;
}

.side-nav__menu :deep(.el-menu-item .el-icon) {
  width: 18px;
  margin-right: 0;
  color: var(--subtle);
}

.side-nav__menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.56);
  color: var(--text);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.58);
}

.side-nav__menu :deep(.el-menu-item.is-active) {
  background:
    linear-gradient(135deg, rgba(225, 248, 244, 0.96), rgba(235, 251, 253, 0.86));
  color: var(--primary-strong);
  box-shadow:
    0 14px 28px -22px rgba(13, 148, 136, 0.62),
    inset 0 0 0 1px rgba(168, 221, 214, 0.76);
}

.side-nav__menu :deep(.el-menu-item.is-active .el-icon) {
  color: var(--primary);
}

@media (max-width: 900px) {
  .side-nav {
    min-height: auto;
    padding: 16px;
  }

  .side-nav__brand {
    padding-bottom: 16px;
  }

  .side-nav__menu {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 4px;
    flex: none;
    overflow: visible;
  }

  .side-nav__menu :deep(.el-menu-item) {
    min-width: 0;
    height: 40px;
    justify-content: center;
    margin: 0;
    padding: 0 4px;
    font-size: 14px;
  }
}
</style>
