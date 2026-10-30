<script setup>
import { computed, ref, watch } from 'vue'
import { LoaderCircle, Search, X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
  collectionId: { type: String, required: true },
  existingIds: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'added'])

const products = ref([])
const loading = ref(false)
const loadError = ref('')
const submitError = ref('')
const search = ref('')
const makerFilter = ref('')
const lineFilter = ref('')
const picked = ref([])
const busy = ref(false)

const existingSet = computed(() => new Set(props.existingIds))
const pickedSet = computed(() => new Set(picked.value))

const available = computed(() => products.value.filter((product) => !existingSet.value.has(product.id)))
const makers = computed(() => [...new Set(available.value.map((p) => p.manufacturer).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-CN')))
const lines = computed(() => {
  const source = makerFilter.value
    ? available.value.filter((p) => p.manufacturer === makerFilter.value)
    : available.value
  return [...new Set(source.map((p) => p.product_line).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-CN'))
})

const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  return available.value
    .filter((product) => {
      if (makerFilter.value && product.manufacturer !== makerFilter.value) return false
      if (lineFilter.value && product.product_line !== lineFilter.value) return false
      if (!term) return true
      return [product.kit_name, product.manufacturer, product.product_line, product.product_code]
        .filter(Boolean).join(' ').toLowerCase().includes(term)
    })
    .slice(0, 500)
})

const allChecked = computed(() => filtered.value.length > 0 && filtered.value.every((p) => pickedSet.value.has(p.id)))

watch(
  () => props.open,
  async (open) => {
    if (!open) return
    picked.value = []
    search.value = ''
    makerFilter.value = ''
    lineFilter.value = ''
    loadError.value = ''
    submitError.value = ''
    loading.value = true
    try {
      const response = await fetch('/api/v1/products?limit=5000')
      if (!response.ok) throw new Error('产品目录读取失败')
      products.value = await response.json()
    } catch (exc) {
      loadError.value = exc.message
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

function toggle(id) {
  const index = picked.value.indexOf(id)
  if (index >= 0) picked.value.splice(index, 1)
  else picked.value.push(id)
}

function toggleAll() {
  if (allChecked.value) {
    const visible = new Set(filtered.value.map((p) => p.id))
    picked.value = picked.value.filter((id) => !visible.has(id))
  } else {
    const next = new Set(picked.value)
    for (const product of filtered.value) next.add(product.id)
    picked.value = [...next]
  }
}

async function submit() {
  if (!picked.value.length || busy.value) return
  busy.value = true
  submitError.value = ''
  try {
    const response = await fetch(`/api/v1/collections/${props.collectionId}/items/bulk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_ids: picked.value }),
    })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(body.detail || `请求失败 (${response.status})`)
    emit('added', body)
    emit('close')
  } catch (exc) {
    submitError.value = exc.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Transition name="dialog">
    <div v-if="open" class="dialog-layer" @click.self="emit('close')">
      <section class="dialog add-dialog">
        <header>
          <div>
            <span class="eyebrow">添加目标</span>
            <h2>从产品目录选择</h2>
            <p class="dialog-hint">只列出还没加入本收藏集的产品；一次最多 500 条。</p>
          </div>
          <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')"><X :size="20" /></button>
        </header>

        <div class="pick-toolbar">
          <label class="search-field"><Search :size="18" /><input v-model="search" type="search" placeholder="搜索产品名 / 编号 / 系列" /></label>
          <label class="select-field">
            <select v-model="makerFilter" @change="lineFilter = ''">
              <option value="">所有厂商</option>
              <option v-for="maker in makers" :key="maker" :value="maker">{{ maker }}</option>
            </select>
          </label>
          <label class="select-field">
            <select v-model="lineFilter">
              <option value="">所有系列</option>
              <option v-for="line in lines" :key="line" :value="line">{{ line }}</option>
            </select>
          </label>
        </div>

        <div class="pick-summary">
          <button class="text-button" type="button" :disabled="!filtered.length" @click="toggleAll">
            {{ allChecked ? '取消全选' : '全选当前结果' }}
          </button>
          <span>{{ filtered.length }} 个可选</span>
        </div>

        <p v-if="loading" class="pick-state"><LoaderCircle class="spin" :size="18" />读取产品目录…</p>
        <p v-else-if="loadError" class="pick-state is-error">{{ loadError }}</p>
        <ul v-else-if="filtered.length" class="pick-list">
          <li v-for="product in filtered" :key="product.id" :class="{ picked: pickedSet.has(product.id) }" @click="toggle(product.id)">
            <span class="tick">{{ pickedSet.has(product.id) ? '✓' : '' }}</span>
            <span class="pick-name">{{ product.kit_name }}</span>
            <span class="pick-meta">{{ [product.manufacturer, product.product_line, product.product_code].filter(Boolean).join(' · ') }}</span>
          </li>
        </ul>
        <p v-else class="pick-state">没有可加入的产品。先去产品目录录入，或调整筛选。</p>

        <p v-if="submitError" class="form-error">{{ submitError }}</p>
        <footer>
          <span class="pick-count">已选 {{ picked.length }} 项</span>
          <div>
            <button class="text-button" type="button" @click="emit('close')">取消</button>
            <button class="primary-button" type="button" :disabled="!picked.length || busy" @click="submit">
              {{ busy ? '处理中…' : `加入收藏集（${picked.length}）` }}
            </button>
          </div>
        </footer>
      </section>
    </div>
  </Transition>
</template>

<style scoped>
.add-dialog { width: min(100%, 760px); }
.dialog-hint { margin: 6px 0 0; color: #71807c; font-size: 12px; }
.pick-toolbar { display: grid; grid-template-columns: minmax(0, 1fr) 150px 150px; gap: 9px; margin: 18px 0 10px; }
.pick-summary { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; color: #6b7774; font-size: 12px; }
.pick-list { max-height: 46vh; margin: 0; padding: 0; overflow: auto; list-style: none; border: 1px solid #e2e8e4; border-radius: 6px; }
.pick-list li { display: grid; grid-template-columns: 26px minmax(0, 1fr) auto; gap: 8px; align-items: center; padding: 9px 12px; font-size: 13px; color: #2b3a35; border-bottom: 1px solid #eff2ef; cursor: pointer; }
.pick-list li:last-child { border-bottom: 0; }
.pick-list li:hover { background: #f7faf7; }
.pick-list li.picked { background: #eef6f2; }
.tick { display: grid; width: 18px; height: 18px; place-items: center; color: #fff; font-size: 12px; background: #fff; border: 1px solid #c7d3ce; border-radius: 3px; }
.picked .tick { background: #24705f; border-color: #24705f; }
.pick-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pick-meta { color: #87938f; font-size: 11px; white-space: nowrap; }
.pick-state { display: flex; align-items: center; gap: 8px; min-height: 120px; padding: 24px; color: #6d7b77; }
.pick-state.is-error { color: #9a452f; }
footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 16px; padding-top: 14px; border-top: 1px solid #e4eae6; }
footer > div { display: flex; gap: 8px; }
.pick-count { color: #6b7774; font-size: 13px; }
@media (max-width: 650px) {
  .pick-toolbar { grid-template-columns: 1fr; }
}
</style>
