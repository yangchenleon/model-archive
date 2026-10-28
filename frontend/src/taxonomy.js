export const CATEGORY_META = {
  gundam: { label: '高达', order: 0 },
  guomo: { label: '国模', order: 1 },
  ko: { label: 'KO', order: 2 },
}

export const CATEGORY_ORDER = ['gundam', 'guomo', 'ko']

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
