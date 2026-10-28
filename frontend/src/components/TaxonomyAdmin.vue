<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { Building2, LoaderCircle, Plus, RefreshCw, Save, Trash2 } from 'lucide-vue-next'
import { CATEGORY_META, categoryLabel } from '../taxonomy'

const manufacturers = ref([])
const lines = ref([])
const selectedId = ref('')
const loading = ref(true)
const saving = ref(false)
const message = ref('')
const messageError = ref(false)
const search = ref('')
const categoryFilter = ref('')
const lineDraft = ref('')
const mergeTargetId = ref('')
const creating = ref(false)
const createForm = reactive({ name: '', category: '', tier: 3 })
const form = reactive({ name: '', category: '', tier: 3, sort_order: 0, description: '' })

const selected = computed(() => manufacturers.value.find((row) => row.id === selectedId.value) || null)
const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  return manufacturers.value.filter((row) => {
    if (categoryFilter.value === 'unclassified' && row.category !== null) return false
    if (categoryFilter.value && categoryFilter.value !== 'unclassified' && row.category !== categoryFilter.value) return false
    return !term || row.name.toLowerCase().includes(term)
  })
})
const mergeTargets = computed(() => manufacturers.value.filter((row) => row.id !== selectedId.value))
const categoryOptions = computed(() => Object.entries(CATEGORY_META).map(([value, meta]) => ({ value, label: meta.label })))

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

function syncForm() {
  if (!selected.value) return
  Object.assign(form, {
    name: selected.value.name,
    category: selected.value.category || '',
    tier: selected.value.tier || 3,
    sort_order: selected.value.sort_order || 0,
    description: selected.value.description || '',
  })
  mergeTargetId.value = ''
}

async function loadManufacturers() {
  loading.value = true
  try {
    manufacturers.value = await api('/api/v1/manufacturers?limit=500')
    if (selectedId.value && !selected.value) selectedId.value = ''
    if (!selectedId.value && manufacturers.value.length) selectedId.value = manufacturers.value[0].id
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    loading.value = false
  }
}

async function loadLines() {
  if (!selectedId.value) {
    lines.value = []
    return
  }
  try {
    lines.value = await api(`/api/v1/product-lines?manufacturer_id=${selectedId.value}&limit=500`)
  } catch {
    lines.value = []
  }
}

async function createManufacturer() {
  if (saving.value) return
  if (!createForm.name.trim()) {
    flash('请填写厂商名称', true)
    return
  }
  saving.value = true
  try {
    const created = await api('/api/v1/manufacturers', {
      method: 'POST',
      body: JSON.stringify({
        name: createForm.name.trim(),
        category: createForm.category || null,
        tier: Number(createForm.tier),
      }),
    })
    createForm.name = ''
    createForm.category = ''
    createForm.tier = 3
    creating.value = false
    await loadManufacturers()
    selectedId.value = created.id
    await loadLines()
    syncForm()
    flash('厂商已新建')
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    saving.value = false
  }
}

async function saveManufacturer() {
  if (!selected.value || saving.value) return
  saving.value = true
  try {
    await api(`/api/v1/manufacturers/${selected.value.id}`, {
      method: 'PATCH',
      body: JSON.stringify({
        name: form.name.trim(),
        category: form.category || null,
        tier: Number(form.tier),
        sort_order: Number(form.sort_order) || 0,
        description: form.description.trim() || null,
      }),
    })
    await loadManufacturers()
    syncForm()
    flash('厂商已保存')
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    saving.value = false
  }
}

async function deleteManufacturer() {
  if (!selected.value) return
  if (!window.confirm(`删除厂商「${selected.value.name}」？\n\n有产品时会被拒绝；先合并到其他厂商。`)) return
  try {
    await api(`/api/v1/manufacturers/${selected.value.id}`, { method: 'DELETE' })
    selectedId.value = ''
    await loadManufacturers()
    flash('厂商已删除')
  } catch (exc) {
    flash(exc.message, true)
  }
}

async function mergeManufacturer() {
  if (!selected.value || !mergeTargetId.value) return
  const target = manufacturers.value.find((row) => row.id === mergeTargetId.value)
  if (!target) return
  if (!window.confirm(`把「${selected.value.name}」合并到「${target.name}」？\n\n产品、系列和审核关联都会移动。`)) return
  saving.value = true
  try {
    await api(`/api/v1/manufacturers/${selected.value.id}/merge`, {
      method: 'POST',
      body: JSON.stringify({ target_id: target.id }),
    })
    await loadManufacturers()
    selectedId.value = target.id
    await loadLines()
    syncForm()
    flash(`已合并到「${target.name}」`)
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    saving.value = false
  }
}

async function addLine() {
  if (!selected.value || !lineDraft.value.trim()) return
  try {
    await api('/api/v1/product-lines', {
      method: 'POST',
      body: JSON.stringify({ manufacturer_id: selected.value.id, name: lineDraft.value.trim() }),
    })
    lineDraft.value = ''
    await loadLines()
    await loadManufacturers()
    flash('系列已新增')
  } catch (exc) {
    flash(exc.message, true)
  }
}

async function renameLine(line, event) {
  const name = event.target.value.trim()
  if (!name || name === line.name) {
    event.target.value = line.name
    return
  }
  try {
    await api(`/api/v1/product-lines/${line.id}`, { method: 'PATCH', body: JSON.stringify({ name }) })
    await loadLines()
    flash('系列已改名')
  } catch (exc) {
    event.target.value = line.name
    flash(exc.message, true)
  }
}

async function deleteLine(line) {
  if (!window.confirm(`删除系列「${line.name}」？\n\n${line.product_count} 款产品会回到「未知」。`)) return
  try {
    const result = await api(`/api/v1/product-lines/${line.id}`, { method: 'DELETE' })
    await loadLines()
    await loadManufacturers()
    flash(`系列已删除；${result.products_reset} 款产品回到未知`)
  } catch (exc) {
    flash(exc.message, true)
  }
}

watch(selectedId, async () => {
  syncForm()
  await loadLines()
})

loadManufacturers()
</script>

<template>
  <section class="taxonomy-view">
    <header class="page-header">
      <div>
        <p class="eyebrow">后台管理</p>
        <h1>厂家管理</h1>
        <p class="page-subtitle">分类、等级、隐藏排序、系列都在这里维护。等级数字越大越靠后；前台不显示等级徽章。</p>
      </div>
      <div class="header-actions">
        <button class="secondary-button" type="button" :disabled="loading" @click="loadManufacturers"><RefreshCw :size="16" />刷新</button>
        <button class="primary-button" type="button" @click="creating = !creating"><Plus :size="17" />新建厂商</button>
      </div>
    </header>

    <form v-if="creating" class="create-panel" @submit.prevent="createManufacturer">
      <input v-model="createForm.name" placeholder="厂商名称，例如：猛虎模型" />
      <select v-model="createForm.category">
        <option value="">未分类</option>
        <option v-for="item in categoryOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-model.number="createForm.tier">
        <option :value="1">1 级</option><option :value="2">2 级</option><option :value="3">3 级</option>
      </select>
      <button class="primary-button" type="submit" :disabled="saving"><Save :size="16" />创建</button>
    </form>

    <div class="taxonomy-layout">
      <aside class="maker-pane">
        <div class="pane-toolbar">
          <input v-model="search" type="search" placeholder="搜索厂商" />
          <select v-model="categoryFilter">
            <option value="">全部分类</option>
            <option v-for="item in categoryOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            <option value="unclassified">未分类</option>
          </select>
        </div>
        <p v-if="loading" class="pane-empty"><LoaderCircle class="spin" :size="18" />读取中…</p>
        <div v-else class="maker-list">
          <button
            v-for="maker in filtered"
            :key="maker.id"
            type="button"
            class="maker-row"
            :class="{ active: selectedId === maker.id }"
            @click="selectedId = maker.id"
          >
            <span class="maker-row-main">
              <strong>{{ maker.name }}</strong>
              <small>{{ maker.product_count }} 款 · {{ maker.line_count }} 个系列</small>
            </span>
            <span class="maker-row-meta">
              <span class="category-badge" :class="maker.category || 'unclassified'">{{ categoryLabel(maker.category) }}</span>
              <small>T{{ maker.tier }}</small>
            </span>
          </button>
          <p v-if="!filtered.length" class="pane-empty">没有匹配的厂商。</p>
        </div>
      </aside>

      <main v-if="selected" class="detail-pane">
        <header class="detail-title">
          <div><span class="eyebrow">厂商</span><h2>{{ selected.name }}</h2></div>
          <span class="category-badge" :class="selected.category || 'unclassified'">{{ categoryLabel(selected.category) }}</span>
        </header>

        <div class="form-grid">
          <label><span>名称</span><input v-model="form.name" /></label>
          <label><span>分类</span>
            <select v-model="form.category">
              <option value="">未分类</option>
              <option v-for="item in categoryOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
          </label>
          <label><span>等级（数字越大越靠后）</span>
            <select v-model.number="form.tier"><option :value="1">1 级</option><option :value="2">2 级</option><option :value="3">3 级</option></select>
          </label>
          <label><span>同级隐藏排序</span><input v-model.number="form.sort_order" type="number" /></label>
          <label class="full"><span>描述</span><textarea v-model="form.description" rows="3"></textarea></label>
        </div>
        <div class="detail-actions">
          <button class="primary-button" type="button" :disabled="saving" @click="saveManufacturer"><Save :size="16" />保存</button>
          <button class="text-button danger-text" type="button" :disabled="saving" @click="deleteManufacturer"><Trash2 :size="16" />删除</button>
          <span class="spacer"></span>
          <select v-model="mergeTargetId">
            <option value="">合并到…</option>
            <option v-for="maker in mergeTargets" :key="maker.id" :value="maker.id">{{ maker.name }}</option>
          </select>
          <button class="secondary-button" type="button" :disabled="saving || !mergeTargetId" @click="mergeManufacturer">合并</button>
        </div>

        <section class="line-section">
          <header class="line-head">
            <h3><Building2 :size="15" />系列（{{ lines.length }}）</h3>
            <span class="hint">删除后，已绑定的产品回到“未知”</span>
          </header>
          <form class="line-add" @submit.prevent="addLine">
            <input v-model="lineDraft" placeholder="新增系列，例如：HG、HGUC、66系列" />
            <button class="secondary-button" type="submit" :disabled="!lineDraft.trim()"><Plus :size="15" />添加</button>
          </form>
          <ul class="line-list">
            <li v-for="line in lines" :key="line.id">
              <input :value="line.name" @change="renameLine(line, $event)" />
              <span class="line-count">{{ line.product_count }} 款</span>
              <button class="icon-button danger-text" type="button" aria-label="删除系列" @click="deleteLine(line)"><Trash2 :size="14" /></button>
            </li>
            <li v-if="!lines.length" class="line-empty">还没有系列。先添加一个。</li>
          </ul>
        </section>
      </main>
      <main v-else class="detail-pane empty-detail"><p>左边选一个厂商，或者新建一个。</p></main>
    </div>

    <p v-if="message" class="taxonomy-message" :class="{ 'is-error': messageError }">{{ message }}</p>
  </section>
</template>

<style scoped>
.taxonomy-layout { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 16px; }
.maker-pane, .detail-pane { background: #fff; border: 1px solid #d9e1dc; border-radius: 8px; }
.maker-pane { overflow: hidden; }
.pane-toolbar { display: grid; grid-template-columns: 1fr 120px; gap: 7px; padding: 12px; border-bottom: 1px solid #e7ece8; }
.pane-toolbar input, .pane-toolbar select { min-width: 0; padding: 7px 8px; color: #2c3b36; background: #fbfcfa; border: 1px solid #cfd9d4; border-radius: 5px; }
.maker-list { max-height: 66vh; overflow: auto; }
.maker-row { display: flex; justify-content: space-between; gap: 8px; width: 100%; padding: 10px 12px; text-align: left; background: transparent; border: 0; border-bottom: 1px solid #f0f3f1; }
.maker-row:hover { background: #f7faf7; }
.maker-row.active { background: #eef6f2; }
.maker-row-main { display: grid; min-width: 0; gap: 2px; }
.maker-row-main strong { overflow: hidden; color: #1d2b27; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.maker-row-main small, .maker-row-meta small { color: #87938f; font-size: 10px; }
.maker-row-meta { display: grid; justify-items: end; gap: 3px; }
.category-badge { display: inline-block; padding: 1px 6px; font-size: 10px; line-height: 1.5; border-radius: 999px; border: 1px solid #dfe6e1; }
.category-badge.gundam { color: #3f5f8a; background: #eef3fb; border-color: #d3dff0; }
.category-badge.guomo { color: #1f5b4c; background: #e8f3ee; border-color: #c9e2d7; }
.category-badge.ko { color: #8a5f18; background: #fdf6e7; border-color: #f0dfb8; }
.category-badge.unclassified { color: #8a8f8c; background: #f3f3f1; border-color: #e2e2df; }
.detail-pane { padding: 18px; }
.detail-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.detail-title h2 { margin: 3px 0 0; color: #1b2925; font-size: 21px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 18px 0; }
.form-grid label { display: grid; gap: 5px; color: #5d6d67; font-size: 12px; }
.form-grid label.full { grid-column: 1 / -1; }
.form-grid input, .form-grid select, .form-grid textarea { width: 100%; padding: 8px 10px; color: #22302b; background: #fbfcfa; border: 1px solid #cfd9d4; border-radius: 5px; }
.detail-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding-bottom: 16px; border-bottom: 1px solid #e7ece8; }
.spacer { flex: 1; }
.detail-actions select { padding: 7px 8px; border: 1px solid #cfd9d4; border-radius: 5px; }
.line-section { padding-top: 16px; }
.line-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.line-head h3 { display: flex; align-items: center; gap: 5px; margin: 0; color: #31443d; font-size: 14px; }
.hint { color: #98a39f; font-size: 11px; }
.line-add { display: flex; gap: 8px; margin: 10px 0; }
.line-add input { flex: 1; padding: 7px 9px; border: 1px solid #cfd9d4; border-radius: 5px; }
.line-list { display: grid; gap: 4px; margin: 0; padding: 0; list-style: none; }
.line-list li { display: grid; grid-template-columns: minmax(0, 1fr) auto 30px; gap: 8px; align-items: center; padding: 5px 0; border-bottom: 1px solid #f0f3f1; }
.line-list input { width: 100%; padding: 5px 7px; color: #2c3b36; background: transparent; border: 1px solid transparent; border-radius: 4px; }
.line-list input:hover { border-color: #dbe7e0; }
.line-list input:focus { background: #fff; border-color: #24705f; outline: none; }
.line-count { color: #87938f; font-size: 11px; white-space: nowrap; }
.line-empty { color: #98a39f; font-size: 12px; }
.danger-text { color: #a4402c; }
.create-panel { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 12px; margin-bottom: 14px; background: #fafbf8; border: 1px solid #d9e1dc; border-radius: 8px; }
.create-panel input, .create-panel select { padding: 8px 10px; border: 1px solid #cfd9d4; border-radius: 5px; }
.create-panel input { flex: 1 1 240px; }
.pane-empty { display: flex; align-items: center; gap: 6px; padding: 24px; color: #98a39f; font-size: 12px; }
.empty-detail { display: grid; place-items: center; min-height: 320px; color: #98a39f; }
.taxonomy-message { position: fixed; right: 28px; bottom: 28px; z-index: 60; padding: 10px 14px; color: #1f4a3c; font-size: 13px; background: #e8f5ec; border: 1px solid #b9d9c4; border-radius: 7px; }
.taxonomy-message.is-error { color: #8d3423; background: #fdeee9; border-color: #efc6ba; }
@media (max-width: 900px) {
  .taxonomy-layout { grid-template-columns: 1fr; }
  .maker-list { max-height: 40vh; }
}
</style>
