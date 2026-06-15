import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse } from '@vue/compiler-sfc'

const source = readFileSync(
  new URL('./ConversationList.vue', import.meta.url),
  'utf8',
)
const { descriptor } = parse(source)

test('ConversationList declares the expected display props and events', () => {
  assert.match(descriptor.scriptSetup.content, /defineProps\(/)
  assert.match(descriptor.scriptSetup.content, /conversations/)
  assert.match(descriptor.scriptSetup.content, /activeId/)
  assert.match(descriptor.scriptSetup.content, /defineEmits\(\['select', 'delete'\]\)/)
})

test('ConversationList renders selectable rows with delete confirmation', () => {
  assert.match(descriptor.scriptSetup.content, /未命名会话/)
  assert.match(descriptor.template.content, /conversationTitle\(conversation\)/)
  assert.match(descriptor.template.content, /@click="emit\('select', conversation\.id\)"/)
  assert.match(descriptor.template.content, /<el-popconfirm/)
  assert.match(descriptor.template.content, /@confirm="emit\('delete', conversation\.id\)"/)
})
