<script setup>
import { computed, ref, watch } from 'vue'
import { LoaderCircle, Search, X } from 'lucide-vue-next'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'created'])

const STATE_OPTIONS = [
  { value: 'pending', label: '待拼（买了没动）' },
  { value: 'displayed', label: '展示（已拼）' },
  { value: 'stored', label: '收纳（已拼已封袋）' },
  { value: 'keep', label: '收藏（不打算拼）' },
]

const products = ref([])
const loading = ref(false)
const error = ref('')
const search = ref('')
const state = ref('pending')
const picked = ref([])
const busy = ref(false)

const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  const rows = term
    ? products.value.filter((item) =>
      [item.kit_name, item.manufacturer, item.product_line, item.product_code]
        .filter(Boolean).join(' ').toLowerCase().includes(term))
    : products.value
  return rows.slice(0, 200)
})

const pickedSet = computed(() => new Set(picked.value))

watch(() => props.open, async (open) => {
  if (!open) return
  picked.value = []
  search.value = ''
  if (products.value.length) return
  loading.value = true
  error.value = ''
  try {
    const response = await fetch('/api/v1/products?limit=5000')
    if (!response.ok) throw new Error('产品目录请求失败')
    products.value = await response.json()
  } catch (exc) {
    error.value = exc.message
  } finally {
    loading.value = false
  }
}, { immediate: true })

function toggle(id) {
  const index = picked.value.indexOf(id)
  if (index >= 0) picked.value.splice(index, 1)
  else picked.value.push(id)
}

async function submit() {
  if (!picked.value.length || busy.value) return
  busy.value = true
  try {
    const response = await fetch('/api/v1/assets/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_ids: picked.value, state: state.value }),
    })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(body.detail || `请求失败 (${response.status})`)
    emit('created', { assets: body, state: state.value })
    emit('close')
  } catch (exc) {
    error.value = exc.message
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
            <span class="eyebrow">添加资产</span>
            <h2>从产品库选择</h2>
            <p class="hint">同一台模型有两盒就选两次；一次最多 200 条。</p>
          </div>
          <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')"><X :size="20" /></button>
        </header>

        <div class="pick-toolbar">
          <label class="search-field"><Search :size="18" /><input v-model="search" type="search" placeholder="搜索产品名 / 厂商 / 系列" /></label>
          <label class="select-field state-field">
            <select v-model="state">
              <option v-for="option in STATE_OPTIONS" :key="option.value" :value="option.value">{{ option.label }}</option>
            </select>
          </label>
        </div>

        <p v-if="loading" class="pick-state"><LoaderCircle class="spin" :size="18" />读取产品目录…</p>
        <p v-else-if="error" class="pick-state is-error">{{ error }}</p>
        <ul v-else class="pick-list">
          <li v-for="product in filtered" :key="product.id" :class="{ picked: pickedSet.has(product.id) }" @click="toggle(product.id)">
            <span class="tick">{{ pickedSet.has(product.id) ? '✓' : '' }}</span>
            <span class="pick-name">{{ product.kit_name }}</span>
            <span class="pick-meta">{{ [product.manufacturer, product.product_line].filter(Boolean).join(' · ') }}</span>
          </li>
        </ul>

        <footer>
          <span class="pick-count">已选 {{ picked.length }} 项</span>
          <div>
            <button class="text-button" type="button" @click="emit('close')">取消</button>
            <button class="primary-button" type="button" :disabled="!picked.length || busy" @click="submit">
              {{ busy ? '处理中…' : `加入资产（${picked.length}）` }}
            </button>
          </div>
        </footer>
      </section>
    </div>
  </Transition>
</template>

<style scoped>
.add-dialog { width: min(100%, 720px); }
.hint { margin: 6px 0 0; color: #71807c; font-size: 12px; }
.pick-toolbar { display: flex; gap: 9px; margin: 18px 0 12px; }
.state-field { flex: 0 0 220px; }
.pick-list { max-height: 44vh; margin: 0; padding: 0; overflow: auto; list-style: none; border: 1px solid #e2e8e4; border-radius: 6px; }
.pick-list li { display: grid; grid-template-columns: 26px minmax(0, 1fr) auto; gap: 8px; align-items: center; padding: 9px 12px; font-size: 13px; color: #2b3a35; border-bottom: 1px solid #eff2ef; cursor: pointer; }
.pick-list li:last-child { border-bottom: 0; }
.pick-list li:hover { background: #f7faf7; }
.pick-list li.picked { background: #eef6f2; }
.tick { display: grid; width: 18px; height: 18px; place-items: center; color: #fff; font-size: 12px; background: #fff; border: 1px solid #c7d3ce; border-radius: 3px; }
.picked .tick { background: #24705f; border-color: #24705f; }
.pick-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pick-meta { color: #87938f; font-size: 11px; white-space: nowrap; }
.pick-state { display: flex; align-items: center; gap: 8px; padding: 28px; color: #6d7b77; }
.pick-state.is-error { color: #9a452f; }
footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 16px; padding-top: 14px; border-top: 1px solid #e4eae6; }
footer > div { display: flex; gap: 8px; }
.pick-count { color: #6b7774; font-size: 13px; }
</style>
