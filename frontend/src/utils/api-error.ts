import axios from 'axios'

/**
 * Extract the error message from an API error response.
 * Uses axios.isAxiosError() for proper type narrowing instead of unsafe `as` casts.
 */
export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || fallback
  }
  return fallback
}

/**
 * Extract the HTTP status code from an API error response.
 */
export function getApiErrorStatus(error: unknown): number | undefined {
  if (axios.isAxiosError(error)) {
    return error.response?.status
  }
  return undefined
}
