<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Building2, Filter, Grid2X2, List, LoaderCircle, Plus, RefreshCw, Search, X } from 'lucide-vue-next'
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

const SECTIONS = ['directory', 'review', 'admin', 'inventory', 'collections', 'labels', 'print', 'wishlist', 'activity']
const activeSection = ref('directory')
const collectionId = ref('')
const selectedProduct = ref(null)

function applyRoute() {
  const [section, id = ''] = window.location.hash.replace('#', '').split('/')
  activeSection.value = SECTIONS.includes(section) ? section : 'directory'
  collectionId.value = activeSection.value === 'collections' ? id : ''
  selectedProduct.value = null
}

function setRoute(section, id = '') {
  const target = section === 'directory' ? '' : (id ? `${section}/${id}` : section)
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

async function loadReviewPending() {
  try {
    const response = await fetch('/api/v1/review/stats')
    if (response.ok) reviewPending.value = (await response.json()).pending
  } catch {
    /* badge is best-effort */
  }
}

const makers = computed(() => [...new Set(products.value.map((item) => item.manufacturer).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-CN')))

// 厂商选定后，产品线栏仅可选厂商所存在的产品线，而非全局
const productLines = computed(() => {
  const sourceList = makerFilter.value
    ? products.value.filter((item) => item.manufacturer === makerFilter.value)
    : products.value
  return [...new Set(sourceList.map((item) => item.product_line).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-CN'))
})

// 如果先选产品线，再选厂商的话，则产品恢复全局筛选（清空已选产品线）
watch(makerFilter, () => {
  lineFilter.value = ''
})

const filteredProducts = computed(() => {
  const keyword = search.value.trim().toLocaleLowerCase()
  return products.value
    .filter((item) => {
      const matchText = !keyword || [item.kit_name, item.manufacturer, item.product_code, item.product_line].filter(Boolean).join(' ').toLocaleLowerCase().includes(keyword)
      return matchText && (!makerFilter.value || item.manufacturer === makerFilter.value) && (!lineFilter.value || item.product_line === lineFilter.value)
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

      // 2. 按照产品线排序
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
  makerFilter.value = ''
  lineFilter.value = ''
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
        <header class="page-header">
          <div><p class="eyebrow">产品资料库</p><h1>产品目录</h1><p class="page-subtitle">将手头资料整理为可检索的产品档案。</p></div>
          <button class="primary-button" type="button" @click="addDialogOpen = true"><Plus :size="17" />录入产品</button>
        </header>

        <section class="overview-row" aria-label="目录概要">
          <div class="metric"><span>已入库产品</span><strong>{{ products.length }}</strong><small>实时读取数据库</small></div>
          <div class="metric"><span>产品线</span><strong>{{ productLines.length }}</strong><small>待后续统一规范</small></div>
          <div class="metric"><span>厂商</span><strong>{{ makers.length }}</strong><small>按厂商归并</small></div>
          <div class="metric mock-metric"><span>待补详情</span><strong>{{ products.filter((item) => !item.detail).length }}</strong><small>可作为整理队列</small></div>
        </section>

        <section class="toolbar" aria-label="产品筛选">
          <label class="search-field"><Search :size="18" /><input v-model="search" type="search" placeholder="搜索产品名、厂商或产品线" /></label>
          <label class="select-field"><Building2 :size="16" /><select v-model="makerFilter"><option value="">所有厂商</option><option v-for="maker in makers" :key="maker" :value="maker">{{ maker }}</option></select></label>
          <label class="select-field"><Filter :size="16" /><select v-model="lineFilter"><option value="">所有产品线</option><option v-for="line in productLines" :key="line" :value="line">{{ line }}</option></select></label>
          <button v-if="search || makerFilter || lineFilter" class="reset-button" type="button" @click="resetFilters"><X :size="15" />清除</button>
          <span class="result-count">{{ filteredProducts.length }} 项</span>
          <div class="view-switch" aria-label="视图方式"><button :class="{ selected: view === 'grid' }" type="button" aria-label="网格视图" title="网格视图" @click="view = 'grid'"><Grid2X2 :size="17" /></button><button :class="{ selected: view === 'list' }" type="button" aria-label="列表视图" title="列表视图" @click="view = 'list'"><List :size="18" /></button></div>
        </section>

        <section v-if="loading" class="state-panel"><LoaderCircle class="spin" :size="26" /><p>正在读取产品目录...</p></section>
        <section v-else-if="loadError" class="state-panel error-state"><p>{{ loadError }}</p><button class="secondary-button" type="button" @click="loadProducts"><RefreshCw :size="16" />重新加载</button></section>
        <section v-else-if="filteredProducts.length" class="products" :class="`view-${view}`"><ProductCard v-for="product in filteredProducts" :key="product.id" :product="product" :view="view" :owned="ownedByProduct.get(product.id) || 0" @select="selectedProduct = $event" @own="ownProduct" /></section>
        <section v-else class="state-panel"><p>没有符合条件的产品。</p><button class="secondary-button" type="button" @click="resetFilters">清除筛选</button></section>
      </section>

      <section v-else-if="activeSection === 'review'" class="review-section">
        <ReviewView @pending="reviewPending = $event" />
      </section>

      <section v-else-if="activeSection === 'admin'" class="admin-section">
        <AdminView />
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
  <AddProductDialog :open="addDialogOpen" @close="addDialogOpen = false" @created="onCreated" />
</template>

<style>
.app-toast { position: fixed; right: 28px; bottom: 28px; z-index: 60; padding: 10px 14px; color: #1f4a3c; font-size: 13px; background: #e8f5ec; border: 1px solid #b9d9c4; border-radius: 7px; box-shadow: 0 8px 24px #17352a1f; }
.app-toast.is-error { color: #8d3423; background: #fdeee9; border-color: #efc6ba; }
</style>
