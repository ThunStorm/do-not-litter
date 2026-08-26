const BEIJING_TIME_ZONE = 'Asia/Shanghai'

export function formatBeijingDateTime(
  value: string | null | undefined,
  options: Intl.DateTimeFormatOptions = {},
) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: BEIJING_TIME_ZONE,
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  }).format(new Date(value))
}

export function formatBeijingTime(value: string | null | undefined) {
  return formatBeijingDateTime(value, { second: '2-digit' })
}
