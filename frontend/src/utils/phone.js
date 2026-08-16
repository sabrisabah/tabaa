const IRAQ_LOCAL_RE = /^07\d{9}$/

/**
 * Normalize Iraqi mobiles to local 11-digit form: 07XXXXXXXXX
 * Accepts: 07…, 7…, 9647…, +9647…
 */
export function toIraqLocal11(value) {
  let digits = String(value || '').replace(/\D/g, '')

  if (digits.startsWith('964')) digits = digits.slice(3)
  if (digits.startsWith('0') && digits.length > 11) {
    // keep trimming accidental leading zeros beyond local format
    while (digits.startsWith('00')) digits = digits.slice(1)
  }

  if (digits.startsWith('7') && digits.length === 10) {
    digits = `0${digits}`
  }

  if (digits.startsWith('07')) {
    return digits.slice(0, 11)
  }

  // While typing: allow partial 0 / 07 / 07…
  if (digits === '0' || digits.startsWith('0')) {
    return digits.slice(0, 11)
  }

  return digits.slice(0, 11)
}

/** @deprecated Prefer toIraqLocal11 — kept for older imports */
export function toIraqLocalDigits(value) {
  const local = toIraqLocal11(value)
  return local.startsWith('0') ? local.slice(1) : local
}

/** @deprecated Login/register now use local 11-digit numbers */
export function toIraqE164(localOrFull) {
  return toIraqLocal11(localOrFull)
}

export function isValidIraqLocal(local) {
  return IRAQ_LOCAL_RE.test(toIraqLocal11(local))
}

export function formatIraqLocalInput(value) {
  return toIraqLocal11(value)
}
