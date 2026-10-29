<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { Check, ExternalLink, LoaderCircle, RotateCcw, Search, SkipForward } from 'lucide-vue-next'
import SkippedItems from './SkippedItems.vue'
import ManufacturerPicker from './ManufacturerPicker.vue'
import { CHANNEL_OPTIONS, fetchLines, fetchManufacturers } from '../taxonomy'

const emit = defineEmits(['pending'])

const SKIP_REASONS = [
  { value: 'later', label: '暂缓 / 以后再看' },
  { value: 'ad', label: '广告 / 赠品' },
  { value: 'duplicate', label: '重复' },
  { value: 'invalid', label: '无效 / 抽错' },
]

const stats = ref({ pending: 0, mapped: 0, created: 0, skipped: 0, later: 0, total: 0 })
const items = ref([])
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const message = ref('')
const messageIsError = ref(false)
const sort = ref('brand')
const skipReason = ref('later')
const showSkipped = ref(false)

const manufacturers = ref([])
const lines = ref([])
const form = reactive({ manufacturer_id: '', kit_name: '', product_code: '', product_line_id: '', work: '', release_channel: '', price_text: '' })
const search = ref('')
const candidates = ref([])
const selected = ref(null)
const searching = ref(false)
const player = ref(null)
const videoFailed = ref(false)

const item = computed(() => items.value[0] || null)
const videoUrl = computed(() => item.value?.video_id
  ? `https://www.bilibili.com/video/${item.value.video_id}?t=${item.value.start_seconds || 0}`
  : '')
const videoSrc = computed(() => item.value?.video_id
  ? `/api/v1/media/${item.value.video_id}?date=${(item.value.event_date || '').replaceAll('-', '')}`
  : '')
const timeLabel = computed(() => {
  const seconds = item.value?.start_seconds || 0
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
})

watch(item, () => { videoFailed.value = false })

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `请求失败 (${response.status})`)
  }
  return response.status === 204 ? null : response.json()
}

function flash(text, isError = false) {
  message.value = text
  messageIsError.value = isError
  window.clearTimeout(flash.timer)
  flash.timer = window.setTimeout(() => { message.value = '' }, 3200)
}

async function loadManufacturers() {
  try {
    manufacturers.value = await fetchManufacturers()
  } catch {
    manufacturers.value = []
  }
}

async function loadLines(manufacturerId) {
  if (!manufacturerId) {
    lines.value = []
    return
  }
  try {
    lines.value = await fetchLines(manufacturerId)
  } catch {
    lines.value = []
  }
}

async function prepare(next) {
  if (!next) return
  const brand = (next.brand || '').trim()
  const maker = manufacturers.value.find((row) => row.name === brand)
  form.manufacturer_id = maker?.id || ''
  form.kit_name = next.variant ? `${next.product}（${next.variant}）` : (next.product || '')
  form.product_code = ''
  form.product_line_id = ''
  form.work = ''
  form.release_channel = ''
  form.price_text = next.price_raw || ''
  selected.value = null
  search.value = next.product || ''
  candidates.value = []
  fetchCandidates()
  await loadLines(form.manufacturer_id)
  const line = lines.value.find((row) => row.name === (next.line || '').trim())
  form.product_line_id = line?.id || ''
}

function onManufacturerChange() {
  form.product_line_id = ''
  loadLines(form.manufacturer_id)
}

async function loadStats() {
  try {
    stats.value = await api('/api/v1/review/stats')
    emit('pending', stats.value.pending)
  } catch {
    /* sidebar badge is best-effort */
  }
}

async function loadQueue() {
  loading.value = true
  error.value = ''
  try {
    const data = await api(`/api/v1/review/items?state=pending&limit=50&sort=${sort.value}`)
    items.value = data.items
    if (items.value.length) prepare(items.value[0])
  } catch (exc) {
    error.value = `审核队列加载失败：${exc.message}`
  } finally {
    loading.value = false
  }
}

let searchTimer = 0
let searchSeq = 0
watch(search, () => {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(fetchCandidates, 250)
})

async function fetchCandidates() {
  const term = search.value.trim()
  const token = ++searchSeq
  if (!term) {
    candidates.value = []
    searching.value = false
    return
  }
  searching.value = true
  try {
    const data = await api(`/api/v1/products?limit=20&search=${encodeURIComponent(term)}`)
    if (token === searchSeq) candidates.value = data
  } catch {
    if (token === searchSeq) candidates.value = []
  } finally {
    if (token === searchSeq) searching.value = false
  }
}

async function afterAction(text) {
  items.value.shift()
  flash(text)
  await loadStats()
  if (items.value.length) prepare(items.value[0])
  else await loadQueue()
}

async function mapItem() {
  if (!selected.value || !item.value || busy.value) return
  const productName = selected.value.kit_name
  busy.value = true
  try {
    await api(`/api/v1/review/${item.value.id}/map`, {
      method: 'POST',
      body: JSON.stringify({ product_id: selected.value.id }),
    })
    await afterAction(`已映射到「${productName}」（仅记录归属，不改产品）`)
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

async function createProduct() {
  if (!item.value || busy.value) return
  if (!form.kit_name.trim()) {
    flash('产品名不能为空', true)
    return
  }
  if (!form.manufacturer_id) {
    flash('请选择厂商；没有就去「厂家管理」新建，刷新后再匹配', true)
    return
  }
  busy.value = true
  try {
    const product = await api(`/api/v1/review/${item.value.id}/create`, {
      method: 'POST',
      body: JSON.stringify({
        manufacturer_id: form.manufacturer_id,
        product_line_id: form.product_line_id || null,
        kit_name: form.kit_name.trim(),
        work: form.work.trim() || null,
        release_channel: form.release_channel || null,
        product_code: form.product_code.trim() || null,
        detail: item.value.detail,
        price_text: form.price_text.trim() || null,
      }),
    })
    await afterAction(`已新建「${product.kit_name}」`)
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

async function skipItem() {
  if (!item.value || busy.value) return
  busy.value = true
  try {
    await api(`/api/v1/review/${item.value.id}/skip`, {
      method: 'POST',
      body: JSON.stringify({ reason: skipReason.value }),
    })
    await afterAction(`已跳过（${SKIP_REASONS.find((r) => r.value === skipReason.value)?.label}）`)
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

function onVideoLoaded() {
  if (player.value && item.value) player.value.currentTime = item.value.start_seconds || 0
}

function onRestored() {
  loadStats()
  if (!items.value.length) loadQueue()
}

watch(sort, () => loadQueue())

function onKey(event) {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) return
  if (event.key === 'Enter' && selected.value) {
    event.preventDefault()
    mapItem()
  } else if (event.key === 's' || event.key === 'S') {
    skipItem()
  } else if (event.key === 'n' || event.key === 'N') {
    createProduct()
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  await loadManufacturers()
  await Promise.all([loadStats(), loadQueue()])
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <section class="review-view">
    <header class="page-header">
      <div>
        <p class="eyebrow">入库审核</p>
        <h1>产品入库审核</h1>
        <p class="page-subtitle">逐条确认抽取出的 mention：映射到已有产品、新建产品，或跳过广告与赠品。</p>
      </div>
      <div class="review-progress" aria-label="审核进度">
        <span>待审 <b>{{ stats.pending }}</b></span>
        <span>已映射 <b>{{ stats.mapped }}</b></span>
        <span>已新建 <b>{{ stats.created }}</b></span>
        <span>已跳过 <b>{{ stats.skipped }}</b></span>
      </div>
    </header>

    <div class="review-toolbar">
      <label class="sort-field">排序
        <select v-model="sort">
          <option value="brand">厂商 · 产品 · 时间</option>
          <option value="date">时间</option>
          <option value="product">产品 · 厂商 · 时间</option>
        </select>
      </label>
      <button class="secondary-button" type="button" @click="showSkipped = true">
        <RotateCcw :size="15" /> 已跳过 {{ stats.skipped }} · 打捞
      </button>
    </div>

    <section v-if="loading" class="state-panel"><LoaderCircle class="spin" :size="24" /><p>正在读取审核队列…</p></section>
    <section v-else-if="error" class="state-panel error-state"><p>{{ error }}</p><button class="secondary-button" type="button" @click="loadQueue">重新加载</button></section>
    <section v-else-if="!item" class="state-panel"><p>队列已清空。全部条目都处理完了 🎉</p><button class="secondary-button" type="button" @click="loadQueue">刷新</button></section>

    <div v-else class="review-grid">
      <article class="review-card">
        <header class="review-card-head">
          <div>
            <span class="review-date">{{ item.event_date }} · {{ item.brand || '未知厂商' }}<template v-if="item.line"> · {{ item.line }}</template></span>
            <h2>{{ item.product }}<em v-if="item.variant">（{{ item.variant }}）</em></h2>
          </div>
          <a v-if="videoUrl" class="video-link" :href="videoUrl" target="_blank" rel="noopener">
            ▶ {{ timeLabel }} 原视频 <ExternalLink :size="13" />
          </a>
        </header>

        <div class="review-video-wrap">
          <video
            v-if="!videoFailed"
            ref="player"
            class="review-video"
            :src="videoSrc"
            controls
            preload="metadata"
            @loadedmetadata="onVideoLoaded"
            @error="videoFailed = true"
          ></video>
          <p v-else class="video-fallback">本地视频不可用，<a :href="videoUrl" target="_blank" rel="noopener">改用 B 站原视频</a>。</p>
        </div>

        <blockquote class="evidence">{{ item.evidence }}</blockquote>

        <div class="review-meta">
          <span>抽取阶段 <b>{{ item.status_raw || 'unknown' }}</b></span>
          <span>抽取价格 <b>{{ item.price_raw || '—' }}</b></span>
          <span>抽取系列 <b>{{ item.line || '—' }}</b></span>
        </div>

        <div class="review-form">
          <label><span>厂商</span>
            <ManufacturerPicker
              v-model="form.manufacturer_id"
              :manufacturers="manufacturers"
              @change="onManufacturerChange"
            />
          </label>
          <label><span>产品编号</span><input v-model="form.product_code" placeholder="RG32 / MDH-12E" /></label>
          <label class="wide"><span>产品名（入库用，可改）</span><input v-model="form.kit_name" /></label>
          <label><span>系列</span>
            <select v-model="form.product_line_id">
              <option value="">未知</option>
              <option v-for="line in lines" :key="line.id" :value="line.id">{{ line.name }}</option>
            </select>
          </label>
          <label><span>作品 / IP</span><input v-model="form.work" placeholder="EVANGELION / 勇者王 …" /></label>
          <label><span>渠道</span>
            <select v-model="form.release_channel">
              <option value="">未知</option>
              <option v-for="channel in CHANNEL_OPTIONS" :key="channel.value" :value="channel.value">{{ channel.label }}</option>
            </select>
          </label>
          <label><span>价格</span><input v-model="form.price_text" placeholder="78 / 68元 / 22000日元" /></label>
        </div>
        <p v-if="!form.manufacturer_id" class="manufacturer-warning">没有匹配到厂商：去「厂家管理」新建，刷新页面后再匹配。</p>

        <footer class="review-actions">
          <span class="hint">Enter 映射 · N 新建 · S 跳过</span>
          <div class="action-group">
            <select v-model="skipReason" class="skip-select" aria-label="跳过原因">
              <option v-for="reason in SKIP_REASONS" :key="reason.value" :value="reason.value">{{ reason.label }}</option>
            </select>
            <button class="text-button" type="button" :disabled="busy" @click="skipItem"><SkipForward :size="16" />跳过</button>
            <button class="secondary-button" type="button" :disabled="busy" @click="createProduct"><Check :size="16" />新建产品并入库</button>
          </div>
        </footer>
      </article>

      <aside class="review-side">
        <h3>匹配现有产品</h3>
        <label class="search-field"><Search :size="16" /><input v-model="search" type="search" placeholder="搜厂商 / 产品 / 系列" /></label>
        <p class="side-hint" v-if="searching">搜索中…</p>
        <ul class="candidate-list">
          <li
            v-for="product in candidates"
            :key="product.id"
            :class="{ selected: selected && selected.id === product.id }"
            @click="selected = product"
          >
            <strong>{{ product.kit_name }}</strong>
            <span>
              {{ product.manufacturer || '未填厂商' }}<template v-if="product.product_line"> · {{ product.product_line }}</template><template v-if="product.product_code"> · {{ product.product_code }}</template>
            </span>
          </li>
          <li v-if="!searching && !candidates.length" class="empty">没有匹配的产品</li>
        </ul>
        <button class="primary-button map-button" type="button" :disabled="!selected || busy" @click="mapItem">
          映射到选中产品
        </button>
        <p class="side-tip">映射只记录归属，不改产品；重复内容请跳过，新条目用「新建」。</p>
      </aside>
    </div>

    <p v-if="message" class="review-message" :class="{ 'is-error': messageIsError }">{{ message }}</p>

    <SkippedItems :open="showSkipped" @close="showSkipped = false" @restored="onRestored" />
  </section>
</template>

<style scoped>
.review-progress { display: flex; gap: 14px; color: #64736e; font-size: 12px; white-space: nowrap; }
.review-progress b { color: #1c2b27; font-size: 15px; margin-left: 2px; font-variant-numeric: tabular-nums; }

.review-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.sort-field { display: flex; align-items: center; gap: 6px; color: #5d6d67; font-size: 12px; }
.sort-field select, .skip-select { min-height: 32px; padding: 0 8px; color: #2c4038; background: #fff; border: 1px solid #cfd9d4; border-radius: 6px; }
.review-video-wrap { margin-top: 16px; }
.review-video { display: block; width: 100%; max-height: 320px; background: #000; border-radius: 6px; }
.video-fallback { margin: 0; padding: 10px 12px; color: #7a8782; font-size: 12px; background: #f7faf6; border: 1px dashed #d3ddd6; border-radius: 6px; }
.video-fallback a { color: #24705f; }
.action-group { display: flex; align-items: center; gap: 8px; }
.skip-select { max-width: 148px; font-size: 12px; }

.review-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 16px; align-items: start; }
.review-card { padding: 22px; background: #fff; border: 1px solid #d9e1dc; border-radius: 8px; }
.review-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.review-date { color: #6b7874; font-size: 12px; font-variant-numeric: tabular-nums; }
.review-card h2 { margin: 6px 0 0; color: #18251f; font-size: 22px; line-height: 1.3; }
.review-card h2 em { color: #6b7874; font-size: 15px; font-style: normal; font-weight: 500; }
.video-link { display: inline-flex; align-items: center; gap: 5px; padding: 6px 10px; color: #24705f; font-size: 12px; text-decoration: none; background: #eef6f1; border: 1px solid #cfe3d8; border-radius: 6px; white-space: nowrap; }
.video-link:hover { background: #e2f0e8; }

.evidence { margin: 18px 0 14px; padding: 14px 16px; color: #2d3d37; font-size: 15px; line-height: 1.75; background: #f7faf6; border-left: 3px solid #8cb59b; border-radius: 0 6px 6px 0; }

.review-meta { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-bottom: 18px; color: #7a8782; font-size: 12px; }
.review-meta b { color: #3c4f48; font-weight: 600; }

.review-form { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding-top: 18px; border-top: 1px solid #e7ece8; }
.review-form label { display: grid; gap: 6px; color: #5d6d67; font-size: 12px; }
.review-form label.wide { grid-column: 1 / -1; }
.review-form input, .review-form select { width: 100%; min-height: 36px; padding: 0 10px; color: #22302b; background: #fbfcfa; border: 1px solid #cfd9d4; border-radius: 5px; outline: none; }
.review-form input:focus, .review-form select:focus { background: #fff; border-color: #59877b; }
.manufacturer-warning { margin: 8px 0 0; color: #a4402c; font-size: 12px; }

.review-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 18px; padding-top: 14px; border-top: 1px solid #e7ece8; }
.review-actions .hint { color: #98a39f; font-size: 12px; }
.review-actions > div { display: flex; gap: 8px; }

.review-side { padding: 20px; background: #fff; border: 1px solid #d9e1dc; border-radius: 8px; }
.review-side h3 { margin: 0 0 12px; color: #2c4038; font-size: 14px; }
.review-side .search-field { width: 100%; }
.candidate-list { display: grid; gap: 2px; max-height: 380px; margin: 12px 0; padding: 0; overflow: auto; list-style: none; }
.candidate-list li { padding: 9px 10px; cursor: pointer; border: 1px solid transparent; border-radius: 6px; }
.candidate-list li:hover { background: #f3f7f3; }
.candidate-list li.selected { background: #eaf4ee; border-color: #8fb9a0; }
.candidate-list strong { display: block; color: #22302b; font-size: 13px; font-weight: 600; line-height: 1.4; }
.candidate-list span { display: block; margin-top: 3px; color: #7c8a85; font-size: 11px; }
.candidate-list .empty { color: #98a39f; font-size: 12px; cursor: default; }
.map-button { width: 100%; }
.side-hint { margin: 8px 0 0; color: #98a39f; font-size: 11px; }
.side-tip { margin: 12px 0 0; color: #98a39f; font-size: 11px; line-height: 1.6; }

.review-message { position: fixed; right: 28px; bottom: 28px; padding: 11px 16px; color: #1f4a3c; font-size: 13px; background: #e8f5ec; border: 1px solid #b9d9c4; border-radius: 7px; box-shadow: 0 8px 24px #17352a1f; }
.review-message.is-error { color: #8d3423; background: #fdeee9; border-color: #efc6ba; }

@media (max-width: 900px) {
  .review-grid { grid-template-columns: 1fr; }
  .review-form { grid-template-columns: 1fr; }
}
</style>
