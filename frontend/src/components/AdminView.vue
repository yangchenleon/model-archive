<script setup>
import { computed, reactive, ref } from 'vue'
import {
  ArrowDown, ArrowUp, ChevronDown, Download, LoaderCircle, Pencil, Plus, RefreshCw, Save, Search, Trash2, X,
} from 'lucide-vue-next'
import ManufacturerPicker from './ManufacturerPicker.vue'
import { CHANNEL_OPTIONS, channelLabel } from '../taxonomy'

const SORT_FIELDS = [
  { key: 'manufacturer', label: '厂商' },
  { key: 'kit_name', label: '产品' },
  { key: 'product_code', label: '编号' },
  { key: 'product_line', label: '系列' },
  { key: 'release_channel', label: '渠道' },
  { key: 'price', label: '价格' },
  { key: 'created_at', label: '入库时间' },
]
const STATE_LABELS = { pending: '待审', mapped: '已映射', created: '已新建', skipped: '已跳过' }

const products = ref([])
const manufacturers = ref([])
const lines = ref([])
const loading = ref(true)
const error = ref('')
const search = ref('')
const busy = ref(false)
const message = ref('')
const messageError = ref(false)

const sortKey = ref('manufacturer')
const sortDirection = ref('asc')
const selectedIds = ref(new Set())
const bulkChannel = ref('')
const bulkApplying = ref(false)
const allVisibleSelected = computed(() => filtered.value.length > 0 && filtered.value.every((product) => selectedIds.value.has(product.id)))

const editorMode = ref(null) // 'create' | 'edit'
const editing = ref(null)
const detailProduct = ref(null)
const audit = ref([])
const auditLoading = ref(false)
const form = reactive({
  kit_name: '', manufacturer_id: '', product_code: '', product_line_id: '', release_channel: '', price: '', source: '', detail: '',
})

const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  const rows = term
    ? products.value.filter((product) =>
      [product.kit_name, product.manufacturer, product.product_code, product.product_line, channelLabel(product.release_channel), product.price]
        .filter(Boolean).join(' ').toLowerCase().includes(term))
    : products.value
  const direction = sortDirection.value === 'asc' ? 1 : -1
  return [...rows].sort((a, b) => {
    const left = sortKey.value === 'release_channel' ? channelLabel(a.release_channel) : (a[sortKey.value] ?? '')
    const right = sortKey.value === 'release_channel' ? channelLabel(b.release_channel) : (b[sortKey.value] ?? '')
    const result = String(left).localeCompare(String(right), 'zh-CN', { numeric: true, sensitivity: 'base' })
    return result * direction
  })
})

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `请求失败 (${response.status})`)
  }
  return response.status === 204 ? null : response.json()
}

function flash(text, isError = false) {
  message.value = text
  messageError.value = isError
  window.clearTimeout(flash.timer)
  flash.timer = window.setTimeout(() => { message.value = '' }, 3200)
}

async function loadProducts() {
  loading.value = true
  error.value = ''
  try {
    products.value = await api('/api/v1/products?limit=2000')
    selectedIds.value = new Set()
  } catch (exc) {
    error.value = `产品读取失败：${exc.message}`
  } finally {
    loading.value = false
  }
}

async function loadManufacturers() {
  try {
    manufacturers.value = await api('/api/v1/manufacturers?limit=500')
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
    lines.value = await api(`/api/v1/product-lines?manufacturer_id=${manufacturerId}&limit=500`)
  } catch {
    lines.value = []
  }
}

function onManufacturerChange() {
  form.product_line_id = ''
  loadLines(form.manufacturer_id)
}

function replaceProduct(updated) {
  const index = products.value.findIndex((item) => item.id === updated.id)
  if (index >= 0) products.value[index] = updated
}

function sortBy(key) {
  if (sortKey.value === key) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDirection.value = 'asc'
  }
}

function toggleAllVisible(event) {
  selectedIds.value = event.target.checked
    ? new Set(filtered.value.map((product) => product.id))
    : new Set()
}

function toggleOne(productId, event) {
  const next = new Set(selectedIds.value)
  if (event.target.checked) next.add(productId)
  else next.delete(productId)
  selectedIds.value = next
}

function clearSelection() {
  selectedIds.value = new Set()
}

async function applyBulkChannel() {
  if (!selectedIds.value.size || bulkApplying.value) return
  bulkApplying.value = true
  try {
    const ids = [...selectedIds.value]
    const channel = bulkChannel.value || null
    const result = await api('/api/v1/products/bulk-channel', {
      method: 'PATCH',
      body: JSON.stringify({ product_ids: ids, release_channel: channel }),
    })
    const selected = new Set(ids)
    products.value = products.value.map((product) =>
      selected.has(product.id) ? { ...product, release_channel: channel } : product
    )
    clearSelection()
    flash(`已更新 ${result.updated} 条渠道`)
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    bulkApplying.value = false
  }
}

function resetForm() {
  Object.assign(form, {
    kit_name: '', manufacturer_id: '', product_code: '', product_line_id: '', release_channel: '',
    price: '', source: '手动录入', detail: '',
  })
  lines.value = []
}

function openCreate() {
  detailProduct.value = null
  editorMode.value = 'create'
  editing.value = null
  audit.value = []
  resetForm()
}

function openDetail(product) {
  detailProduct.value = product
  editorMode.value = null
  editing.value = null
  audit.value = []
}

async function openEdit(product) {
  detailProduct.value = null
  editorMode.value = 'edit'
  editing.value = { ...product }
  Object.assign(form, {
    kit_name: product.kit_name || '',
    manufacturer_id: product.manufacturer_id || '',
    product_code: product.product_code || '',
    product_line_id: product.product_line_id || '',
    release_channel: product.release_channel || '',
    price: product.price || '',
    source: product.source || '',
    detail: product.detail || '',
  })
  await loadLines(form.manufacturer_id)
  audit.value = []
  auditLoading.value = true
  try {
    audit.value = await api(`/api/v1/products/${product.id}/review-items`)
  } catch {
    audit.value = []
  } finally {
    auditLoading.value = false
  }
}

function closeEditor() {
  detailProduct.value = null
  editorMode.value = null
  editing.value = null
  audit.value = []
}

function nullIfEmpty(value) {
  return value.trim() || null
}

function payload() {
  return {
    kit_name: form.kit_name.trim(),
    manufacturer_id: form.manufacturer_id || null,
    product_code: nullIfEmpty(form.product_code),
    product_line_id: form.product_line_id || null,
    release_channel: form.release_channel || null,
    price: nullIfEmpty(form.price),
    source: form.source.trim(),
    detail: nullIfEmpty(form.detail),
  }
}

async function saveProduct() {
  if (!editorMode.value || busy.value) return
  if (!form.kit_name.trim()) {
    flash('产品名称不能为空', true)
    return
  }
  if (!form.manufacturer_id) {
    flash('请选择厂商；没有就去「厂家管理」新建', true)
    return
  }
  if (!form.source.trim()) {
    flash('资料来源不能为空', true)
    return
  }
  busy.value = true
  try {
    if (editorMode.value === 'create') {
      const created = await api('/api/v1/products', { method: 'POST', body: JSON.stringify(payload()) })
      products.value.push(created)
      closeEditor()
      flash('产品已新增')
    } else {
      const updated = await api(`/api/v1/products/${editing.value.id}`, { method: 'PATCH', body: JSON.stringify(payload()) })
      replaceProduct(updated)
      closeEditor()
      flash('产品已保存')
    }
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

async function removeProduct() {
  if (editorMode.value !== 'edit' || !editing.value || busy.value) return
  const product = editing.value
  const linked = audit.value.length
  if (!window.confirm(`删除「${product.kit_name}」？\n\n关联的 ${linked} 条审核记录会退回待审队列，收藏集里的目标也会一起移除，产品字段会一并删除。`)) return
  busy.value = true
  try {
    const result = await api(`/api/v1/products/${product.id}`, { method: 'DELETE' })
    products.value = products.value.filter((item) => item.id !== product.id)
    closeEditor()
    flash(`已删除；${result.review_items_reset} 条审核记录已退回待审`)
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

function exportCsv() {
  const headers = ['厂商', '产品编号', '系列', '渠道', '模型名称', '价格', '资料来源', '详情', '入库时间', 'id']
  const escape = (value) => `"${String(value ?? '').replaceAll('"', '""')}"`
  const lines = [headers.join(',')]
  for (const product of filtered.value) {
    lines.push([
      product.manufacturer, product.product_code, product.product_line, channelLabel(product.release_channel), product.kit_name,
      product.price, product.source, product.detail, product.created_at, product.id,
    ].map(escape).join(','))
  }
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `products-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

function reviewLink(item) {
  return item.video_id ? `https://www.bilibili.com/video/${item.video_id}?t=${item.start_seconds || 0}` : ''
}

loadManufacturers()
loadProducts()
</script>

<template>
  <section class="admin-view">
    <header class="page-header">
      <div>
        <p class="eyebrow">后台管理</p>
        <h1>产品管理</h1>
        <p class="page-subtitle">新增、编辑或删除产品；删除时会把关联的审核记录退回待审，并从收藏集移除该目标。</p>
      </div>
      <div class="header-actions">
        <button class="secondary-button" type="button" :disabled="loading" @click="exportCsv"><Download :size="16" />导出 CSV</button>
        <button class="secondary-button" type="button" :disabled="loading" @click="loadProducts"><RefreshCw :size="16" />刷新</button>
        <button class="primary-button" type="button" @click="openCreate"><Plus :size="17" />新增产品</button>
      </div>
    </header>

    <section class="toolbar admin-toolbar">
      <label class="search-field"><Search :size="18" /><input v-model="search" type="search" placeholder="搜索名称 / 厂商 / 编号 / 系列" /></label>
      <span class="result-count">{{ filtered.length }} 项</span>
    </section>

    <section v-if="selectedIds.size" class="bulk-bar">
      <strong>已选 {{ selectedIds.size }} 项</strong>
      <span>批量设置渠道</span>
      <select v-model="bulkChannel">
        <option value="">未知</option>
        <option v-for="channel in CHANNEL_OPTIONS" :key="channel.value" :value="channel.value">{{ channel.label }}</option>
      </select>
      <button class="secondary-button" type="button" :disabled="bulkApplying" @click="applyBulkChannel">
        <LoaderCircle v-if="bulkApplying" class="spin" :size="15" />应用
      </button>
      <button class="text-button" type="button" :disabled="bulkApplying" @click="clearSelection">取消选择</button>
    </section>

    <section v-if="loading" class="state-panel"><LoaderCircle class="spin" :size="24" /><p>正在读取产品…</p></section>
    <section v-else-if="error" class="state-panel error-state"><p>{{ error }}</p><button class="secondary-button" type="button" @click="loadProducts">重新加载</button></section>
    <section v-else class="admin-table-wrap">
      <table class="admin-table">
        <thead>
          <tr>
            <th class="check-cell"><input type="checkbox" :checked="allVisibleSelected" aria-label="全选当前筛选结果" @change="toggleAllVisible" /></th>
            <th v-for="field in SORT_FIELDS" :key="field.key" @click="sortBy(field.key)">
              <span class="th-inner">
                {{ field.label }}
                <ArrowUp v-if="sortKey === field.key && sortDirection === 'asc'" :size="12" />
                <ArrowDown v-else-if="sortKey === field.key && sortDirection === 'desc'" :size="12" />
                <ChevronDown v-else :size="12" class="muted" />
              </span>
            </th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="product in filtered" :key="product.id" @click="openDetail(product)">
            <td class="check-cell"><input type="checkbox" :checked="selectedIds.has(product.id)" :aria-label="`选择 ${product.kit_name}`" @click.stop @change="toggleOne(product.id, $event)" /></td>
            <td>{{ product.manufacturer || '—' }}</td>
            <td class="name">{{ product.kit_name }}</td>
            <td class="code">{{ product.product_code || '—' }}</td>
            <td>{{ product.product_line || '—' }}</td>
            <td>{{ channelLabel(product.release_channel) }}</td>
            <td class="price">{{ product.price || '—' }}</td>
            <td class="date">{{ (product.created_at || '').slice(0, 10) }}</td>
            <td class="row-actions"><button class="icon-button" type="button" aria-label="编辑" @click.stop="openEdit(product)"><Pencil :size="15" /></button></td>
          </tr>
        </tbody>
      </table>
      <p v-if="!filtered.length" class="empty-state">没有匹配的产品。</p>
    </section>

    <Transition name="dialog">
      <div v-if="detailProduct || editorMode" class="dialog-layer">
        <section class="admin-dialog" :aria-label="detailProduct ? '产品详情' : '产品编辑'">
          <header>
            <div>
              <span class="eyebrow">{{ detailProduct ? '产品详情' : editorMode === 'create' ? '新增产品' : '编辑产品' }}</span>
              <h2>{{ detailProduct ? detailProduct.kit_name : editorMode === 'create' ? '手工录入' : editing?.kit_name }}</h2>
            </div>
            <button class="icon-button" type="button" aria-label="关闭" @click="closeEditor"><X :size="20" /></button>
          </header>

          <template v-if="detailProduct">
            <p class="detail-hint">只读查看；需要修改时关闭弹窗，点列表右侧的铅笔。</p>
            <dl class="detail-grid">
              <div><dt>厂商</dt><dd>{{ detailProduct.manufacturer || '—' }}</dd></div>
              <div><dt>产品编号</dt><dd>{{ detailProduct.product_code || '—' }}</dd></div>
              <div><dt>产品名称</dt><dd>{{ detailProduct.kit_name }}</dd></div>
              <div><dt>系列</dt><dd>{{ detailProduct.product_line || '未知' }}</dd></div>
              <div><dt>渠道</dt><dd>{{ channelLabel(detailProduct.release_channel) }}</dd></div>
              <div><dt>价格</dt><dd>{{ detailProduct.price || '—' }}</dd></div>
              <div><dt>入库时间</dt><dd>{{ (detailProduct.created_at || '').slice(0, 10) }}</dd></div>
              <div class="full"><dt>资料来源</dt><dd class="detail-text">{{ detailProduct.source || '—' }}</dd></div>
              <div class="full"><dt>详情</dt><dd class="detail-text">{{ detailProduct.detail || '—' }}</dd></div>
            </dl>
            <footer class="admin-footer">
              <span></span>
              <div>
                <button class="text-button" type="button" @click="closeEditor">关闭</button>
              </div>
            </footer>
          </template>

          <template v-else>
            <div class="admin-form">
              <label><span>厂商 <b>*</b></span>
                <ManufacturerPicker
                  v-model="form.manufacturer_id"
                  :manufacturers="manufacturers"
                  @change="onManufacturerChange"
                />
              </label>
              <label><span>产品编号</span><input v-model="form.product_code" placeholder="RG32 / MDH-12E" /></label>
              <label class="full"><span>产品名称 <b>*</b></span><input v-model="form.kit_name" /></label>
              <label><span>系列</span>
                <select v-model="form.product_line_id">
                  <option value="">未知</option>
                  <option v-for="line in lines" :key="line.id" :value="line.id">{{ line.name }}</option>
                </select>
              </label>
              <label><span>渠道</span>
                <select v-model="form.release_channel">
                  <option value="">未知</option>
                  <option v-for="channel in CHANNEL_OPTIONS" :key="channel.value" :value="channel.value">{{ channel.label }}</option>
                </select>
              </label>
              <label><span>价格</span><input v-model="form.price" placeholder="自由文本：78 / 68元 / 22000日元" /></label>
              <label class="full"><span>资料来源 <b>*</b></span><input v-model="form.source" /></label>
              <label class="full"><span>详情</span><textarea v-model="form.detail" rows="3"></textarea></label>
            </div>

            <section v-if="editorMode === 'edit'" class="audit-section">
              <header class="audit-head">
                <h3>关联审核记录（{{ audit.length }}）</h3>
                <span class="audit-hint">这条产品由哪些 mention 来、怎么处理的</span>
              </header>
              <p v-if="auditLoading" class="audit-empty"><LoaderCircle class="spin" :size="16" />读取中…</p>
              <p v-else-if="!audit.length" class="audit-empty">没有关联的审核记录（手工录入或来源已清理）。</p>
              <ul v-else class="audit-list">
                <li v-for="item in audit" :key="item.id">
                  <span class="audit-date">{{ item.event_date }}</span>
                  <span class="audit-state">{{ STATE_LABELS[item.state] || item.state }}</span>
                  <span class="audit-brand">{{ item.brand || '未知厂商' }}</span>
                  <span class="audit-product">{{ item.product }}</span>
                  <a v-if="reviewLink(item)" class="audit-link" :href="reviewLink(item)" target="_blank" rel="noopener">▶ 原视频</a>
                </li>
              </ul>
            </section>

            <footer class="admin-footer">
              <button v-if="editorMode === 'edit'" class="text-button danger-text" type="button" :disabled="busy" @click="removeProduct"><Trash2 :size="16" />删除产品</button>
              <span v-else></span>
              <div>
                <button class="text-button" type="button" @click="closeEditor">取消</button>
                <button class="primary-button" type="button" :disabled="busy" @click="saveProduct"><Save :size="16" />{{ editorMode === 'create' ? '创建产品' : '保存产品' }}</button>
              </div>
            </footer>
          </template>
        </section>
      </div>
    </Transition>

    <p v-if="message" class="admin-message" :class="{ 'is-error': messageError }">{{ message }}</p>
  </section>
</template>

<style scoped>
.header-actions { display: flex; gap: 8px; }
.admin-toolbar { margin-bottom: 16px; }
.bulk-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding: 10px 12px; margin-bottom: 12px; color: #24574d; font-size: 13px; background: #eef6f2; border: 1px solid #c9e2d7; border-radius: 7px; }
.bulk-bar select { padding: 6px 8px; color: #22302b; background: #fff; border: 1px solid #cfd9d4; border-radius: 5px; }
.admin-table .check-cell { width: 34px; padding-right: 4px; padding-left: 12px; }
.admin-table .check-cell input { width: 14px; height: 14px; accent-color: #24705f; }
.admin-table-wrap { overflow: auto; background: #fff; border: 1px solid #d9e1dc; border-radius: 8px; }
.admin-table { width: 100%; min-width: 980px; border-collapse: collapse; font-size: 13px; }
.admin-table th { position: sticky; top: 0; padding: 10px 12px; color: #6b7774; font-size: 12px; font-weight: 500; text-align: left; background: #fafbf8; border-bottom: 1px solid #e3e9e4; cursor: pointer; user-select: none; }
.admin-table th:hover { color: #24574d; }
.th-inner { display: inline-flex; align-items: center; gap: 3px; }
.th-inner .muted { color: #c3ccc7; }
.admin-table td { padding: 10px 12px; color: #2c3b36; border-bottom: 1px solid #eff2ef; }
.admin-table tbody tr { cursor: pointer; }
.admin-table tbody tr:hover { background: #f7faf7; }
.admin-table .name { font-weight: 600; }
.admin-table .code, .admin-table .price, .admin-table .date { font-variant-numeric: tabular-nums; }
.admin-table .row-actions { text-align: right; }
.empty-state { padding: 32px; color: #98a39f; text-align: center; }

.dialog-layer { position: fixed; z-index: 40; inset: 0; display: flex; align-items: center; justify-content: center; padding: 20px; background: #13201c66; }
.admin-dialog { width: min(100%, 780px); max-height: 90vh; padding: 22px; overflow: auto; background: #fff; border: 1px solid #dae3de; border-radius: 8px; box-shadow: 0 18px 54px #17271f35; }
.admin-dialog > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.admin-dialog h2 { margin: 4px 0 0; color: #1b2925; font-size: 20px; }
.admin-form { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 18px 0; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; margin: 18px 0; overflow: hidden; background: #e7ece8; border: 1px solid #e0e7e2; border-radius: 7px; }
.detail-grid > div { min-width: 0; padding: 11px 13px; background: #fff; }
.detail-grid > div.full { grid-column: 1 / -1; }
.detail-grid dt { margin: 0 0 4px; color: #87938f; font-size: 11px; }
.detail-grid dd { margin: 0; color: #22302b; font-size: 13px; }
.detail-grid dd.detail-text { white-space: pre-wrap; word-break: break-word; line-height: 1.65; }
.detail-hint { margin: 14px 0 -4px; color: #87938f; font-size: 12px; }
.admin-form label { display: grid; gap: 5px; color: #5d6d67; font-size: 12px; }
.admin-form label.full { grid-column: 1 / -1; }
.admin-form label b { color: #bb563b; }
.admin-form input, .admin-form select, .admin-form textarea { width: 100%; padding: 8px 10px; color: #22302b; background: #fbfcfa; border: 1px solid #cfd9d4; border-radius: 5px; outline: none; }
.admin-form input:focus, .admin-form select:focus, .admin-form textarea:focus { background: #fff; border-color: #59877b; }

.audit-section { padding-top: 14px; border-top: 1px solid #e7ece8; }
.audit-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
.audit-head h3 { margin: 0; color: #2c4038; font-size: 14px; }
.audit-hint { color: #98a39f; font-size: 11px; }
.audit-list { display: grid; gap: 4px; margin: 10px 0 0; padding: 0; list-style: none; }
.audit-list li { display: flex; align-items: baseline; gap: 8px; padding: 7px 9px; font-size: 12px; color: #5d6d67; background: #fafbf8; border: 1px solid #eef1ee; border-radius: 5px; }
.audit-date { font-variant-numeric: tabular-nums; color: #7a8782; }
.audit-state { padding: 1px 7px; font-size: 11px; border-radius: 999px; border: 1px solid #d5ddd8; background: #fff; }
.audit-brand { font-weight: 600; color: #445751; }
.audit-product { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.audit-link { margin-left: auto; color: #24705f; font-size: 11px; text-decoration: none; }
.audit-empty { display: flex; align-items: center; gap: 6px; margin: 10px 0 0; color: #98a39f; font-size: 12px; }

.admin-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 18px; padding-top: 14px; border-top: 1px solid #e7ece8; }
.admin-footer > div { display: flex; gap: 8px; }
.danger-text { color: #a4402c; }
.danger-text:hover { background: #fbeeea; }
.admin-message { position: fixed; right: 28px; bottom: 28px; padding: 11px 16px; color: #1f4a3c; font-size: 13px; background: #e8f5ec; border: 1px solid #b9d9c4; border-radius: 7px; box-shadow: 0 8px 24px #17352a1f; }
.admin-message.is-error { color: #8d3423; background: #fdeee9; border-color: #efc6ba; }
.dialog-enter-active, .dialog-leave-active { transition: opacity .2s ease; }
.dialog-enter-from, .dialog-leave-to { opacity: 0; }
@media (max-width: 720px) {
  .admin-form { grid-template-columns: 1fr; }
  .header-actions { flex-wrap: wrap; }
}
</style>
