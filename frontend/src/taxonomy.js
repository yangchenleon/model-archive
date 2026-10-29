export const CATEGORY_META = {
  gundam: { label: '高达', order: 0 },
  guomo: { label: '国模', order: 1 },
  ko: { label: 'KO', order: 2 },
}

export const CATEGORY_ORDER = ['gundam', 'guomo', 'ko']

export const CHANNEL_META = {
  regular: { label: '通贩', order: 0 },
  pb: { label: 'PB', order: 1 },
  limited: { label: '限定', order: 2 },
  event: { label: '会场', order: 3 },
  other: { label: '其他', order: 4 },
  unknown: { label: '未知', order: 5 },
}

export const CHANNEL_OPTIONS = Object.entries(CHANNEL_META).map(([value, meta]) => ({
  value,
  label: meta.label,
  order: meta.order,
}))

export function channelLabel(value) {
  return CHANNEL_META[value || 'unknown']?.label || '未知'
}

export function categoryLabel(category) {
  return CATEGORY_META[category]?.label || '未分类'
}

export function categoryOrder(category) {
  return CATEGORY_META[category]?.order ?? 99
}

export function tierLabel(tier) {
  return tier ? `${tier} 级` : '未分级'
}

export async function fetchManufacturers() {
  const response = await fetch('/api/v1/manufacturers?limit=500')
  if (!response.ok) throw new Error('厂商读取失败')
  return response.json()
}

export async function fetchLines(manufacturerId) {
  if (!manufacturerId) return []
  const response = await fetch(`/api/v1/product-lines?manufacturer_id=${manufacturerId}&limit=500`)
  if (!response.ok) throw new Error('系列读取失败')
  return response.json()
}
