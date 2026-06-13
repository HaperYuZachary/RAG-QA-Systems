import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'
import DebugView from '../views/DebugView.vue'
import KnowledgeBaseView from '../views/KnowledgeBaseView.vue'
import UploadView from '../views/UploadView.vue'

const routes = [
  {
    path: '/',
    redirect: '/knowledge-bases',
  },
  {
    path: '/knowledge-bases',
    name: 'knowledge-bases',
    component: KnowledgeBaseView,
    meta: {
      title: '知识库管理',
      subtitle: '创建、选择和维护知识库的入口。',
    },
  },
  {
    path: '/upload',
    name: 'upload',
    component: UploadView,
    meta: {
      title: '文档上传',
      subtitle: '向当前知识库上传文档并查看处理状态。',
    },
  },
  {
    path: '/chat',
    name: 'chat',
    component: ChatView,
    meta: {
      title: '知识库问答',
      subtitle: '基于选中文档进行流式问答。',
    },
  },
  {
    path: '/debug',
    name: 'debug',
    component: DebugView,
    meta: {
      title: '检索调试台',
      subtitle: '观察召回、融合、重排和耗时指标。',
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
