<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ArrowLeft, Building2, Filter, Grid2X2, List, LoaderCircle, Plus, RefreshCw, Search, X } from 'lucide-vue-next'
import SidebarNav from './components/SidebarNav.vue'
import ProductCard from './components/ProductCard.vue'
import ProductDrawer from './components/ProductDrawer.vue'
import AddProductDialog from './components/AddProductDialog.vue'
import ReviewView from './components/ReviewView.vue'
import AdminView from './components/AdminView.vue'
import AssetView from './components/AssetView.vue'
import LabelsView from './components/LabelsView.vue'
import PrintView from './components/PrintView.vue'
import CollectionsView from './components/CollectionsView.vue'
import CollectionDetail from './components/CollectionDetail.vue'
import TaxonomyAdmin from './components/TaxonomyAdmin.vue'
import { categoryLabel, categoryOrder, fetchManufacturers } from './taxonomy'

const SECTIONS = ['directory', 'review', 'admin', 'taxonomy', 'inventory', 'collections', 'labels', 'print', 'wishlist', 'activity']
const activeSection = ref('directory')
const collectionId = ref('')
const directoryMaker = ref('')
const selectedProduct = ref(null)

function decodeHash(value) {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

function applyRoute() {
  const [section, rawId = ''] = window.location.hash.replace('#', '').split('/')
  activeSection.value = SECTIONS.includes(section) ? section : 'directory'
  collectionId.value = section === 'collections' ? rawId : ''
  directoryMaker.value = section === 'directory' ? decodeHash(rawId) : ''
  selectedProduct.value = null
}

function setRoute(section, id = '') {
  const target = section === 'directory'
    ? (id ? `directory/${id}` : '')
    : (id ? `${section}/${id}` : section)
  if (window.location.hash.replace('#', '') === target) applyRoute()
  else window.location.hash = target
}

function navigate(section) {
  selectedProduct.value = null
  setRoute(section)
}

function openCollection(id) {
  selectedProduct.value = null
  setRoute('collections', id)
}

function backToCollections() {
  setRoute('collections')
}

applyRoute()
window.addEventListener('hashchange', applyRoute)
const products = ref([])
const manufacturers = ref([])
const loading = ref(true)
const loadError = ref('')
const search = ref('')
const lineFilter = ref('')
const makerFilter = ref('')
const view = ref('grid')
const addDialogOpen = ref(false)
const reviewPending = ref(0)
const assets = ref([])
const toast = ref('')
const toastError = ref(false)
const makerSearch = ref('')
const makerSort = ref('taxonomy')
const categoryFilter = ref('')

function makerName(product) {
  return product.manufacturer || '未标注厂商'
}

async function loadReviewPending() {
  try {
    const response = await fetch('/api/v1/review/stats')
    if (response.ok) reviewPending.value = (await response.json()).pending
  } catch {
    /* badge is best-effort */
  }
}

async function loadManufacturers() {
  try {
    manufacturers.value = await fetchManufacturers()
  } catch {
    manufacturers.value = []
  }
}

const manufacturerById = computed(() => new Map(manufacturers.value.map((row) => [row.id, row])))
const manufacturerByName = computed(() => new Map(manufacturers.value.map((row) => [row.name, row])))

const makers = computed(() => [...new Set(products.value.map(makerName))].sort((a, b) => a.localeCompare(b, 'zh-CN')))

// 厂商选定后，系列栏仅可选厂商所存在的系列，而非全局
const productLines = computed(() => {
  const sourceList = makerFilter.value
    ? products.value.filter((item) => makerName(item) === makerFilter.value)
    : products.value
  return [...new Set(sourceList.map((item) => item.product_line || '未知'))].sort((a, b) => a.localeCompare(b, 'zh-CN'))
})

// 如果先选系列，再选厂商的话，则产品恢复全局筛选（清空已选系列）
watch(makerFilter, () => {
  lineFilter.value = ''
})

const selectedMaker = computed(() => (directoryMaker.value && directoryMaker.value !== 'all' ? directoryMaker.value : ''))
const browseAll = computed(() => directoryMaker.value === 'all')
const isMakerLanding = computed(() => !directoryMaker.value)
const selectedMakerId = computed(() => (selectedMaker.value ? manufacturerByName.value.get(selectedMaker.value)?.id || '' : ''))

const makerGroups = computed(() => {
  const groups = new Map()
  for (const product of products.value) {
    const key = product.manufacturer_id || makerName(product)
    if (!groups.has(key)) {
      const meta = manufacturerById.value.get(product.manufacturer_id)
      groups.set(key, {
        id: key,
        name: meta?.name || makerName(product),
        category: meta?.category || null,
        tier: meta?.tier || 3,
        sort_order: meta?.sort_order || 0,
        count: 0,
        lines: new Map(),
        samples: [],
      })
    }
    const group = groups.get(key)
    group.count += 1
    const lineName = product.product_line || '未知'
    group.lines.set(lineName, (group.lines.get(lineName) || 0) + 1)
    if (group.samples.length < 3) group.samples.push(product.kit_name)
  }
  return [...groups.values()].map((group) => {
    const lines = [...group.lines.entries()]
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'zh-CN'))
      .map(([name]) => name)
    return {
      ...group,
      lineCount: group.lines.size,
      lines: lines.slice(0, 3),
    }
  })
})

const filteredMakers = computed(() => {
  const term = makerSearch.value.trim().toLowerCase()
  return makerGroups.value
    .filter((maker) => {
      if (categoryFilter.value === 'unclassified' && maker.category !== null) return false
      if (categoryFilter.value && categoryFilter.value !== 'unclassified' && maker.category !== categoryFilter.value) return false
      return !term || maker.name.toLowerCase().includes(term)
    })
    .slice()
    .sort((a, b) => {
      if (makerSort.value === 'name') return a.name.localeCompare(b.name, 'zh-CN')
      if (makerSort.value === 'count') return b.count - a.count || a.name.localeCompare(b.name, 'zh-CN')
      return categoryOrder(a.category) - categoryOrder(b.category)
        || a.tier - b.tier
        || a.sort_order - b.sort_order
        || b.count - a.count
        || a.name.localeCompare(b.name, 'zh-CN')
    })
})

const makerProductCount = computed(() => {
  if (!selectedMaker.value) return products.value.length
  return products.value.filter((product) => makerName(product) === selectedMaker.value).length
})

const makerLineGroups = computed(() => {
  if (!selectedMaker.value) return []
  const counts = new Map()
  for (const product of products.value) {
    if (makerName(product) !== selectedMaker.value) continue
    const lineName = product.product_line || '未知'
    counts.set(lineName, (counts.get(lineName) || 0) + 1)
  }
  return [...counts.entries()]
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, 'zh-CN'))
})

// 给厂牌卡一个稳定的色块，避免 86 张卡全是同一种灰。
function makerTint(name) {
  let hash = 0
  for (const char of name) hash = (hash * 31 + char.codePointAt(0)) % 6
  return `tint-${hash}`
}

function enterMaker(name) {
  setRoute('directory', encodeURIComponent(name))
}

function browseAllProducts() {
  setRoute('directory', 'all')
}

function backToMakers() {
  setRoute('directory')
}

watch(directoryMaker, (maker) => {
  if (activeSection.value !== 'directory') return
  makerFilter.value = maker && maker !== 'all' ? maker : ''
  lineFilter.value = ''
  search.value = ''
}, { immediate: true })

watch(activeSection, (section) => {
  if (section === 'directory') {
    loadManufacturers()
    loadProducts()
  }
  if (section === 'directory' && !directoryMaker.value) {
    makerFilter.value = ''
    lineFilter.value = ''
    search.value = ''
  }
})

const filteredProducts = computed(() => {
  const keyword = search.value.trim().toLocaleLowerCase()
  return products.value
    .filter((item) => {
      const lineName = item.product_line || '未知'
      const matchText = !keyword || [item.kit_name, item.manufacturer, item.product_code, lineName].filter(Boolean).join(' ').toLocaleLowerCase().includes(keyword)
      return matchText && (!makerFilter.value || makerName(item) === makerFilter.value) && (!lineFilter.value || lineName === lineFilter.value)
    })
    .slice()
    .sort((a, b) => {
      // 1. 按照厂商排序
      const makerA = a.manufacturer || ''
      const makerB = b.manufacturer || ''
      if (makerA !== makerB) {
        if (!makerA) return 1
        if (!makerB) return -1
        const makerDiff = makerA.localeCompare(makerB, 'zh-CN')
        if (makerDiff !== 0) return makerDiff
      }

      // 2. 按照系列排序
      const lineA = a.product_line || ''
      const lineB = b.product_line || ''
      if (lineA !== lineB) {
        if (!lineA) return 1
        if (!lineB) return -1
        const lineDiff = lineA.localeCompare(lineB, 'zh-CN')
        if (lineDiff !== 0) return lineDiff
      }

      // 3. 按照编号自然数字排序
      const codeA = a.product_code || ''
      const codeB = b.product_code || ''
      if (codeA !== codeB) {
        if (!codeA) return 1
        if (!codeB) return -1
        const codeDiff = codeA.localeCompare(codeB, undefined, { numeric: true, sensitivity: 'base' })
        if (codeDiff !== 0) return codeDiff
      }

      // 4. 名称排序兜底
      return (a.kit_name || '').localeCompare(b.kit_name || '', 'zh-CN')
    })
})

async function loadProducts() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await fetch('/api/v1/products?limit=2000')
    if (!response.ok) throw new Error('产品目录请求失败')
    products.value = await response.json()
  } catch {
    loadError.value = '产品目录暂时无法连接。请确认 API 与数据库服务已经启动。'
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  search.value = ''
  lineFilter.value = ''
  if (!selectedMaker.value) makerFilter.value = ''
}

function flash(text, isError = false) {
  toast.value = text
  toastError.value = isError
  window.clearTimeout(flash.timer)
  flash.timer = window.setTimeout(() => { toast.value = '' }, 3000)
}

async function loadAssets() {
  try {
    const response = await fetch('/api/v1/assets?limit=500')
    if (response.ok) assets.value = await response.json()
  } catch {
    /* 卡片上的“已入”只是提示，失败不阻塞目录 */
  }
}

const ownedByProduct = computed(() => {
  const counts = new Map()
  for (const asset of assets.value) {
    counts.set(asset.product_id ?? asset.product?.id, (counts.get(asset.product_id ?? asset.product?.id) || 0) + 1)
  }
  return counts
})

async function ownProduct(product) {
  try {
    const response = await fetch('/api/v1/assets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: product.id, state: 'pending' }),
    })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(body.detail || `请求失败 (${response.status})`)
    assets.value.push(body)
    flash(`${product.kit_name} → ${body.code}（待拼）`)
  } catch (exc) {
    flash(exc.message, true)
  }
}

function onCreated(product) {
  products.value.push(product)
  selectedProduct.value = product
}

onMounted(() => {
  loadProducts()
  loadManufacturers()
  loadAssets()
  loadReviewPending()
})
</script>

<template>
  <PrintView v-if="activeSection === 'print'" />
  <div v-else class="app-shell">
    <SidebarNav :active="activeSection" :total="products.length" :pending="reviewPending" @change="navigate" />

    <main class="content">
      <section v-if="activeSection === 'directory'" class="directory-view">
        <template v-if="isMakerLanding">
          <header class="page-header">
            <div>
              <p class="eyebrow">产品资料库</p>
              <h1>厂家目录</h1>
              <p class="page-subtitle">先选厂牌，再看产品。当前按厂名归并，系列只做厂牌内的次级筛选。</p>
            </div>
            <div class="header-actions">
              <button class="secondary-button" type="button" @click="browseAllProducts">全部产品（{{ products.length }}）</button>
              <button class="primary-button" type="button" @click="addDialogOpen = true"><Plus :size="17" />录入产品</button>
            </div>
          </header>

          <section class="overview-row" aria-label="目录概要">
            <div class="metric"><span>厂牌</span><strong>{{ makerGroups.length }}</strong><small>按厂名归并</small></div>
            <div class="metric"><span>产品</span><strong>{{ products.length }}</strong><small>实时读取数据库</small></div>
            <div class="metric"><span>系列</span><strong>{{ productLines.length }}</strong><small>仅作厂牌内筛选</small></div>
            <div class="metric mock-metric"><span>待补详情</span><strong>{{ products.filter((item) => !item.detail).length }}</strong><small>可作为整理队列</small></div>
          </section>

          <section class="toolbar" aria-label="厂牌筛选">
            <label class="search-field"><Search :size="18" /><input v-model="makerSearch" type="search" placeholder="搜索厂牌" /></label>
            <label class="select-field">
              <select v-model="categoryFilter">
                <option value="">全部分类</option>
                <option value="gundam">高达</option>
                <option value="guomo">国模</option>
                <option value="ko">KO</option>
                <option value="unclassified">未分类</option>
              </select>
            </label>
            <label class="select-field"><Filter :size="16" /><select v-model="makerSort"><option value="taxonomy">按分类 / 等级</option><option value="count">按产品数</option><option value="name">按厂名</option></select></label>
            <span class="result-count">{{ filteredMakers.length }} 家</span>
          </section>

          <section v-if="loading" class="state-panel"><LoaderCircle class="spin" :size="26" /><p>正在读取厂家目录...</p></section>
          <section v-else-if="loadError" class="state-panel error-state"><p>{{ loadError }}</p><button class="secondary-button" type="button" @click="loadProducts"><RefreshCw :size="16" />重新加载</button></section>
          <div v-else-if="filteredMakers.length" class="maker-grid">
            <button v-for="maker in filteredMakers" :key="maker.name" class="maker-card" type="button" @click="enterMaker(maker.name)">
              <span class="maker-avatar" :class="makerTint(maker.name)">{{ maker.name.slice(0, 1) }}</span>
              <span class="maker-body">
                <span class="maker-head">
                  <span class="maker-name">{{ maker.name }}</span>
                  <span class="maker-category" :class="maker.category || 'unclassified'">{{ categoryLabel(maker.category) }}</span>
                </span>
                <span class="maker-meta">{{ maker.count }} 款 · {{ maker.lineCount }} 个系列</span>
                <span v-if="maker.lines.length" class="maker-lines">
                  <span v-for="line in maker.lines" :key="line">{{ line }}</span>
                  <span v-if="maker.lineCount > maker.lines.length" class="more">+{{ maker.lineCount - maker.lines.length }}</span>
                </span>
              </span>
              <span class="maker-arrow" aria-hidden="true">›</span>
            </button>
          </div>
          <section v-else class="state-panel"><p>没有匹配的厂牌。</p><button class="secondary-button" type="button" @click="makerSearch = ''">清除搜索</button></section>
        </template>

        <template v-else>
          <header class="page-header">
            <div>
              <button class="text-button back" type="button" @click="backToMakers"><ArrowLeft :size="16" />厂家目录</button>
              <p class="eyebrow">产品目录</p>
              <h1>{{ selectedMaker || '全部产品' }}</h1>
              <p class="page-subtitle">
                <template v-if="selectedMaker">{{ makerProductCount }} 款 · {{ makerLineGroups.length }} 个系列</template>
                <template v-else>全部 {{ products.length }} 款产品</template>
              </p>
            </div>
            <div class="header-actions">
              <button v-if="selectedMaker" class="secondary-button" type="button" @click="browseAllProducts">全部产品</button>
              <button class="primary-button" type="button" @click="addDialogOpen = true"><Plus :size="17" />录入产品</button>
            </div>
          </header>

          <section v-if="selectedMaker && makerLineGroups.length" class="maker-chips" aria-label="厂牌内系列">
            <button type="button" :class="{ active: !lineFilter }" @click="lineFilter = ''">全部 {{ makerProductCount }}</button>
            <button
              v-for="line in makerLineGroups"
              :key="line.name"
              type="button"
              :class="{ active: lineFilter === line.name }"
              @click="lineFilter = lineFilter === line.name ? '' : line.name"
            >{{ line.name }} {{ line.count }}</button>
          </section>

          <section class="toolbar" aria-label="产品筛选">
            <label class="search-field"><Search :size="18" /><input v-model="search" type="search" :placeholder="selectedMaker ? '搜索当前厂牌的产品' : '搜索产品名、厂商或系列'" /></label>
            <template v-if="!selectedMaker">
              <label class="select-field"><Building2 :size="16" /><select v-model="makerFilter"><option value="">所有厂商</option><option v-for="maker in makers" :key="maker" :value="maker">{{ maker }}</option></select></label>
              <label class="select-field"><Filter :size="16" /><select v-model="lineFilter"><option value="">所有系列</option><option v-for="line in productLines" :key="line" :value="line">{{ line }}</option></select></label>
            </template>
            <button v-if="search || lineFilter || (!selectedMaker && makerFilter)" class="reset-button" type="button" @click="resetFilters"><X :size="15" />清除</button>
            <span class="result-count">{{ filteredProducts.length }} 项</span>
            <div class="view-switch" aria-label="视图方式"><button :class="{ selected: view === 'grid' }" type="button" aria-label="网格视图" title="网格视图" @click="view = 'grid'"><Grid2X2 :size="17" /></button><button :class="{ selected: view === 'list' }" type="button" aria-label="列表视图" title="列表视图" @click="view = 'list'"><List :size="18" /></button></div>
          </section>

          <section v-if="loading" class="state-panel"><LoaderCircle class="spin" :size="26" /><p>正在读取产品目录...</p></section>
          <section v-else-if="loadError" class="state-panel error-state"><p>{{ loadError }}</p><button class="secondary-button" type="button" @click="loadProducts"><RefreshCw :size="16" />重新加载</button></section>
          <section v-else-if="filteredProducts.length" class="products" :class="`view-${view}`"><ProductCard v-for="product in filteredProducts" :key="product.id" :product="product" :view="view" :owned="ownedByProduct.get(product.id) || 0" @select="selectedProduct = $event" @own="ownProduct" /></section>
          <section v-else class="state-panel"><p>没有符合条件的产品。</p><button class="secondary-button" type="button" @click="resetFilters">清除筛选</button></section>
        </template>
      </section>

      <section v-else-if="activeSection === 'review'" class="review-section">
        <ReviewView @pending="reviewPending = $event" />
      </section>

      <section v-else-if="activeSection === 'admin'" class="admin-section">
        <AdminView />
      </section>

      <section v-else-if="activeSection === 'taxonomy'" class="taxonomy-section">
        <TaxonomyAdmin />
      </section>

      <section v-else-if="activeSection === 'inventory'" class="asset-section">
        <AssetView />
      </section>

      <section v-else-if="activeSection === 'collections'" class="collections-section">
        <CollectionDetail v-if="collectionId" :collection-id="collectionId" @back="backToCollections" />
        <CollectionsView v-else @open="openCollection" />
      </section>

      <section v-else-if="activeSection === 'labels'" class="labels-section">
        <LabelsView />
      </section>

      <section v-else class="mock-view">
        <header class="page-header"><div><p class="eyebrow">模拟模块</p><h1>{{ { inventory: '资产清点', wishlist: '愿望单', activity: '活动记录' }[activeSection] }}</h1><p class="page-subtitle">此区域暂用前端模拟数据，尚未连接数据库。</p></div></header>
        <div v-if="false" class="mock-grid"><section class="mock-panel"><h2>收纳概览</h2><strong>48</strong><p>盒装模型 · 模拟统计</p></section><section class="mock-panel"><h2>待确认位置</h2><strong>6</strong><p>可在后续资产模块处理</p></section><section class="mock-panel wide"><h2>最近清点</h2><div class="mock-line"><span>MG 百式 Ver.2.0</span><small>书柜 B-03</small></div><div class="mock-line"><span>HG 风灵高达</span><small>展示柜 A-01</small></div></section></div>
        <div v-else-if="activeSection === 'wishlist'" class="mock-grid"><section class="mock-panel wide"><h2>关注清单</h2><div class="mock-line"><span>RG 沙扎比 Special Coating</span><small>等待补货</small></div><div class="mock-line"><span>GK 独角兽胸像</span><small>待确认资料</small></div></section><section class="mock-panel"><h2>本月预算</h2><strong>¥ 800</strong><p>模拟数据</p></section></div>
        <div v-else class="mock-grid"><section class="mock-panel wide"><h2>近期记录</h2><div class="mock-line"><span>导入产品目录</span><small>195 条 · 初始化测试</small></div><div class="mock-line"><span>创建资料库</span><small>系统事件 · 模拟</small></div></section></div>
      </section>
    </main>
  </div>

  <ProductDrawer :product="selectedProduct" @close="selectedProduct = null" @open-collection="openCollection" />
  <p v-if="toast" class="app-toast" :class="{ 'is-error': toastError }">{{ toast }}</p>
  <AddProductDialog :open="addDialogOpen" :default-manufacturer-id="selectedMakerId" @close="addDialogOpen = false" @created="onCreated" />
</template>

<style>
.app-toast { position: fixed; right: 28px; bottom: 28px; z-index: 60; padding: 10px 14px; color: #1f4a3c; font-size: 13px; background: #e8f5ec; border: 1px solid #b9d9c4; border-radius: 7px; box-shadow: 0 8px 24px #17352a1f; }
.app-toast.is-error { color: #8d3423; background: #fdeee9; border-color: #efc6ba; }

.header-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.back { min-height: 30px; padding: 0; margin-bottom: 8px; color: #557a71; }
.maker-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(245px, 1fr)); gap: 10px; }
.maker-card { display: flex; align-items: center; gap: 12px; padding: 13px 14px; text-align: left; background: #fff; border: 1px solid #dbe2de; border-radius: 8px; transition: border-color .15s ease, transform .15s ease, box-shadow .15s ease; }
.maker-card:hover { border-color: #8eaca1; box-shadow: 0 4px 12px #1e312714; transform: translateY(-1px); }
.maker-avatar { display: grid; flex: 0 0 42px; width: 42px; height: 42px; place-items: center; font-size: 18px; font-weight: 700; border-radius: 12px; }
.maker-avatar.tint-0 { color: #24705f; background: #e8f3ee; }
.maker-avatar.tint-1 { color: #3f5f8a; background: #eef3fb; }
.maker-avatar.tint-2 { color: #8a5f18; background: #fdf6e7; }
.maker-avatar.tint-3 { color: #6b4d8a; background: #f3eef8; }
.maker-avatar.tint-4 { color: #a4402c; background: #fdeee9; }
.maker-avatar.tint-5 { color: #4f5f5a; background: #eef1ef; }
.maker-body { display: grid; flex: 1; gap: 2px; min-width: 0; }
.maker-head { display: flex; align-items: center; gap: 6px; min-width: 0; }
.maker-name { flex: 1; overflow: hidden; color: #1d2b27; font-size: 15px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.maker-category { flex: 0 0 auto; padding: 1px 6px; font-size: 10px; line-height: 1.5; border-radius: 999px; border: 1px solid #dfe6e1; }
.maker-category.gundam { color: #3f5f8a; background: #eef3fb; border-color: #d3dff0; }
.maker-category.guomo { color: #1f5b4c; background: #e8f3ee; border-color: #c9e2d7; }
.maker-category.ko { color: #8a5f18; background: #fdf6e7; border-color: #f0dfb8; }
.maker-category.unclassified { color: #8a8f8c; background: #f3f3f1; border-color: #e2e2df; }
.maker-meta { color: #87938f; font-size: 11px; }
.maker-lines { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 2px; }
.maker-lines span { padding: 1px 6px; color: #557069; font-size: 10px; background: #f2f7f4; border: 1px solid #e0eae4; border-radius: 999px; }
.maker-lines .more { color: #87938f; background: transparent; border-color: transparent; }
.maker-arrow { margin-left: auto; color: #b0bbb6; font-size: 20px; line-height: 1; }
.maker-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: -6px 0 16px; }
.maker-chips button { padding: 5px 10px; color: #52645e; font-size: 12px; background: #f2f7f4; border: 1px solid #dbe7e0; border-radius: 999px; }
.maker-chips button:hover { background: #e8f1ec; }
.maker-chips button.active { color: #fff; background: #24705f; border-color: #24705f; }
@media (max-width: 650px) {
  .maker-grid { grid-template-columns: 1fr; }
}
</style>
