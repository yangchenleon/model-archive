<script setup>
import { computed, ref, watch } from 'vue'
import { ArrowLeft, LoaderCircle, Pencil, Plus, RefreshCw, Search, Trash2, Trophy, X } from 'lucide-vue-next'
import CollectionDialog from './CollectionDialog.vue'
import CollectionItemDialog from './CollectionItemDialog.vue'
import CollectionProgress from './CollectionProgress.vue'
import { COLLECTION_STATUS_META, formatShortDate } from '../collectionMeta'

const props = defineProps({
  collectionId: { type: String, required: true },
})
const emit = defineEmits(['back'])

const ASSET_STATE_LABELS = {
  pending: '待拼',
  keep: '收藏',
  displayed: '展示',
  stored: '收纳',
}

const collection = ref(null)
const items = ref([])
const itemTotal = ref(0)
const allProductIds = ref([])
const loading = ref(true)
const itemsLoading = ref(false)
const error = ref('')
const stateFilter = ref('all')
const search = ref('')
const selected = ref([])
const busy = ref(false)
const editOpen = ref(false)
const addOpen = ref(false)
const message = ref('')
const messageError = ref(false)

const stats = computed(() => collection.value?.stats || {
  total: 0, owned: 0, built: 0, unbuilt: 0, missing: 0,
  sold_only: 0, extra_copies: 0, percent: 0, completed: false,
})

const selectedSet = computed(() => new Set(selected.value))
const selectedItems = computed(() => items.value.filter((item) => selectedSet.value.has(item.id)))
const selectedMissing = computed(() => selectedItems.value.filter((item) => !item.owned))
const allChecked = computed(() => items.value.length > 0 && items.value.every((item) => selectedSet.value.has(item.id)))

function flash(text, isError = false) {
  message.value = text
  messageError.value = isError
  window.clearTimeout(flash.timer)
  flash.timer = window.setTimeout(() => { message.value = '' }, 3600)
}

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options })
  const body = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) throw new Error(body?.detail || `请求失败 (${response.status})`)
  return body
}

async function loadCollection() {
  collection.value = await api(`/api/v1/collections/${props.collectionId}`)
}

async function loadItems() {
  itemsLoading.value = true
  try {
    const query = new URLSearchParams({ state: stateFilter.value, limit: '500' })
    if (search.value.trim()) query.set('q', search.value.trim())
    const body = await api(`/api/v1/collections/${props.collectionId}/items?${query}`)
    items.value = body.items
    itemTotal.value = body.total
    selected.value = selected.value.filter((id) => body.items.some((item) => item.id === id))
  } finally {
    itemsLoading.value = false
  }
}

async function loadAll() {
  loading.value = true
  error.value = ''
  try {
    await loadCollection()
    await loadItems()
  } catch (exc) {
    error.value = exc.message
  } finally {
    loading.value = false
  }
}

function setFilter(state) {
  stateFilter.value = state
  selected.value = []
  loadItems().catch((exc) => flash(exc.message, true))
}

function submitSearch() {
  selected.value = []
  loadItems().catch((exc) => flash(exc.message, true))
}

function clearSearch() {
  search.value = ''
  submitSearch()
}

function toggle(id) {
  const index = selected.value.indexOf(id)
  if (index >= 0) selected.value.splice(index, 1)
  else selected.value.push(id)
}

function toggleAll() {
  selected.value = allChecked.value ? [] : items.value.map((item) => item.id)
}

function stateText(item) {
  if (!item.owned) return item.sold_only ? '曾有已售' : '未拥有'
  const states = item.asset_states.map((state) => ASSET_STATE_LABELS[state] || state).join(' / ')
  return `${states}${item.asset_count > 1 ? ` · ${item.asset_count} 台` : ''}`
}

function statusText(item) {
  if (item.owned) return item.built ? '已拼' : '已拥有'
  return item.sold_only ? '缺口 · 曾售' : '缺口'
}

function statusClass(item) {
  if (item.owned) return item.built ? 'built' : 'owned'
  return item.sold_only ? 'sold' : 'missing'
}

async function own(item) {
  if (busy.value) return
  busy.value = true
  try {
    const asset = await api('/api/v1/assets', {
      method: 'POST',
      body: JSON.stringify({ product_id: item.product_id, state: 'pending' }),
    })
    flash(`已登记 ${asset.code}（待拼）`)
    await Promise.all([loadCollection(), loadItems()])
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

async function ownSelected() {
  if (busy.value || !selectedMissing.value.length) return
  busy.value = true
  try {
    const created = await api('/api/v1/assets/bulk', {
      method: 'POST',
      body: JSON.stringify({ product_ids: selectedMissing.value.map((item) => item.product_id), state: 'pending' }),
    })
    flash(`已登记 ${created.length} 台（待拼）`)
    selected.value = []
    await Promise.all([loadCollection(), loadItems()])
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

async function removeSelected() {
  if (busy.value || !selected.value.length) return
  if (!window.confirm(`从收藏集移除 ${selected.value.length} 个目标？\n\n只动清单，不会删除产品或资产。`)) return
  busy.value = true
  try {
    const result = await api(`/api/v1/collections/${props.collectionId}/items/bulk-remove`, {
      method: 'POST',
      body: JSON.stringify({ item_ids: selected.value }),
    })
    selected.value = []
    flash(`已移除 ${result.removed} 个目标`)
    await Promise.all([loadCollection(), loadItems()])
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

async function saveNote(item, event) {
  const note = event.target.value.trim()
  if (note === (item.note || '')) return
  try {
    const updated = await api(`/api/v1/collections/${props.collectionId}/items/${item.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ note: note || null }),
    })
    item.note = updated.note
    flash('备注已保存')
  } catch (exc) {
    event.target.value = item.note || ''
    flash(exc.message, true)
  }
}

async function openAdd() {
  try {
    const body = await api(`/api/v1/collections/${props.collectionId}/items?state=all&limit=500`)
    allProductIds.value = body.items.map((item) => item.product_id)
  } catch {
    allProductIds.value = []
  }
  addOpen.value = true
}

async function onItemsAdded(result) {
  flash(`已加入 ${result.added} 个目标${result.skipped ? `，跳过 ${result.skipped} 个已存在` : ''}`)
  selected.value = []
  await Promise.all([loadCollection(), loadItems()])
}

async function onCollectionSaved(updated) {
  collection.value = updated
  editOpen.value = false
  await Promise.all([loadCollection(), loadItems()])
  flash('收藏集已保存')
}

async function removeCollection() {
  if (!collection.value) return
  if (!window.confirm(`删除收藏集「${collection.value.title}」？\n\n只删除范围和进度，不会删除产品或资产。`)) return
  try {
    await api(`/api/v1/collections/${props.collectionId}`, { method: 'DELETE' })
    emit('back')
  } catch (exc) {
    flash(exc.message, true)
  }
}

watch(() => props.collectionId, loadAll, { immediate: true })
</script>

<template>
  <section class="collection-detail">
    <header class="detail-head">
      <div>
        <button class="text-button back" type="button" @click="emit('back')"><ArrowLeft :size="16" />收藏集</button>
        <div class="title-row">
          <h1>{{ collection?.title || '收藏集' }}</h1>
          <span v-if="collection" class="status-pill" :class="collection.status">{{ COLLECTION_STATUS_META[collection.status]?.label || collection.status }}</span>
          <span v-if="stats.completed" class="completed-badge">已制霸</span>
        </div>
        <p class="page-subtitle description">{{ collection?.description || '还没有描述。' }}</p>
        <p v-if="collection" class="meta-line">
          <span v-if="collection.started_on">开始 {{ collection.started_on }}</span>
          <span v-if="collection.target_on">目标 {{ collection.target_on }}</span>
          <span>更新 {{ formatShortDate(collection.updated_at) }}</span>
        </p>
      </div>
      <div class="header-actions">
        <button class="secondary-button" type="button" :disabled="loading" @click="loadAll"><RefreshCw :size="16" />刷新</button>
        <button class="secondary-button" type="button" :disabled="!collection" @click="editOpen = true"><Pencil :size="16" />编辑</button>
        <button class="text-button danger" type="button" :disabled="!collection" @click="removeCollection"><Trash2 :size="16" />删除</button>
        <button class="primary-button" type="button" :disabled="!collection" @click="openAdd"><Plus :size="17" />添加目标</button>
      </div>
    </header>

    <p v-if="loading" class="state-panel"><LoaderCircle class="spin" :size="24" />正在读取收藏集…</p>
    <p v-else-if="error" class="state-panel error-state">{{ error }}</p>
    <template v-else-if="collection">
      <section class="progress-panel" aria-label="制霸进度">
        <div class="progress-top">
          <div>
            <strong>{{ stats.owned }}</strong><span> / {{ stats.total }}</span>
          </div>
          <span class="percent">{{ stats.total ? `${stats.percent}%` : '未定义范围' }}</span>
        </div>
        <CollectionProgress :built="stats.built" :owned="stats.owned" :total="stats.total" :height="14" />
        <div class="legend">
          <span><i class="dot built"></i>已拼 {{ stats.built }}</span>
          <span><i class="dot unbuilt"></i>已拥有未拼 {{ stats.unbuilt }}</span>
          <span><i class="dot missing"></i>缺口 {{ stats.missing }}</span>
        </div>
        <p class="progress-note">
          <span v-if="!stats.total">还没有目标。点右上角「添加目标」从产品目录选。</span>
          <span v-else-if="stats.completed">全部收齐。</span>
          <span v-else>还差 {{ stats.missing }} 款。</span>
          <span v-if="stats.sold_only">另有 {{ stats.sold_only }} 款已售出。</span>
          <span v-if="stats.extra_copies">复份 {{ stats.extra_copies }} 台。</span>
        </p>
      </section>

      <section class="toolbar">
        <div class="filter-tabs" role="group" aria-label="目标筛选">
          <button type="button" :class="{ active: stateFilter === 'all' }" @click="setFilter('all')">全部 {{ stats.total }}</button>
          <button type="button" :class="{ active: stateFilter === 'owned' }" @click="setFilter('owned')">已拥有 {{ stats.owned }}</button>
          <button type="button" :class="{ active: stateFilter === 'missing' }" @click="setFilter('missing')">未拥有 {{ stats.missing }}</button>
        </div>
        <label class="search-field"><Search :size="18" /><input v-model="search" type="search" placeholder="搜索产品名 / 编号（回车）" @keyup.enter="submitSearch" /></label>
        <button v-if="search" class="reset-button" type="button" @click="clearSearch"><X :size="15" />清除</button>
        <span class="result-count">{{ selected.length ? `已选 ${selected.length} 项` : `${itemTotal} 项` }}</span>
      </section>

      <section v-if="selected.length" class="action-bar">
        <span>已选 {{ selected.length }} 项</span>
        <button v-if="selectedMissing.length" class="chip-button" type="button" :disabled="busy" @click="ownSelected">登记 {{ selectedMissing.length }} 台</button>
        <button class="chip-button danger" type="button" :disabled="busy" @click="removeSelected">移出收藏集</button>
      </section>

      <p v-if="itemsLoading" class="state-panel small"><LoaderCircle class="spin" :size="20" />正在读取目标…</p>
      <div v-else-if="items.length" class="item-table">
        <div class="item-head">
          <span class="check"><input type="checkbox" :checked="allChecked" @change="toggleAll" /></span>
          <span>产品</span>
          <span>状态</span>
          <span>备注</span>
          <span class="action-col">操作</span>
        </div>
        <div v-for="item in items" :key="item.id" class="item-row" :class="{ picked: selectedSet.has(item.id) }">
          <span class="check"><input type="checkbox" :checked="selectedSet.has(item.id)" @change="toggle(item.id)" /></span>
          <div class="item-main">
            <strong>{{ item.name }}</strong>
            <small>{{ [item.manufacturer, item.product_line, item.product_code].filter(Boolean).join(' · ') }}</small>
          </div>
          <div class="item-status">
            <span class="target-pill" :class="statusClass(item)">{{ statusText(item) }}</span>
            <small>{{ stateText(item) }}</small>
          </div>
          <input class="note-input" :value="item.note || ''" placeholder="备注" maxlength="200" @change="saveNote(item, $event)" />
          <div class="action-col">
            <button v-if="!item.owned" class="chip-button" type="button" :disabled="busy" @click="own(item)">登记一台</button>
            <span v-else class="owned-label">已拥有</span>
          </div>
        </div>
      </div>
      <div v-else class="state-panel">
        <Trophy :size="26" />
        <p>{{ stats.total ? '没有符合条件的目标。' : '范围还是空的。点右上角「添加目标」，从已录入的产品里选。' }}</p>
      </div>
    </template>

    <CollectionDialog :open="editOpen" :collection="collection" @close="editOpen = false" @saved="onCollectionSaved" />
    <CollectionItemDialog
      :open="addOpen"
      :collection-id="collectionId"
      :existing-ids="allProductIds"
      @close="addOpen = false"
      @added="onItemsAdded"
    />

    <p v-if="message" class="collection-message" :class="{ 'is-error': messageError }">{{ message }}</p>
  </section>
</template>

<style scoped>
.detail-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; margin-bottom: 22px; }
.back { margin-bottom: 10px; padding: 0; }
.title-row { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.title-row h1 { margin: 0; color: #172321; font-size: 28px; line-height: 1.25; }
.description { max-width: 760px; white-space: pre-wrap; }
.meta-line { display: flex; flex-wrap: wrap; gap: 14px; margin: 8px 0 0; color: #87938f; font-size: 12px; }
.header-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.status-pill { display: inline-block; padding: 3px 9px; font-size: 11px; border-radius: 999px; border: 1px solid #dfe6e1; }
.status-pill.planning { color: #4f5f8a; background: #eef3fb; border-color: #d3dff0; }
.status-pill.active { color: #1f5b4c; background: #e8f3ee; border-color: #c9e2d7; }
.status-pill.paused { color: #8a5f18; background: #fdf6e7; border-color: #f0dfb8; }
.status-pill.abandoned { color: #8a8f8c; background: #f3f3f1; border-color: #e2e2df; }
.completed-badge { padding: 3px 9px; color: #7a5312; font-size: 11px; font-weight: 600; background: #fdf3d9; border: 1px solid #ecd39b; border-radius: 999px; }
.progress-panel { padding: 20px; margin-bottom: 18px; background: #fafbf8; border: 1px solid #d9e1dc; border-radius: 8px; }
.progress-top { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 10px; }
.progress-top strong { color: #1b2925; font-size: 34px; line-height: 1; }
.progress-top div span { color: #6b7774; font-size: 14px; }
.percent { color: #24705f; font-size: 20px; font-weight: 600; }
.legend { display: flex; flex-wrap: wrap; gap: 10px 18px; margin-top: 12px; color: #52645e; font-size: 12px; }
.legend span { display: inline-flex; align-items: center; gap: 5px; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.dot.built { background: #1f6f5c; }
.dot.unbuilt { background: #8fc7b4; }
.dot.missing { background: #e6e9e6; border: 1px solid #cbd6d0; }
.progress-note { display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0 0; color: #6b7774; font-size: 12px; }
.filter-tabs { display: inline-flex; padding: 3px; background: #f1f5f2; border: 1px solid #dbe5df; border-radius: 999px; }
.filter-tabs button { padding: 5px 11px; color: #52645e; font-size: 12px; background: transparent; border: 0; border-radius: 999px; }
.filter-tabs button.active { color: #fff; background: #24705f; }
.action-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 9px 12px; margin-bottom: 12px; color: #52645e; font-size: 13px; background: #eef6f2; border: 1px solid #cfe3d9; border-radius: 6px; }
.chip-button { display: inline-flex; align-items: center; gap: 4px; padding: 5px 10px; color: #2f554c; font-size: 12px; background: #fff; border: 1px solid #cbd7d2; border-radius: 999px; }
.chip-button:hover { background: #f4f8f5; }
.chip-button.danger { color: #a4402c; border-color: #eccabf; }
.item-table { overflow: auto; background: #fff; border: 1px solid #d9e1dc; border-radius: 8px; }
.item-head, .item-row { display: grid; grid-template-columns: 34px minmax(220px, 1.4fr) 180px minmax(140px, 1fr) 104px; gap: 10px; align-items: center; min-width: 760px; padding: 10px 12px; }
.item-head { color: #6b7774; font-size: 12px; background: #fafbf8; border-bottom: 1px solid #e3e9e4; }
.item-row { color: #2c3b36; font-size: 13px; border-bottom: 1px solid #eff2ef; }
.item-row:last-child { border-bottom: 0; }
.item-row:hover { background: #f7faf7; }
.item-row.picked { background: #eef6f2; }
.check { display: grid; place-items: center; }
.item-main { display: grid; gap: 2px; min-width: 0; }
.item-main strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-main small, .item-status small { color: #87938f; font-size: 11px; }
.item-status { display: grid; justify-items: start; gap: 3px; }
.target-pill { display: inline-block; padding: 2px 8px; font-size: 11px; border-radius: 999px; border: 1px solid #dfe6e1; }
.target-pill.built { color: #1f5b4c; background: #e8f3ee; border-color: #c9e2d7; }
.target-pill.owned { color: #3f5f8a; background: #eef3fb; border-color: #d3dff0; }
.target-pill.missing { color: #8a5f18; background: #fdf6e7; border-color: #f0dfb8; }
.target-pill.sold { color: #8a8f8c; background: #f3f3f1; border-color: #e2e2df; }
.note-input { width: 100%; padding: 5px 7px; color: #2f554c; font-size: 12px; background: transparent; border: 1px solid transparent; border-radius: 4px; }
.note-input:hover { border-color: #dbe7e0; }
.note-input:focus { background: #fff; border-color: #24705f; outline: none; }
.action-col { display: flex; justify-content: flex-end; }
.owned-label { color: #87938f; font-size: 11px; }
.small { min-height: 120px; }
.collection-message { position: fixed; right: 28px; bottom: 28px; z-index: 60; padding: 10px 14px; color: #1f4a3c; font-size: 13px; background: #e8f5ec; border: 1px solid #b9d9c4; border-radius: 7px; box-shadow: 0 8px 24px #17352a1f; }
.collection-message.is-error { color: #8d3423; background: #fdeee9; border-color: #efc6ba; }
@media (max-width: 900px) {
  .detail-head { flex-direction: column; }
  .header-actions { justify-content: flex-start; }
}
@media (max-width: 650px) {
  .filter-tabs { width: 100%; justify-content: space-between; }
  .filter-tabs button { flex: 1; }
  .progress-top strong { font-size: 28px; }
}
</style>
