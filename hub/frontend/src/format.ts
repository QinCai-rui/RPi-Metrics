export function valueText(value: number | null | undefined, unit = '', digits = 1) {
  if (value == null || !Number.isFinite(value)) return 'Unavailable'
  return value.toLocaleString(undefined, { maximumFractionDigits: digits }) + unit
}

export function rate(value: number | null | undefined) {
  return valueText(value == null ? null : value / 1048576, ' MiB/s', 2)
}

export function capacity(value: number | null | undefined) {
  return valueText(value == null ? null : value / (1024 ** 3), ' GiB', 2)
}

export function duration(seconds: number | null | undefined) {
  if (seconds == null) return 'Unavailable'
  if (seconds < 60) return Math.floor(seconds) + 's'
  if (seconds < 3600) return Math.floor(seconds / 60) + 'm'
  if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ' + Math.floor(seconds % 3600 / 60) + 'm'
  return Math.floor(seconds / 86400) + 'd ' + Math.floor(seconds % 86400 / 3600) + 'h'
}

export function localTime(timestamp: string) {
  return new Date(timestamp).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}
