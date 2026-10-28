<script setup>
import { computed, onMounted, ref } from 'vue'
import { LoaderCircle, Plus, RefreshCw, Search, Trophy } from 'lucide-vue-next'
import CollectionDialog from './CollectionDialog.vue'
import CollectionProgress from './CollectionProgress.vue'
import { COLLECTION_STATUSES, COLLECTION_STATUS_META, formatShortDate } from '../collectionMeta'

const emit = defineEmits(['open'])

const collections = ref([])
const loading = ref(true)
const error = ref('')
const search = ref('')
const statusFilter = ref('')
const sortBy = ref('updated')
const dialogOpen = ref(false)
const editing = ref(null)

const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  const rows = collections.value.filter((collection) => {
    if (statusFilter.value && collection.status !== statusFilter.value) return false
    if (!term) return true
    return [collection.title, collection.description].filter(Boolean).join(' ').toLowerCase().includes(term)
  })
  return rows.slice().sort((a, b) => {
    if (sortBy.value === 'progress') {
      const diff = (b.stats.percent || 0) - (a.stats.percent || 0)
      return diff || a.title.localeCompare(b.title, 'zh-CN')
    }
    if (sortBy.value === 'title') return a.title.localeCompare(b.title, 'zh-CN')
    return (b.updated_at || '').localeCompare(a.updated_at || '')
  })
})

const overview = computed(() => {
  const active = collections.value.filter((collection) => collection.status === 'active').length
  const completed = collections.value.filter((collection) => collection.stats.completed).length
  const targets = collections.value.reduce((sum, collection) => sum + collection.stats.total, 0)
  const owned = collections.value.reduce((sum, collection) => sum + collection.stats.owned, 0)
  return { active, completed, targets, owned }
})

async function loadCollections() {
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/v1/collections?limit=500')
    if (!response.ok) throw new Error('收藏集读取失败')
    collections.value = await response.json()
  } catch (exc) {
    error.value = exc.message
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}

function onSaved(saved) {
  loadCollections()
  if (!editing.value) emit('open', saved.id)
  editing.value = null
}

onMounted(loadCollections)
</script>

<template>
  <section class="collections-view">
    <header class="page-header">
      <div>
        <p class="eyebrow">收藏集</p>
        <h1>制霸计划</h1>
        <p class="page-subtitle">范围由你定：把想收的产品列成一张清单，进度从资产表实时算。</p>
      </div>
      <div class="header-actions">
        <button class="secondary-button" type="button" :disabled="loading" @click="loadCollections"><RefreshCw :size="16" />刷新</button>
        <button class="primary-button" type="button" @click="openCreate"><Plus :size="17" />新建收藏集</button>
      </div>
    </header>

    <section class="overview-row collection-overview" aria-label="收藏集概要">
      <div class="metric"><span>进行中</span><strong>{{ overview.active }}</strong><small>状态为进行中</small></div>
      <div class="metric"><span>已达成</span><strong>{{ overview.completed }}</strong><small>拥有数 = 目标数</small></div>
      <div class="metric"><span>目标总数</span><strong>{{ overview.targets }}</strong><small>所有清单加总</small></div>
      <div class="metric"><span>已拥有</span><strong>{{ overview.owned }}</strong><small>不算已售</small></div>
    </section>

    <section class="toolbar">
      <label class="search-field"><Search :size="18" /><input v-model="search" type="search" placeholder="搜索名称或描述" /></label>
      <label class="select-field">
        <select v-model="statusFilter">
          <option value="">所有状态</option>
          <option v-for="item in COLLECTION_STATUSES" :key="item.value" :value="item.value">{{ item.label }}</option>
        </select>
      </label>
      <label class="select-field">
        <select v-model="sortBy">
          <option value="updated">最近更新</option>
          <option value="progress">进度</option>
          <option value="title">名称</option>
        </select>
      </label>
      <span class="result-count">{{ filtered.length }} 个</span>
    </section>

    <p v-if="loading" class="state-panel"><LoaderCircle class="spin" :size="24" />正在读取收藏集…</p>
    <p v-else-if="error" class="state-panel error-state">{{ error }}</p>
    <div v-else-if="filtered.length" class="collection-grid">
      <button v-for="collection in filtered" :key="collection.id" class="collection-card" type="button" @click="emit('open', collection.id)">
        <div class="card-head">
          <span class="status-pill" :class="collection.status">{{ COLLECTION_STATUS_META[collection.status]?.label || collection.status }}</span>
          <span v-if="collection.stats.completed" class="completed-badge">已制霸</span>
        </div>
        <h2>{{ collection.title }}</h2>
        <p class="card-desc">{{ collection.description || '还没有描述。' }}</p>

        <div class="progress-head">
          <span><strong>{{ collection.stats.owned }}</strong> / {{ collection.stats.total }}</span>
          <span>{{ collection.stats.total ? `${collection.stats.percent}%` : '未定义' }}</span>
        </div>
        <CollectionProgress :built="collection.stats.built" :owned="collection.stats.owned" :total="collection.stats.total" :height="10" />
        <div class="legend">
          <span><i class="dot built"></i>已拼 {{ collection.stats.built }}</span>
          <span><i class="dot unbuilt"></i>未拼 {{ collection.stats.unbuilt }}</span>
          <span><i class="dot missing"></i>缺口 {{ collection.stats.missing }}</span>
        </div>

        <footer class="card-foot">
          <span>{{ collection.stats.completed ? '全部收齐' : `还差 ${collection.stats.missing} 款` }}</span>
          <span v-if="collection.target_on">目标 {{ formatShortDate(collection.target_on) }}</span>
          <span v-else>更新 {{ formatShortDate(collection.updated_at) }}</span>
        </footer>
      </button>
    </div>
    <div v-else class="state-panel collection-empty">
      <Trophy :size="28" />
      <p>{{ collections.length ? '没有符合条件的收藏集。' : '还没有收藏集。先定义一个范围，比如“RG 扎古全制霸”。' }}</p>
      <button v-if="!collections.length" class="primary-button" type="button" @click="openCreate"><Plus :size="17" />新建收藏集</button>
    </div>

    <CollectionDialog :open="dialogOpen" :collection="editing" @close="dialogOpen = false" @saved="onSaved" />
  </section>
</template>

<style scoped>
.header-actions { display: flex; gap: 8px; }
.collection-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }
.collection-card { display: grid; gap: 10px; padding: 18px; text-align: left; background: #fff; border: 1px solid #dbe2de; border-radius: 8px; transition: border-color .15s ease, transform .15s ease, box-shadow .15s ease; }
.collection-card:hover { border-color: #8eaca1; box-shadow: 0 5px 14px #1e312714; transform: translateY(-2px); }
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.collection-card h2 { margin: 0; color: #1d2b27; font-size: 17px; line-height: 1.35; }
.card-desc { display: -webkit-box; min-height: 38px; margin: 0; overflow: hidden; color: #6b7774; font-size: 12px; line-height: 1.55; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.progress-head { display: flex; align-items: baseline; justify-content: space-between; margin-top: 2px; color: #557069; font-size: 12px; }
.progress-head strong { color: #1b2925; font-size: 20px; }
.progress-head span:last-child { color: #24705f; font-weight: 600; }
.legend { display: flex; flex-wrap: wrap; gap: 8px 12px; color: #6b7774; font-size: 11px; }
.legend span { display: inline-flex; align-items: center; gap: 4px; }
.dot { width: 7px; height: 7px; border-radius: 50%; }
.dot.built { background: #1f6f5c; }
.dot.unbuilt { background: #8fc7b4; }
.dot.missing { background: #e6e9e6; border: 1px solid #cbd6d0; }
.card-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding-top: 10px; color: #87938f; font-size: 11px; border-top: 1px solid #edf0ee; }
.status-pill { display: inline-block; padding: 2px 8px; font-size: 11px; border-radius: 999px; border: 1px solid #dfe6e1; }
.status-pill.planning { color: #4f5f8a; background: #eef3fb; border-color: #d3dff0; }
.status-pill.active { color: #1f5b4c; background: #e8f3ee; border-color: #c9e2d7; }
.status-pill.paused { color: #8a5f18; background: #fdf6e7; border-color: #f0dfb8; }
.status-pill.abandoned { color: #8a8f8c; background: #f3f3f1; border-color: #e2e2df; }
.completed-badge { padding: 2px 8px; color: #7a5312; font-size: 11px; font-weight: 600; background: #fdf3d9; border: 1px solid #ecd39b; border-radius: 999px; }
.collection-empty { flex-direction: column; }
@media (max-width: 650px) {
  .collection-grid { grid-template-columns: 1fr; }
  .collection-overview { grid-template-columns: 1fr 1fr; }
}
</style>
