const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

export function daysInMonth(year, monthIndex) {
  return new Date(year, monthIndex + 1, 0).getDate()
}

export function ageFromBirthday(year, monthIndex, day) {
  const birth = new Date(year, monthIndex, day)
  if (Number.isNaN(birth.getTime())) return null
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  const monthDiff = today.getMonth() - birth.getMonth()
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age -= 1
  }
  return age
}

export function cmFromFeetInches(feet, inches) {
  const totalInches = Number(feet) * 12 + Number(inches)
  return Math.round(totalInches * 2.54 * 100) / 100
}

export function feetInchesFromCm(cm) {
  const totalInches = Number(cm) / 2.54
  const feet = Math.floor(totalInches / 12)
  const inches = Math.round(totalInches - feet * 12)
  if (inches === 12) return { feet: feet + 1, inches: 0 }
  return { feet, inches }
}

export function kgFromLb(lb) {
  return Math.round(Number(lb) * 0.45359237 * 100) / 100
}

export function lbFromKg(kg) {
  return Math.round(Number(kg) / 0.45359237 * 10) / 10
}

export { MONTHS }
