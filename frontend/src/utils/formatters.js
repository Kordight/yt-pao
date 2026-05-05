export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
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

export function formatPlaylistDuration(totalSeconds) {
  const seconds = Number(totalSeconds) || 0
  if (seconds <= 0) {
    return '0m'
  }

  const THREE_DAYS_IN_SECONDS = 3 * 24 * 3600

  if (seconds >= THREE_DAYS_IN_SECONDS) {
    const days = Math.floor(seconds / (24 * 3600))
    const hours = Math.floor((seconds % (24 * 3600)) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${days}d ${hours}h ${minutes}m`
  }

  if (seconds >= 3600) {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}h ${minutes}m`
  }

  if (seconds >= 60) {
    const minutes = Math.floor(seconds / 60)
    return `${minutes}m`
  }

  return `${Math.floor(seconds)}s`
}