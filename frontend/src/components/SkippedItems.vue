<script setup>
import { ref, watch } from 'vue'
import { LoaderCircle, RotateCcw, Search, X } from 'lucide-vue-next'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['close', 'restored'])

const REASONS = { later: '暂缓', ad: '广告 / 赠品', duplicate: '重复', invalid: '无效' }
const items = ref([])
const total = ref(0)
const q = ref('')
const loading = ref(false)
const restoring = ref('')

let timer = 0

async function load() {
  loading.value = true
  try {
    const response = await fetch(`/api/v1/review/items?state=skipped&limit=200&sort=brand&q=${encodeURIComponent(q.value)}`)
    if (!response.ok) throw new Error('load failed')
    const data = await response.json()
    items.value = data.items
    total.value = data.total
  } catch {
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

watch(() => props.open, (open) => {
  if (open) {
    q.value = ''
    load()
  }
})

watch(q, () => {
  window.clearTimeout(timer)
  timer = window.setTimeout(load, 250)
})

async function restore(id) {
  restoring.value = id
  try {
    const response = await fetch(`/api/v1/review/${id}/reset`, { method: 'POST' })
    if (!response.ok) return
    await load()
    emit('restored')
  } finally {
    restoring.value = ''
  }
}
</script>

<template>
  <Transition name="fade">
    <div v-if="open" class="skipped-layer" @click.self="$emit('close')">
      <section class="skipped-panel" aria-label="已跳过的条目">
        <header>
          <div>
            <span class="eyebrow">暂不录入</span>
            <h2>已跳过（{{ total }}）</h2>
            <p class="panel-hint">跳过的 mention 仍保留在这里，随时可以放回待审队列。</p>
          </div>
          <button class="icon-button" type="button" aria-label="关闭" @click="$emit('close')"><X :size="20" /></button>
        </header>

        <label class="search-field skipped-search">
          <Search :size="16" />
          <input v-model="q" type="search" placeholder="搜厂商 / 产品 / 原文" />
        </label>

        <p v-if="loading" class="panel-state"><LoaderCircle class="spin" :size="18" />读取中…</p>
        <p v-else-if="!items.length" class="panel-state">没有跳过的条目。{{ q ? '换个关键词试试。' : '' }}</p>
        <ul v-else class="skipped-list">
          <li v-for="entry in items" :key="entry.id">
            <div class="skipped-main">
              <span class="skipped-date">{{ entry.event_date }}</span>
              <span class="skipped-brand">{{ entry.brand || '未知厂商' }}</span>
              <span class="skipped-product">{{ entry.product }}</span>
              <span class="skipped-reason">{{ REASONS[entry.skip_reason] || '暂缓' }}</span>
            </div>
            <button class="secondary-button" type="button" :disabled="restoring === entry.id" @click="restore(entry.id)">
              <RotateCcw :size="14" />放回队列
            </button>
          </li>
        </ul>
      </section>
    </div>
  </Transition>
</template>

<style scoped>
.skipped-layer { position: fixed; z-index: 30; inset: 0; display: flex; align-items: center; justify-content: center; padding: 24px; background: #13201c66; }
.skipped-panel { width: min(100%, 720px); max-height: 82vh; display: flex; flex-direction: column; padding: 22px; overflow: hidden; background: #fff; border: 1px solid #d9e1dc; border-radius: 8px; box-shadow: 0 18px 54px #17271f35; }
.skipped-panel > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.skipped-panel h2 { margin: 4px 0 0; color: #1b2925; font-size: 20px; }
.panel-hint { margin: 6px 0 0; color: #7a8782; font-size: 12px; }
.skipped-search { margin: 16px 0 8px; }
.panel-state { display: flex; align-items: center; gap: 8px; margin: 24px 0; color: #7a8782; font-size: 13px; }
.skipped-list { display: grid; gap: 4px; margin: 0; padding: 0; overflow: auto; list-style: none; }
.skipped-list li { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 9px 10px; border: 1px solid #e5ebe6; border-radius: 6px; }
.skipped-main { display: flex; align-items: baseline; gap: 8px; min-width: 0; font-size: 13px; }
.skipped-date { color: #7a8782; font-size: 11px; font-variant-numeric: tabular-nums; white-space: nowrap; }
.skipped-brand { color: #445751; font-weight: 600; white-space: nowrap; }
.skipped-product { color: #22302b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.skipped-reason { flex: 0 0 auto; padding: 1px 7px; color: #8a5a1f; font-size: 11px; background: #fdf4e6; border: 1px solid #eed9b8; border-radius: 999px; }
.fade-enter-active, .fade-leave-active { transition: opacity .18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
