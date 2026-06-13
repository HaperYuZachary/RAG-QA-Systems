<script setup>
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import SideNav from './components/layout/SideNav.vue'

const route = useRoute()

const pageTitle = computed(() => route.meta.title ?? 'RAG QA System')
const pageSubtitle = computed(() => route.meta.subtitle ?? '')
</script>

<template>
  <el-config-provider :locale="zhCn">
    <el-container class="app-shell">
      <el-aside class="app-sidebar" width="264px">
        <SideNav />
      </el-aside>

      <el-container class="app-main">
        <el-header class="app-header" height="96px">
          <div>
            <p class="app-kicker">RAG QA System</p>
            <h1>{{ pageTitle }}</h1>
            <p v-if="pageSubtitle" class="app-subtitle">
              {{ pageSubtitle }}
            </p>
          </div>

          <el-tag type="info" effect="plain" round>Phase 4-1</el-tag>
        </el-header>

        <el-main class="app-content">
          <RouterView />
        </el-main>
      </el-container>
    </el-container>
  </el-config-provider>
</template>
