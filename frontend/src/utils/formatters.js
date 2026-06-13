const BYTES_PER_KB = 1024
const BYTES_PER_MB = BYTES_PER_KB * 1024
const SCORE_PRECISION = {
  bm25: 2,
  default: 3,
  distance: 4,
  rerank: 3,
  rrf: 5,
}

export function formatFileSize(bytes) {
  const size = Number(bytes)

  if (!Number.isFinite(size) || size <= 0) {
    return '0 B'
  }

  if (size < BYTES_PER_KB) {
    return `${Math.round(size)} B`
  }

  if (size < BYTES_PER_MB) {
    return `${formatCompactNumber(size / BYTES_PER_KB)} KB`
  }

  return `${(size / BYTES_PER_MB).toFixed(1)} MB`
}

export function formatDate(iso) {
  if (!iso) {
    return '-'
  }

  const date = new Date(iso)

  if (Number.isNaN(date.getTime())) {
    return '-'
  }

  return date.toLocaleString('zh-CN')
}

export function formatMs(milliseconds) {
  if (
    milliseconds === null ||
    milliseconds === undefined ||
    milliseconds === ''
  ) {
    return '-'
  }

  const value = Number(milliseconds)

  if (!Number.isFinite(value)) {
    return '-'
  }

  return `${value
    .toFixed(2)
    .replace(/\.00$/, '.0')
    .replace(/(\.\d)0$/, '$1')} ms`
}

export function formatScore(value, kind = 'default') {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  const score = Number(value)

  if (!Number.isFinite(score)) {
    return '-'
  }

  return score.toFixed(SCORE_PRECISION[kind] ?? SCORE_PRECISION.default)
}

export function formatNullable(value) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  return String(value)
}

export function truncateMiddle(value, maxLength = 18) {
  const text = formatNullable(value)

  if (text === '-' || text.length <= maxLength) {
    return text
  }

  const tailLength = Math.min(5, Math.max(2, Math.floor(maxLength / 3)))
  const headLength = Math.max(1, maxLength - tailLength - 3)

  return `${text.slice(0, headLength)}...${text.slice(-tailLength)}`
}

export function formatDocumentLocation(metadata = {}) {
  const documentName = firstPresent([
    metadata.document_name,
    metadata.filename,
    metadata.source,
    metadata.title,
    metadata.document_id,
    metadata.doc_id,
  ])
  const page = firstPresent([
    metadata.page,
    metadata.page_number,
    metadata.page_label,
    metadata.page_index,
  ])

  if (documentName && page !== undefined) {
    return `${documentName} / p.${page}`
  }

  if (documentName) {
    return String(documentName)
  }

  if (page !== undefined) {
    return `p.${page}`
  }

  return '-'
}

function formatCompactNumber(value) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function firstPresent(values) {
  return values.find(
    (value) => value !== null && value !== undefined && value !== '',
  )
}
