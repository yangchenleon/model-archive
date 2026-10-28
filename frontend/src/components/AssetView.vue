<script setup>
import { computed, onMounted, ref } from 'vue'
import { Boxes, LoaderCircle, Plus, Printer, RefreshCw, Search, Trash2 } from 'lucide-vue-next'
import AssetDialog from './AssetDialog.vue'
import AssetAddDialog from './AssetAddDialog.vue'

const STATE_META = {
  pending: { label: '待拼', hint: '买了没动' },
  keep: { label: '收藏', hint: '不打算拼' },
  displayed: { label: '展示', hint: '已拼，摆着' },
  stored: { label: '收纳', hint: '已拼，封袋' },
  sold: { label: '卖出', hint: '已出手' },
}
const STATE_ORDER = ['pending', 'keep', 'displayed', 'stored', 'sold']

const assets = ref([])
const loading = ref(true)
const error = ref('')
const search = ref('')
const stateFilter = ref('')
const selected = ref([])
const busy = ref(false)
const message = ref('')
const messageError = ref(false)
const detail = ref(null)
const addOpen = ref(false)

const counts = computed(() => {
  const base = { all: assets.value.length }
  for (const state of STATE_ORDER) base[state] = 0
  for (const asset of assets.value) base[asset.state] = (base[asset.state] || 0) + 1
  return base
})

const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  return assets.value.filter((asset) => {
    if (stateFilter.value && asset.state !== stateFilter.value) return false
    if (!term) return true
    return [asset.code, asset.product?.kit_name, asset.product?.manufacturer, asset.product?.product_line]
      .filter(Boolean).join(' ').toLowerCase().includes(term)
  })
})

const selectedSet = computed(() => new Set(selected.value))
const allChecked = computed(() => filtered.value.length > 0 && filtered.value.every((a) => selectedSet.value.has(a.id)))

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

async function loadAssets() {
  loading.value = true
  error.value = ''
  try {
    assets.value = await api('/api/v1/assets?limit=500')
  } catch (exc) {
    error.value = `资产读取失败：${exc.message}`
  } finally {
    loading.value = false
  }
}

async function jumpToCode() {
  const raw = search.value.trim()
  if (!raw) return
  try {
    detail.value = await api(`/api/v1/assets/by-code/${encodeURIComponent(raw)}`)
  } catch {
    /* 不是编号就继续当普通搜索用 */
  }
}

function toggleAsset(id) {
  const index = selected.value.indexOf(id)
  if (index >= 0) selected.value.splice(index, 1)
  else selected.value.push(id)
}

function toggleAll() {
  selected.value = allChecked.value ? [] : filtered.value.map((asset) => asset.id)
}

async function bulkState(state) {
  if (!selected.value.length || busy.value) return
  busy.value = true
  try {
    const result = await api('/api/v1/assets/bulk/state', {
      method: 'POST',
      body: JSON.stringify({ asset_ids: selected.value, state }),
    })
    await loadAssets()
    flash(`${result.updated} 项，${result.changed} 项改为「${STATE_META[state].label}」`)
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

async function issueTags() {
  if (!selected.value.length || busy.value) return
  busy.value = true
  try {
    const created = await api('/api/v1/assets/bulk/tags', {
      method: 'POST',
      body: JSON.stringify({ asset_ids: selected.value, title: '本体' }),
    })
    flash(`已放入待打印队列：${created.length} 张，去「标签队列」打印`)
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

async function removeSelected() {
  if (!selected.value.length || busy.value) return
  if (!window.confirm(`删除 ${selected.value.length} 条资产？编号不会回收。`)) return
  busy.value = true
  try {
    for (const id of selected.value) await api(`/api/v1/assets/${id}`, { method: 'DELETE' })
    selected.value = []
    await loadAssets()
    flash('已删除')
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

function onSaved(updated) {
  const index = assets.value.findIndex((item) => item.id === updated.id)
  if (index >= 0) assets.value[index] = updated
  detail.value = updated
}

function onRemoved(id) {
  assets.value = assets.value.filter((item) => item.id !== id)
  selected.value = selected.value.filter((value) => value !== id)
}

function onCreated(result) {
  loadAssets()
  flash(`已加入 ${result.assets.length} 项（${STATE_META[result.state].label}）`)
}

onMounted(loadAssets)
</script>

<template>
  <section class="asset-view">
    <header class="page-header">
      <div>
        <p class="eyebrow">资产管理</p>
        <h1>我的模型</h1>
        <p class="page-subtitle">一台一份记录。标签是另一件事：在「标签队列」里生成、打印。</p>
      </div>
      <div class="header-actions">
        <button class="secondary-button" type="button" :disabled="loading" @click="loadAssets"><RefreshCw :size="16" />刷新</button>
        <button class="primary-button" type="button" @click="addOpen = true"><Plus :size="17" />添加资产</button>
      </div>
    </header>

    <section class="overview-row asset-metrics" aria-label="资产概要">
      <button v-for="state in STATE_ORDER" :key="state" class="metric" type="button" :class="{ active: stateFilter === state }" @click="stateFilter = stateFilter === state ? '' : state">
        <span>{{ STATE_META[state].label }}</span>
        <strong>{{ counts[state] || 0 }}</strong>
        <small>{{ STATE_META[state].hint }}</small>
      </button>
    </section>

    <section class="toolbar">
      <label class="search-field"><Search :size="18" /><input v-model="search" type="search" placeholder="搜索编号、模型名、厂商（回车按编号直达）" @keyup.enter="jumpToCode" /></label>
      <button v-if="stateFilter" class="reset-button" type="button" @click="stateFilter = ''">全部（{{ counts.all }}）</button>
      <span class="result-count">{{ selected.length ? `已选 ${selected.length} 项` : `${filtered.length} 项` }}</span>
    </section>

    <section v-if="selected.length" class="action-bar">
      <span>设为</span>
      <button v-for="state in STATE_ORDER" :key="state" class="chip-button" type="button" :disabled="busy" @click="bulkState(state)">{{ STATE_META[state].label }}</button>
      <span class="divider"></span>
      <button class="chip-button" type="button" :disabled="busy" @click="issueTags"><Printer :size="14" />生成标签</button>
      <button class="chip-button danger" type="button" :disabled="busy" @click="removeSelected"><Trash2 :size="14" />删除</button>
    </section>

    <p v-if="loading" class="state-panel"><LoaderCircle class="spin" :size="24" />正在读取资产…</p>
    <p v-else-if="error" class="state-panel error-state">{{ error }}</p>
    <div v-else-if="filtered.length" class="asset-table-wrap">
      <table class="asset-table">
        <thead>
          <tr>
            <th class="check"><input type="checkbox" :checked="allChecked" @change="toggleAll" /></th>
            <th>编号</th>
            <th>产品</th>
            <th>状态</th>
            <th>拼装</th>
            <th class="num">评分</th>
            <th class="num">买入</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="asset in filtered" :key="asset.id" :class="{ picked: selectedSet.has(asset.id) }">
            <td class="check" @click.stop><input type="checkbox" :checked="selectedSet.has(asset.id)" @change="toggleAsset(asset.id)" /></td>
            <td class="code" @click="detail = asset">{{ asset.code }}</td>
            <td class="name" @click="detail = asset">
              <strong>{{ asset.product?.kit_name || '—' }}</strong>
              <small>{{ [asset.product?.manufacturer, asset.product?.product_line].filter(Boolean).join(' · ') }}</small>
            </td>
            <td @click="detail = asset"><span class="state-pill" :class="asset.state">{{ STATE_META[asset.state]?.label || asset.state }}</span></td>
            <td class="date" @click="detail = asset">{{ asset.built_on || '—' }}</td>
            <td class="num" @click="detail = asset">{{ asset.rating ? '★'.repeat(asset.rating) : '—' }}</td>
            <td class="num" @click="detail = asset">{{ asset.purchase_price ?? '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="state-panel">
      <Boxes :size="26" />
      <p>{{ assets.length ? '没有符合条件的资产。' : '还没有资产。点右上角「添加资产」从产品库里选。' }}</p>
    </div>

    <AssetAddDialog :open="addOpen" @close="addOpen = false" @created="onCreated" />
    <AssetDialog :asset="detail" @close="detail = null" @saved="onSaved" @removed="onRemoved" />

    <p v-if="message" class="asset-message" :class="{ 'is-error': messageError }">{{ message }}</p>
  </section>
</template>

<style scoped>
.header-actions { display: flex; gap: 8px; }
.asset-metrics { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.asset-metrics .metric { text-align: left; background: transparent; border: 0; border-right: 1px solid #dfe5e1; cursor: pointer; }
.asset-metrics .metric:last-child { border-right: 0; }
.asset-metrics .metric:hover { background: #f2f7f3; }
.asset-metrics .metric.active { background: #eaf3ee; box-shadow: inset 0 -2px 0 #24705f; }
.reset-button { color: #24574d; font-weight: 600; }
.action-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; padding: 9px 12px; margin-bottom: 12px; color: #52645e; font-size: 13px; background: #eef6f2; border: 1px solid #cfe3d9; border-radius: 6px; }
.chip-button { display: inline-flex; align-items: center; gap: 4px; padding: 5px 10px; color: #2f554c; font-size: 12px; background: #fff; border: 1px solid #cbd7d2; border-radius: 999px; }
.chip-button:hover { background: #f4f8f5; }
.chip-button.danger { color: #a4402c; border-color: #eccabf; }
.divider { width: 1px; height: 18px; margin: 0 4px; background: #cfe3d9; }
.asset-table-wrap { overflow: auto; background: #fff; border: 1px solid #d9e1dc; border-radius: 8px; }
.asset-table { width: 100%; min-width: 820px; border-collapse: collapse; font-size: 13px; }
.asset-table th { position: sticky; top: 0; padding: 9px 12px; color: #6b7774; font-size: 12px; font-weight: 500; text-align: left; background: #fafbf8; border-bottom: 1px solid #e3e9e4; }
.asset-table td { padding: 9px 12px; color: #2c3b36; border-bottom: 1px solid #eff2ef; cursor: pointer; }
.asset-table tbody tr:hover { background: #f7faf7; }
.asset-table tbody tr.picked { background: #eef6f2; }
.asset-table .check { width: 34px; cursor: default; }
.asset-table .code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: #1f332c; white-space: nowrap; }
.asset-table .name { display: grid; gap: 2px; }
.asset-table .name strong { font-weight: 600; }
.asset-table .name small { color: #87938f; font-size: 11px; }
.asset-table .num, .asset-table .date { font-variant-numeric: tabular-nums; white-space: nowrap; }
.asset-table .num { text-align: right; color: #9a6a1f; }
.state-pill { display: inline-block; padding: 2px 8px; font-size: 11px; border-radius: 999px; border: 1px solid #dfe6e1; }
.state-pill.pending { color: #8a5f18; background: #fdf6e7; border-color: #f0dfb8; }
.state-pill.keep { color: #3f5f8a; background: #eef3fb; border-color: #d3dff0; }
.state-pill.displayed { color: #1f5b4c; background: #e8f3ee; border-color: #c9e2d7; }
.state-pill.stored { color: #4f5f5a; background: #eef1ef; border-color: #d9e0dc; }
.state-pill.sold { color: #8a8f8c; background: #f3f3f1; border-color: #e2e2df; }
.state-panel { display: flex; align-items: center; justify-content: center; gap: 10px; min-height: 220px; color: #6d7b77; background: #fafbf8; border: 1px dashed #cbd6d0; border-radius: 8px; }
.state-panel.error-state { color: #9a452f; }
.asset-message { position: fixed; right: 28px; bottom: 28px; padding: 10px 14px; color: #1f4a3c; font-size: 13px; background: #e8f5ec; border: 1px solid #b9d9c4; border-radius: 7px; box-shadow: 0 8px 24px #17352a1f; }
.asset-message.is-error { color: #8d3423; background: #fdeee9; border-color: #efc6ba; }
@media (max-width: 900px) {
  .asset-metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
</style>
