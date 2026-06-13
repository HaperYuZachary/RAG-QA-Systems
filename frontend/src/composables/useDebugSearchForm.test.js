import assert from 'node:assert/strict'
import { test } from 'node:test'
import { shallowRef } from 'vue'
import {
  DEBUG_TOP_K_MAX,
  DEBUG_TOP_K_MIN,
  useDebugSearchForm,
} from './useDebugSearchForm.js'

function createForm(options = {}) {
  const activeKbId = shallowRef(options.activeKbId ?? 'kb_1')
  const calls = []
  const warnings = []
  const errors = []
  const loading = shallowRef(false)
  const search =
    options.search ??
    (async (payload) => {
      calls.push(payload)
      return { query: payload.query, hits: [], timings: {} }
    })

  const form = useDebugSearchForm({
    activeKbId,
    loading,
    search,
    notifyWarning(message) {
      warnings.push(message)
    },
    notifyError(message) {
      errors.push(message)
    },
  })

  return {
    activeKbId,
    calls,
    errors,
    form,
    loading,
    warnings,
  }
}

test('handleSearch trims the query and passes topK to search', async () => {
  const { calls, form } = createForm()
  form.query.value = ' 年假 '
  form.topK.value = 7

  await form.handleSearch()

  assert.deepEqual(calls, [
    {
      kbId: 'kb_1',
      query: '年假',
      topK: 7,
    },
  ])
})

test('handleSearch blocks missing active knowledge base and does not call search', async () => {
  const { calls, form, warnings } = createForm({ activeKbId: '' })
  form.query.value = '年假'

  const result = await form.handleSearch()

  assert.equal(result, null)
  assert.deepEqual(calls, [])
  assert.equal(form.canSearch.value, false)
  assert.deepEqual(warnings, ['请先在知识库页选择或创建一个知识库'])
})

test('handleSearch clamps topK to the backend schema range before search', async () => {
  const { calls, form } = createForm()
  form.query.value = '年假'

  form.topK.value = 0
  await form.handleSearch()

  form.topK.value = 99
  await form.handleSearch()

  assert.equal(calls[0].topK, DEBUG_TOP_K_MIN)
  assert.equal(calls[1].topK, DEBUG_TOP_K_MAX)
})

test('canSearch is false while loading or when the query is blank', () => {
  const { form, loading } = createForm()

  form.query.value = '   '
  assert.equal(form.canSearch.value, false)

  form.query.value = '年假'
  loading.value = true
  assert.equal(form.canSearch.value, false)
})
