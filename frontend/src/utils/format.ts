/**
 * Format a date string as a short date (e.g. "Feb 16, 2026").
 */
export function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

/**
 * Format a date string as date + time (e.g. "Feb 16, 2026, 2:30 PM").
 */
export function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

/**
 * Format a monetary amount with currency symbol (e.g. "$12.99").
 */
export function formatAmount(amount: number | null, currency: string | null): string {
  if (amount === null) return '-'
  const curr = currency || 'USD'
  return new Intl.NumberFormat(undefined, { style: 'currency', currency: curr }).format(amount)
}

/**
 * Format an ISO date string as a relative time in the past (e.g. "5m ago").
 */
export function formatTimeAgo(isoString: string | null): string {
  if (!isoString) return '-'
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diffMs = now - then
  if (diffMs < 0) return 'just now'

  const diffSec = Math.floor(diffMs / 1000)
  if (diffSec < 60) return 'just now'

  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`

  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}h ago`

  const diffDay = Math.floor(diffHour / 24)
  return `${diffDay}d ago`
}

/**
 * Format an ISO date string as a relative time in the future (e.g. "2m 30s").
 */
export function formatTimeUntil(isoString: string | null): string {
  if (!isoString) return '-'
  const now = Date.now()
  const target = new Date(isoString).getTime()
  const diffMs = target - now
  if (diffMs <= 0) return 'now'

  const diffSec = Math.floor(diffMs / 1000)
  const minutes = Math.floor(diffSec / 60)
  const seconds = diffSec % 60

  if (minutes > 0) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}
