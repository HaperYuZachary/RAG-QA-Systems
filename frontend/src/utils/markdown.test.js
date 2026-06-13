import assert from 'node:assert/strict'
import test from 'node:test'
import createDOMPurify from 'dompurify'
import { JSDOM } from 'jsdom'
import {
  getCitationByIndex,
  renderAssistantMarkdown,
  sourceDocumentLabel,
  sourcePageLabel,
} from './markdown.js'

test('renders markdown through a sanitizer before returning html', () => {
  let sanitizerInput = ''

  const html = renderAssistantMarkdown(
    '**年假** <img src=x onerror=alert(1)> 参考 [2]',
    {
      sanitize(rawHtml) {
        sanitizerInput = rawHtml
        return rawHtml.replace(/<img[^>]*>/g, '')
      },
    },
  )

  assert.match(sanitizerInput, /<strong>年假<\/strong>/)
  assert.match(sanitizerInput, /onerror=alert\(1\)/)
  assert.doesNotMatch(html, /onerror/)
  assert.match(html, /data-citation-index="2"/)
  assert.match(html, /查看引用 2/)
})

test('sanitizes dangerous markdown html with DOMPurify', () => {
  const window = new JSDOM('').window
  const purifier = createDOMPurify(window)
  const html = renderAssistantMarkdown(
    '**安全** <img src=x onerror=alert(1)> <script>alert(2)</script> [1]',
    {
      sanitize(rawHtml, options) {
        return purifier.sanitize(rawHtml, options)
      },
    },
  )

  assert.match(html, /<strong>安全<\/strong>/)
  assert.match(html, /data-citation-index="1"/)
  assert.doesNotMatch(html, /onerror/)
  assert.doesNotMatch(html, /<script/)
})

test('uses DOMPurify by default when a browser window is available', () => {
  const previousWindow = globalThis.window
  globalThis.window = new JSDOM('').window

  try {
    const html = renderAssistantMarkdown(
      '<img src=x onerror=alert(1)> <script>alert(2)</script> [1]',
    )

    assert.match(html, /data-citation-index="1"/)
    assert.doesNotMatch(html, /onerror/)
    assert.doesNotMatch(html, /<script/)
  } finally {
    if (previousWindow === undefined) {
      delete globalThis.window
    } else {
      globalThis.window = previousWindow
    }
  }
})

test('handles incomplete streaming markdown without throwing', () => {
  const html = renderAssistantMarkdown('```js\nconst answer = [1', {
    sanitize(rawHtml) {
      return rawHtml
    },
  })

  assert.equal(typeof html, 'string')
  assert.ok(html.length > 0)
})

test('maps citation markers to sources by one-based index', () => {
  const sources = [
    { index: 1, id: 'chunk_1', text: '第一段' },
    { index: 2, id: 'chunk_2', text: '第二段' },
  ]

  assert.equal(getCitationByIndex(sources, 1).id, 'chunk_1')
  assert.equal(getCitationByIndex(sources, 2).id, 'chunk_2')
  assert.equal(getCitationByIndex(sources, 3), null)
})

test('formats source document and page labels from metadata', () => {
  const source = {
    metadata: {
      filename: 'handbook.pdf',
      page: 3,
    },
  }

  assert.equal(sourceDocumentLabel(source), 'handbook.pdf')
  assert.equal(sourcePageLabel(source), '第 3 页')
})
