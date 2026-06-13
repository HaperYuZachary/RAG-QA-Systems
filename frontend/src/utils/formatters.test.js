import assert from 'node:assert/strict'
import test from 'node:test'
import {
  formatDate,
  formatDocumentLocation,
  formatFileSize,
  formatMs,
  formatNullable,
  formatScore,
  truncateMiddle,
} from './formatters.js'

test('formats byte counts as B, KB, or MB with one decimal for MB', () => {
  assert.equal(formatFileSize(0), '0 B')
  assert.equal(formatFileSize(512), '512 B')
  assert.equal(formatFileSize(1024), '1 KB')
  assert.equal(formatFileSize(1536), '1.5 KB')
  assert.equal(formatFileSize(1024 * 1024), '1.0 MB')
  assert.equal(formatFileSize(2.25 * 1024 * 1024), '2.3 MB')
})

test('formats missing dates as a placeholder', () => {
  assert.equal(formatDate(''), '-')
  assert.equal(formatDate(null), '-')
  assert.equal(formatDate(undefined), '-')
})

test('formats ISO timestamps with zh-CN locale', () => {
  const expected = new Date('2026-06-11T08:30:00.000Z').toLocaleString('zh-CN')

  assert.equal(formatDate('2026-06-11T08:30:00.000Z'), expected)
})

test('formats milliseconds with one or two decimal places and a placeholder for missing values', () => {
  assert.equal(formatMs(null), '-')
  assert.equal(formatMs(undefined), '-')
  assert.equal(formatMs(Number.NaN), '-')
  assert.equal(formatMs(0), '0.0 ms')
  assert.equal(formatMs(1.234), '1.23 ms')
  assert.equal(formatMs(12.3), '12.3 ms')
})

test('formats debug table scores with field-specific precision and placeholders', () => {
  assert.equal(formatScore(null, 'rrf'), '-')
  assert.equal(formatScore(undefined, 'distance'), '-')
  assert.equal(formatScore(Number.NaN, 'bm25'), '-')
  assert.equal(formatScore(0.0312349, 'rrf'), '0.03123')
  assert.equal(formatScore(0.123456, 'distance'), '0.1235')
  assert.equal(formatScore(12.345, 'bm25'), '12.35')
  assert.equal(formatScore(0.87654, 'rerank'), '0.877')
})

test('formats nullable ranks and identifiers as table-safe text', () => {
  assert.equal(formatNullable(null), '-')
  assert.equal(formatNullable(undefined), '-')
  assert.equal(formatNullable(''), '-')
  assert.equal(formatNullable(2), '2')
  assert.equal(formatNullable('chunk_1'), 'chunk_1')
})

test('truncates long chunk ids through the middle', () => {
  assert.equal(truncateMiddle(null), '-')
  assert.equal(truncateMiddle('chunk_short'), 'chunk_short')
  assert.equal(
    truncateMiddle('chunk_1234567890abcdef', 16),
    'chunk_12...bcdef',
  )
})

test('formats document location from debug hit metadata', () => {
  assert.equal(
    formatDocumentLocation({
      document_name: '员工手册.md',
      page: 3,
    }),
    '员工手册.md / p.3',
  )
  assert.equal(
    formatDocumentLocation({
      filename: '制度.pdf',
      page_number: 12,
    }),
    '制度.pdf / p.12',
  )
  assert.equal(formatDocumentLocation({ document_id: 'doc_1' }), 'doc_1')
  assert.equal(formatDocumentLocation({}), '-')
})
