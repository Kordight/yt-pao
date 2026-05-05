export const API_BASE_URL = 'http://127.0.0.1:8000'
export const DEFAULT_THUMBNAIL = '/playlist-placeholder.svg'

export function resolveThumbnailSrc(path) {
  if (!path) {
    return DEFAULT_THUMBNAIL
  }

  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path
  }

  if (path.startsWith('/static/')) {
    return `${API_BASE_URL}${path}`
  }

  return path
}

export function formatDuration(seconds) {
  const totalSeconds = Number(seconds) || 0
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const remainingSeconds = totalSeconds % 60

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`
  }

  return `${minutes}:${String(remainingSeconds).padStart(2, '0')}`
}

export function formatCompactNumber(value) {
  const numericValue = Number(value) || 0
  return new Intl.NumberFormat('en', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(numericValue)
}