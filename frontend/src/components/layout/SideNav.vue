<script setup>
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useRoute } from 'vue-router'
import { useKbStore } from '../../stores/kb.js'

const route = useRoute()
const kbStore = useKbStore()
const { activeKbId, items } = storeToRefs(kbStore)

const menuItems = [
  {
    path: '/knowledge-bases',
    label: '知识库',
  },
  {
    path: '/upload',
    label: '上传',
  },
  {
    path: '/chat',
    label: '问答',
  },
  {
    path: '/debug',
    label: '调试台',
  },
]

const activeRoute = computed(() => route.path)
const selectedKnowledgeBase = computed({
  get() {
    return activeKbId.value
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
        <p>RAG QA</p>
        <strong>知识库检索</strong>
      </div>
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
      text-color="#cbd5e1"
      active-text-color="#ffffff"
    >
      <el-menu-item
        v-for="item in menuItems"
        :key="item.path"
        :index="item.path"
      >
        <span>{{ item.label }}</span>
      </el-menu-item>
    </el-menu>
  </nav>
</template>

<style scoped>
.side-nav {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  padding: 24px 18px;
}

.side-nav__brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 8px 28px;
}

.side-nav__mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 8px;
  background: #14b8a6;
  color: #06231f;
  font-size: 22px;
  font-weight: 800;
}

.side-nav__brand p,
.side-nav__brand strong {
  display: block;
  margin: 0;
  letter-spacing: 0;
}

.side-nav__brand p {
  color: #9fb0c6;
  font-size: 12px;
  font-weight: 700;
}

.side-nav__brand strong {
  color: #f8fafc;
  font-size: 17px;
}

.side-nav__kb {
  padding: 14px 8px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.side-nav__kb label {
  display: block;
  margin-bottom: 8px;
  color: #9fb0c6;
  font-size: 13px;
  font-weight: 700;
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
  color: #94a3b8;
  font-size: 12px;
}

.side-nav__menu {
  flex: 1;
  margin-top: 18px;
  border-right: 0;
}

.side-nav__menu :deep(.el-menu-item) {
  height: 44px;
  margin: 4px 0;
  border-radius: 8px;
  font-weight: 700;
}

.side-nav__menu :deep(.el-menu-item.is-active) {
  background: rgba(20, 184, 166, 0.18);
}

@media (max-width: 900px) {
  .side-nav {
    min-height: auto;
    padding: 16px;
  }

  .side-nav__brand {
    padding-bottom: 16px;
  }
}
</style>
