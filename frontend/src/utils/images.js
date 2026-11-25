export const maxImageSize = 5 * 1024 * 1024
const typeError = 'Допустимы только картинки форматов JPEG, PNG, GIF и WebP'
const sizeError = 'Файл слишком большой. Максимальный размер картинки: 5 МБ'
export function imageUploadError(error) {
  if (error.status === 413) return sizeError
  if (error.status === 422) return typeError
  return error.message
}
export function imageFileError(file) {
  if (!['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(file.type)) return typeError
  if (file.size > maxImageSize) return sizeError
  return ''
}
export function imageUrl(url, baseUrl) {
  return `${baseUrl.replace(/\/$/, '')}/${url.replace(/^\//, '')}`
}
