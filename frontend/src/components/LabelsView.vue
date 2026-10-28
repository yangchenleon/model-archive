<script setup>
import { computed, onMounted, ref } from 'vue'
import { LoaderCircle, Printer, RefreshCw, Search } from 'lucide-vue-next'

const queue = ref([])
const loading = ref(true)
const error = ref('')
const search = ref('')
const selected = ref([])
const tab = ref('open')
const message = ref('')
const messageError = ref(false)

const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return queue.value
  return queue.value.filter((tag) =>
    [tag.code, tag.asset_code, tag.kit_name, tag.manufacturer]
      .filter(Boolean).join(' ').toLowerCase().includes(term))
})

const selectedSet = computed(() => new Set(selected.value))
const allChecked = computed(() => filtered.value.length > 0 && filtered.value.every((t) => selectedSet.value.has(t.id)))

function flash(text, isError = false) {
  message.value = text
  messageError.value = isError
  window.clearTimeout(flash.timer)
  flash.timer = window.setTimeout(() => { message.value = '' }, 3600)
}

async function api(path) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' } })
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new Error(body?.detail || `请求失败 (${response.status})`)
  return body
}

async function loadQueue() {
  loading.value = true
  error.value = ''
  try {
    queue.value = await api(`/api/v1/tags?status=${tab.value}`)
  } catch (exc) {
    error.value = `标签队列读取失败：${exc.message}`
  } finally {
    loading.value = false
  }
}

async function rename(tag, event) {
  const title = event.target.value.trim()
  if (!title || title === tag.title) {
    event.target.value = tag.title
    return
  }
  try {
    const updated = await fetch(`/api/v1/tags/${tag.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    }).then((response) => {
      if (!response.ok) throw new Error('改名失败')
      return response.json()
    })
    tag.title = updated.title
    flash(`已改名为「${updated.title}」`)
  } catch (exc) {
    event.target.value = tag.title
    flash(exc.message, true)
  }
}

function toggle(id) {
  const index = selected.value.indexOf(id)
  if (index >= 0) selected.value.splice(index, 1)
  else selected.value.push(id)
}

function switchTab(next) {
  if (tab.value === next) return
  tab.value = next
  selected.value = []
  loadQueue()
}

function toggleAll() {
  selected.value = allChecked.value ? [] : filtered.value.map((tag) => tag.id)
}

function print() {
  if (!selected.value.length) return
  window.sessionStorage.setItem('print-tag-ids', JSON.stringify(selected.value))
  window.location.hash = 'print'
}

onMounted(loadQueue)
</script>

<template>
  <section class="labels-view">
    <header class="page-header">
      <div>
        <p class="eyebrow">标签</p>
        <h1>标签队列</h1>
        <p class="page-subtitle">生成后待打印的贴纸。打印即视为已贴，不再手工勾选。</p>
      </div>
      <div class="header-actions">
        <button class="secondary-button" type="button" :disabled="loading" @click="loadQueue"><RefreshCw :size="16" />刷新</button>
        <button class="primary-button" type="button" :disabled="!selected.length" @click="print"><Printer :size="17" />打印所选（{{ selected.length }}）</button>
      </div>
    </header>

    <section class="toolbar">
      <label class="search-field"><Search :size="18" /><input v-model="search" type="search" placeholder="搜索标签码、资产编号、模型名" /></label>
      <span class="result-count">{{ selected.length ? `已选 ${selected.length} 张` : `${filtered.length} 张` }}</span>
      <div class="view-switch">
        <button :class="{ selected: tab === 'open' }" type="button" @click="switchTab('open')">待打印</button>
        <button :class="{ selected: tab === 'printed' }" type="button" @click="switchTab('printed')">已打印</button>
      </div>
    </section>

    <p v-if="loading" class="state-panel"><LoaderCircle class="spin" :size="24" />正在读取队列…</p>
    <p v-else-if="error" class="state-panel error-state">{{ error }}</p>
    <div v-else-if="filtered.length" class="label-table-wrap">
      <table class="label-table">
        <thead>
          <tr>
            <th class="check"><input type="checkbox" :checked="allChecked" @change="toggleAll" /></th>
            <th>标签码</th>
            <th>袋名</th>
            <th>资产</th>
            <th>产品</th>
            <th>厂商</th>
            <th>{{ tab === 'open' ? '生成' : '最近打印' }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="tag in filtered" :key="tag.id" :class="{ picked: selectedSet.has(tag.id) }" @click="toggle(tag.id)">
            <td class="check" @click.stop><input type="checkbox" :checked="selectedSet.has(tag.id)" @change="toggle(tag.id)" /></td>
            <td class="code">{{ tag.code }}</td>
            <td class="role" @click.stop>
              <input
                class="title-input"
                :value="tag.title"
                maxlength="24"
                title="点一下就能改名，码不变"
                @change="rename(tag, $event)"
              />
            </td>
            <td class="code">{{ tag.asset_code }}</td>
            <td class="name">{{ tag.kit_name }}</td>
            <td class="maker">{{ tag.manufacturer || '—' }}</td>
            <td class="date">{{ ((tab === 'open' ? tag.created_at : tag.printed_at) || '').slice(0, 10) || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="state-panel">
      <Printer :size="26" />
      <p>{{ queue.length ? '没有符合条件的标签。' : (tab === 'open' ? '队列是空的。去「我的资产」勾选后点「生成标签」。' : '还没有打印过的标签。') }}</p>
    </div>

    <p v-if="message" class="label-message" :class="{ 'is-error': messageError }">{{ message }}</p>
  </section>
</template>

<style scoped>
.header-actions { display: flex; gap: 8px; }
.label-table-wrap { overflow: auto; background: #fff; border: 1px solid #d9e1dc; border-radius: 8px; }
.label-table { width: 100%; min-width: 760px; border-collapse: collapse; font-size: 13px; }
.label-table th { padding: 9px 12px; color: #6b7774; font-size: 12px; font-weight: 500; text-align: left; background: #fafbf8; border-bottom: 1px solid #e3e9e4; }
.label-table td { padding: 9px 12px; color: #2c3b36; border-bottom: 1px solid #eff2ef; cursor: pointer; }
.label-table tbody tr:hover { background: #f7faf7; }
.label-table tbody tr.picked { background: #eef6f2; }
.label-table .check { width: 34px; cursor: default; }
.label-table .code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; white-space: nowrap; color: #1f332c; }
.label-table .role { color: #5d6d67; }
.title-input { width: 100%; min-width: 60px; padding: 2px 4px; color: #2f554c; font-size: 13px; background: transparent; border: 1px solid transparent; border-radius: 4px; }
.title-input:hover { border-color: #dbe7e0; }
.title-input:focus { background: #fff; border-color: #24705f; outline: none; }
.label-table .date { color: #87938f; font-variant-numeric: tabular-nums; }
.view-switch button { width: auto; padding: 0 12px; font-size: 12px; white-space: nowrap; }
.label-table .maker { color: #87938f; }
.state-panel { display: flex; align-items: center; justify-content: center; gap: 10px; min-height: 220px; color: #6d7b77; background: #fafbf8; border: 1px dashed #cbd6d0; border-radius: 8px; }
.state-panel.error-state { color: #9a452f; }
.label-message { position: fixed; right: 28px; bottom: 28px; padding: 10px 14px; color: #1f4a3c; font-size: 13px; background: #e8f5ec; border: 1px solid #b9d9c4; border-radius: 7px; }
.label-message.is-error { color: #8d3423; background: #fdeee9; border-color: #efc6ba; }
</style>
