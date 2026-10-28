export const COLLECTION_STATUSES = [
  { value: 'planning', label: '构想', hint: '范围还没定' },
  { value: 'active', label: '进行中', hint: '正在收' },
  { value: 'paused', label: '暂缓', hint: '先放一放' },
  { value: 'abandoned', label: '放弃', hint: '不收了' },
]

export const COLLECTION_STATUS_META = Object.fromEntries(
  COLLECTION_STATUSES.map((item) => [item.value, item]),
)

export function formatShortDate(value) {
  if (!value) return '—'
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [, month, day] = value.split('-')
    return `${month}-${day}`
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit' }).format(date)
}

export function statusLabel(status) {
  return COLLECTION_STATUS_META[status]?.label || status
}
