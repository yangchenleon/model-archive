<script setup>
import { computed, onMounted, ref } from 'vue'
import { Filter, Grid2X2, List, LoaderCircle, Plus, RefreshCw, Search, SlidersHorizontal, X } from 'lucide-vue-next'
import SidebarNav from './components/SidebarNav.vue'
import ProductCard from './components/ProductCard.vue'
import ProductDrawer from './components/ProductDrawer.vue'
import AddProductDialog from './components/AddProductDialog.vue'

const activeSection = ref('directory')
const products = ref([])
const loading = ref(true)
const loadError = ref('')
const search = ref('')
const originFilter = ref('')
const lineFilter = ref('')
const view = ref('grid')
const selectedProduct = ref(null)
const addDialogOpen = ref(false)

const origins = computed(() => [...new Set(products.value.map((item) => item.origin_type).filter(Boolean))].sort())
const productLines = computed(() => [...new Set(products.value.map((item) => item.product_line).filter(Boolean))].sort())
const filteredProducts = computed(() => {
  const keyword = search.value.trim().toLocaleLowerCase()
  return products.value.filter((item) => {
    const matchText = !keyword || [item.kit_name, item.manufacturer, item.product_code, item.product_line, item.variant_name].filter(Boolean).join(' ').toLocaleLowerCase().includes(keyword)
    return matchText && (!originFilter.value || item.origin_type === originFilter.value) && (!lineFilter.value || item.product_line === lineFilter.value)
  })
})

async function loadProducts() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await fetch('/api/v1/products?limit=500')
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
  originFilter.value = ''
  lineFilter.value = ''
}

function onCreated(product) {
  products.value.push(product)
  selectedProduct.value = product
}

onMounted(loadProducts)
</script>

<template>
  <div class="app-shell">
    <SidebarNav :active="activeSection" :total="products.length" @change="activeSection = $event" />

    <main class="content">
      <section v-if="activeSection === 'directory'" class="directory-view">
        <header class="page-header">
          <div><p class="eyebrow">产品资料库</p><h1>产品目录</h1><p class="page-subtitle">将手头资料整理为可检索的产品档案。</p></div>
          <button class="primary-button" type="button" @click="addDialogOpen = true"><Plus :size="17" />录入产品</button>
        </header>

        <section class="overview-row" aria-label="目录概要">
          <div class="metric"><span>已入库产品</span><strong>{{ products.length }}</strong><small>实时读取数据库</small></div>
          <div class="metric"><span>产品线</span><strong>{{ productLines.length }}</strong><small>待后续统一规范</small></div>
          <div class="metric"><span>来源类型</span><strong>{{ origins.length }}</strong><small>当前为自由文本</small></div>
          <div class="metric mock-metric"><span>待补详情</span><strong>{{ products.filter((item) => !item.detail).length }}</strong><small>可作为整理队列</small></div>
        </section>

        <section class="toolbar" aria-label="产品筛选">
          <label class="search-field"><Search :size="18" /><input v-model="search" type="search" placeholder="搜索产品名、厂商或产品线" /></label>
          <label class="select-field"><Filter :size="16" /><select v-model="lineFilter"><option value="">所有产品线</option><option v-for="line in productLines" :key="line" :value="line">{{ line }}</option></select></label>
          <label class="select-field"><SlidersHorizontal :size="16" /><select v-model="originFilter"><option value="">所有来源类型</option><option v-for="origin in origins" :key="origin" :value="origin">{{ origin }}</option></select></label>
          <button v-if="search || lineFilter || originFilter" class="reset-button" type="button" @click="resetFilters"><X :size="15" />清除</button>
          <span class="result-count">{{ filteredProducts.length }} 项</span>
          <div class="view-switch" aria-label="视图方式"><button :class="{ selected: view === 'grid' }" type="button" aria-label="网格视图" title="网格视图" @click="view = 'grid'"><Grid2X2 :size="17" /></button><button :class="{ selected: view === 'list' }" type="button" aria-label="列表视图" title="列表视图" @click="view = 'list'"><List :size="18" /></button></div>
        </section>

        <section v-if="loading" class="state-panel"><LoaderCircle class="spin" :size="26" /><p>正在读取产品目录...</p></section>
        <section v-else-if="loadError" class="state-panel error-state"><p>{{ loadError }}</p><button class="secondary-button" type="button" @click="loadProducts"><RefreshCw :size="16" />重新加载</button></section>
        <section v-else-if="filteredProducts.length" class="products" :class="`view-${view}`"><ProductCard v-for="product in filteredProducts" :key="product.id" :product="product" :view="view" @select="selectedProduct = $event" /></section>
        <section v-else class="state-panel"><p>没有符合条件的产品。</p><button class="secondary-button" type="button" @click="resetFilters">清除筛选</button></section>
      </section>

      <section v-else class="mock-view">
        <header class="page-header"><div><p class="eyebrow">模拟模块</p><h1>{{ { inventory: '资产清点', wishlist: '愿望单', activity: '活动记录' }[activeSection] }}</h1><p class="page-subtitle">此区域暂用前端模拟数据，尚未连接数据库。</p></div></header>
        <div v-if="activeSection === 'inventory'" class="mock-grid"><section class="mock-panel"><h2>收纳概览</h2><strong>48</strong><p>盒装模型 · 模拟统计</p></section><section class="mock-panel"><h2>待确认位置</h2><strong>6</strong><p>可在后续资产模块处理</p></section><section class="mock-panel wide"><h2>最近清点</h2><div class="mock-line"><span>MG 百式 Ver.2.0</span><small>书柜 B-03</small></div><div class="mock-line"><span>HG 风灵高达</span><small>展示柜 A-01</small></div></section></div>
        <div v-else-if="activeSection === 'wishlist'" class="mock-grid"><section class="mock-panel wide"><h2>关注清单</h2><div class="mock-line"><span>RG 沙扎比 Special Coating</span><small>等待补货</small></div><div class="mock-line"><span>GK 独角兽胸像</span><small>待确认资料</small></div></section><section class="mock-panel"><h2>本月预算</h2><strong>¥ 800</strong><p>模拟数据</p></section></div>
        <div v-else class="mock-grid"><section class="mock-panel wide"><h2>近期记录</h2><div class="mock-line"><span>导入产品目录</span><small>195 条 · 初始化测试</small></div><div class="mock-line"><span>创建资料库</span><small>系统事件 · 模拟</small></div></section></div>
      </section>
    </main>
  </div>

  <ProductDrawer :product="selectedProduct" @close="selectedProduct = null" />
  <AddProductDialog :open="addDialogOpen" @close="addDialogOpen = false" @created="onCreated" />
</template>
