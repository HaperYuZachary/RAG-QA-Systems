export const ALLOWED_UPLOAD_EXTENSIONS = ['.pdf', '.docx', '.md']
export const MAX_UPLOAD_FILE_SIZE = 50 * 1024 * 1024

export function validateUploadFile(file) {
  const extension = getFileExtension(file?.name ?? '')

  if (!ALLOWED_UPLOAD_EXTENSIONS.includes(extension)) {
    return {
      valid: false,
      reason: '仅支持 .pdf、.docx、.md 文件',
    }
  }

  if ((file?.size ?? 0) > MAX_UPLOAD_FILE_SIZE) {
    return {
      valid: false,
      reason: '单个文件不能超过 50MB',
    }
  }

  return {
    valid: true,
    reason: '',
  }
}

export function getFileExtension(filename) {
  const dotIndex = filename.lastIndexOf('.')

  if (dotIndex === -1) {
    return ''
  }

  return filename.slice(dotIndex).toLowerCase()
}
