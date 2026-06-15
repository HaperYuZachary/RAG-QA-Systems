import assert from 'node:assert/strict'
import test from 'node:test'
import { submitQuestionAndRefreshConversations } from './chatViewActions.js'

test('submitQuestionAndRefreshConversations refreshes conversations after a successful ask', async () => {
  const calls = []
  const chatStore = {
    async ask(payload) {
      calls.push(['ask', payload])
      chatStore.conversationId = 'conv_new'
    },
    async loadConversations(kbId) {
      calls.push(['loadConversations', kbId])
    },
    conversationId: '',
  }

  await submitQuestionAndRefreshConversations({
    chatStore,
    kbId: 'kb_1',
    question: '新会话问题',
  })

  assert.deepEqual(calls, [
    ['ask', { kbId: 'kb_1', question: '新会话问题' }],
    ['loadConversations', 'kb_1'],
  ])
  assert.equal(chatStore.conversationId, 'conv_new')
})

test('submitQuestionAndRefreshConversations does not refresh conversations when ask fails', async () => {
  const calls = []
  const error = new Error('stream failed')
  const chatStore = {
    async ask(payload) {
      calls.push(['ask', payload])
      throw error
    },
    async loadConversations(kbId) {
      calls.push(['loadConversations', kbId])
    },
  }

  await assert.rejects(
    submitQuestionAndRefreshConversations({
      chatStore,
      kbId: 'kb_1',
      question: '会失败吗？',
    }),
    /stream failed/,
  )

  assert.deepEqual(calls, [
    ['ask', { kbId: 'kb_1', question: '会失败吗？' }],
  ])
})
