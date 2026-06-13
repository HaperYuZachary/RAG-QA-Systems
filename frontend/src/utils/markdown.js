import createDOMPurify from 'dompurify'
import { marked } from 'marked'

const CITATION_PATTERN = /\[(\d+)]/g
const SANITIZE_OPTIONS = {
  ADD_TAGS: ['button'],
  ADD_ATTR: ['aria-label', 'class', 'data-citation-index', 'type'],
  ALLOW_DATA_ATTR: true,
}

let purifier = null

export function renderAssistantMarkdown(content, options = {}) {
  const markdown = decorateCitations(String(content ?? ''))
  const unsafeHtml = marked.parse(markdown, {
    async: false,
    breaks: true,
    gfm: true,
  })

  return sanitizeHtml(unsafeHtml, options.sanitize)
}

export function getCitationByIndex(sources, citationIndex) {
  const numericIndex = Number(citationIndex)

  if (!Number.isInteger(numericIndex) || numericIndex < 1) {
    return null
  }

  const items = Array.isArray(sources) ? sources : []
  const arrayAligned = items[numericIndex - 1]

  if (arrayAligned) {
    return arrayAligned
  }

  return items.find((source) => Number(source?.index) === numericIndex) ?? null
}

export function sourceDocumentLabel(source) {
  const metadata = source?.metadata ?? {}

  return (
    source?.document_name ??
    source?.documentName ??
    metadata.filename ??
    metadata.document_name ??
    metadata.documentName ??
    metadata.document_id ??
    source?.id ??
    '未知文档'
  )
}

export function sourcePageLabel(source) {
  const metadata = source?.metadata ?? {}
  const page = source?.page ?? metadata.page

  if (page === undefined || page === null || page === '') {
    return ''
  }

  return `第 ${page} 页`
}

export function sourceSnippet(source) {
  return source?.text || '暂无原文片段'
}

function decorateCitations(markdown) {
  return markdown.replace(CITATION_PATTERN, (_match, index) =>
    [
      '<button type="button"',
      ' class="citation-marker"',
      ` data-citation-index="${index}"`,
      ` aria-label="查看引用 ${index}">`,
      `[${index}]`,
      '</button>',
    ].join(''),
  )
}

function sanitizeHtml(unsafeHtml, sanitize) {
  if (typeof sanitize === 'function') {
    return sanitize(unsafeHtml, SANITIZE_OPTIONS)
  }

  const domPurify = getPurifier()

  if (domPurify?.sanitize) {
    return domPurify.sanitize(unsafeHtml, SANITIZE_OPTIONS)
  }

  return ''
}

function getPurifier() {
  if (purifier) {
    return purifier
  }

  if (typeof window === 'undefined') {
    return null
  }

  purifier = createDOMPurify(window)
  return purifier
}
