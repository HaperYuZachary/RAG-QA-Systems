import assert from 'node:assert/strict'
import test from 'node:test'
import {
  ALLOWED_UPLOAD_EXTENSIONS,
  MAX_UPLOAD_FILE_SIZE,
  validateUploadFile,
} from './uploadValidation.js'

test('accepts supported document extensions up to 50MB', () => {
  for (const extension of ALLOWED_UPLOAD_EXTENSIONS) {
    const result = validateUploadFile({
      name: `handbook${extension}`,
      size: MAX_UPLOAD_FILE_SIZE,
    })

    assert.deepEqual(result, {
      valid: true,
      reason: '',
    })
  }
})

test('rejects unsupported extensions', () => {
  const result = validateUploadFile({
    name: 'notes.txt',
    size: 10,
  })

  assert.equal(result.valid, false)
  assert.match(result.reason, /.pdf、.docx、.md/)
})

test('rejects files larger than 50MB', () => {
  const result = validateUploadFile({
    name: 'large.pdf',
    size: MAX_UPLOAD_FILE_SIZE + 1,
  })

  assert.equal(result.valid, false)
  assert.match(result.reason, /50MB/)
})
