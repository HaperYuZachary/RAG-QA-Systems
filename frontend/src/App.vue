<script setup>
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import SideNav from './components/layout/SideNav.vue'

const route = useRoute()

const pageTitle = computed(() => route.meta.title ?? '知识库检索')
const pageSubtitle = computed(() => route.meta.subtitle ?? '')
</script>

<template>
  <el-config-provider :locale="zhCn">
    <el-container class="app-shell">
      <el-aside class="app-sidebar" width="292px">
        <SideNav />
      </el-aside>

      <el-container class="app-main">
        <el-header class="app-header" height="104px">
          <div>
            <p class="app-kicker">知识检索工作台</p>
            <h1>{{ pageTitle }}</h1>
            <p v-if="pageSubtitle" class="app-subtitle">
              {{ pageSubtitle }}
            </p>
          </div>

          <el-tag class="app-phase" type="info" effect="plain" round>
            本地私有化 · RAG
          </el-tag>
        </el-header>

        <el-main class="app-content">
          <RouterView v-slot="{ Component }">
            <transition name="page" mode="out-in">
              <component :is="Component" />
            </transition>
          </RouterView>
        </el-main>
      </el-container>
    </el-container>
  </el-config-provider>
</template>
