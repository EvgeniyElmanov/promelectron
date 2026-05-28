/**
 * Returns an image URL with an optional size parameter.
 *
 * Rules:
 * - Only `/uploads/…` paths get `?size=…` appended.
 * - Absolute (MinIO / CDN) URLs are returned unchanged.
 * - Invalid / missing URLs are returned as-is.
 */
export function getImageUrl(baseUrl, size = 'original') {
  if (!baseUrl || typeof baseUrl !== 'string') {
    return baseUrl
  }

  // Leave external / MinIO URLs untouched
  if (!baseUrl.startsWith('/uploads/')) {
    return baseUrl
  }

  const separator = baseUrl.includes('?') ? '&' : '?'
  return `${baseUrl}${separator}size=${size}`
}
