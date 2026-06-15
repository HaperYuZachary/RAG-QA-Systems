import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse } from '@vue/compiler-sfc'

const source = readFileSync(new URL('./ChatView.vue', import.meta.url), 'utf8')
const { descriptor } = parse(source)
const script = descriptor.scriptSetup.content
const template = descriptor.template.content

test('ChatView wires the conversation list to chat store actions', () => {
  assert.match(script, /import ConversationList/)
  assert.match(script, /watch\(\s*activeKbId/)
  assert.match(script, /chatStore\.loadConversations\(activeKbId\.value\)/)
  assert.match(script, /chatStore\.loadConversation\(conversationId\)/)
  assert.match(script, /chatStore\.removeConversation\(conversationId\)/)

  assert.match(template, /<ConversationList/)
  assert.match(template, /:conversations="conversations"/)
  assert.match(template, /:active-id="conversationId"/)
  assert.match(template, /@select="handleSelectConversation"/)
  assert.match(template, /@delete="handleDeleteConversation"/)
})

test('ChatView refreshes the conversation list after a successful submit', () => {
  assert.match(script, /submitQuestionAndRefreshConversations/)
  assert.match(script, /question: nextQuestion/)
  assert.match(script, /kbId: activeKbId\.value/)
})
