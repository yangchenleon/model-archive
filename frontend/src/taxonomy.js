export const CATEGORY_META = {
  gundam: { label: '高达', order: 0 },
  guomo: { label: '国模', order: 1 },
  ko: { label: 'KO', order: 2 },
}

export const CATEGORY_ORDER = ['gundam', 'guomo', 'ko']

export const CHANNEL_META = {
  regular: { label: '通贩', order: 0 },
  pb: { label: 'PB', order: 1 },
  base: { label: '基地', order: 2 },
  event: { label: '活动/会场', order: 3 },
  lottery: { label: '抽奖/一番赏', order: 4 },
  limited: { label: '限定', order: 5 },
  unknown: { label: '未知', order: 6 },
}

export const CHANNEL_OPTIONS = Object.entries(CHANNEL_META).map(([value, meta]) => ({
  value,
  label: meta.label,
  order: meta.order,
}))

export const CRAFT_META = {
  clear: { label: '彩透', order: 0 },
  transparent: { label: '透明', order: 1 },
  plated: { label: '电镀', order: 2 },
  clear_plated: { label: '电镀透明', order: 3 },
  color_plated: { label: '彩色电镀', order: 4 },
  pearl: { label: '珍珠/珠光', order: 5 },
  metallic: { label: '金属色', order: 6 },
  coating: { label: '特殊涂层', order: 7 },
  matte: { label: '消光', order: 8 },
  crystal: { label: '水晶', order: 9 },
  luminous: { label: '夜光', order: 10 },
}

export const CRAFT_OPTIONS = Object.entries(CRAFT_META).map(([value, meta]) => ({
  value,
  label: meta.label,
  order: meta.order,
}))

export function channelLabel(value) {
  return CHANNEL_META[value || 'unknown']?.label || '未知'
}

export function craftLabel(value) {
  return value ? CRAFT_META[value]?.label || value : '未知'
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
