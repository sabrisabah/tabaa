const AUTH_PASSWORD_RE = /^[A-Za-z0-9]{4}$/

export function formatAuthPassword(value) {
  return String(value || '')
    .replace(/[^A-Za-z0-9]/g, '')
    .slice(0, 4)
}

export function isValidAuthPassword(value) {
  return AUTH_PASSWORD_RE.test(String(value || ''))
}
