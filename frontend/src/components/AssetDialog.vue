<script setup>
import { computed, ref, watch } from 'vue'
import { Save, Trash2, X } from 'lucide-vue-next'

const props = defineProps({
  asset: { type: Object, default: null },
})
const emit = defineEmits(['close', 'saved', 'removed'])

const STATE_META = {
  pending: '待拼',
  keep: '收藏',
  displayed: '展示',
  stored: '收纳',
  sold: '卖出',
}
const NEXT_ACTIONS = {
  pending: [['displayed', '拼完了'], ['keep', '收藏']],
  keep: [['pending', '改回待拼']],
  displayed: [['stored', '收纳'], ['sold', '卖出']],
  stored: [['displayed', '取出展示'], ['sold', '卖出']],
  sold: [],
}

const PRESETS = ['本体', '余件', '地台', '配件包']
const draftTitle = ref('配件包')
const form = ref({})
const audit = ref([])
const busy = ref(false)
const message = ref('')
const messageError = ref(false)

const asset = computed(() => props.asset)
const actions = computed(() => NEXT_ACTIONS[asset.value?.state] || [])

function flash(text, isError = false) {
  message.value = text
  messageError.value = isError
  window.clearTimeout(flash.timer)
  flash.timer = window.setTimeout(() => { message.value = '' }, 3000)
}

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options })
  const body = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) throw new Error(body?.detail || `请求失败 (${response.status})`)
  return body
}

watch(() => props.asset?.id, async (id) => {
  if (!id) return
  message.value = ''
  form.value = {
    acquired_on: props.asset.acquired_on || '',
    purchase_price: props.asset.purchase_price ?? '',
    built_on: props.asset.built_on || '',
    rating: props.asset.rating || 0,
    review: props.asset.review || '',
    sold_on: props.asset.sold_on || '',
    sold_price: props.asset.sold_price ?? '',
    note: props.asset.note || '',
  }
  try {
    audit.value = await api(`/api/v1/assets/${id}/state-changes`)
  } catch {
    audit.value = []
  }
}, { immediate: true })

function payload() {
  return {
    acquired_on: form.value.acquired_on || null,
    purchase_price: form.value.purchase_price === '' ? null : String(form.value.purchase_price),
    built_on: form.value.built_on || null,
    rating: form.value.rating || null,
    review: form.value.review.trim() || null,
    sold_on: form.value.sold_on || null,
    sold_price: form.value.sold_price === '' ? null : String(form.value.sold_price),
    note: form.value.note.trim() || null,
  }
}

async function save() {
  if (busy.value) return
  busy.value = true
  try {
    const updated = await api(`/api/v1/assets/${asset.value.id}`, { method: 'PATCH', body: JSON.stringify(payload()) })
    emit('saved', updated)
    flash('已保存')
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

async function moveTo(state) {
  if (busy.value) return
  busy.value = true
  try {
    const updated = await api(`/api/v1/assets/${asset.value.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ state }),
    })
    emit('saved', updated)
    flash(`状态改为「${STATE_META[state]}」`)
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

async function addTag() {
  if (busy.value || !asset.value) return
  const title = draftTitle.value.trim()
  if (!title) {
    flash('袋名不能为空', true)
    return
  }
  busy.value = true
  try {
    const tag = await api(`/api/v1/assets/${asset.value.id}/tags`, {
      method: 'POST',
      body: JSON.stringify({ title }),
    })
    flash(`${tag.code}（${tag.title}）已生成，去标签队列打印`)
  } catch (exc) {
    flash(exc.message, true)
  } finally {
    busy.value = false
  }
}

async function remove() {
  if (busy.value) return
  if (!window.confirm(`删除资产 ${asset.value.code}？\n\n编号不会回收，已打印的标签会变成历史。`)) return
  busy.value = true
  try {
    await api(`/api/v1/assets/${asset.value.id}`, { method: 'DELETE' })
    emit('removed', asset.value.id)
    emit('close')
  } catch (exc) {
    flash(exc.message, true)
    busy.value = false
  }
}
</script>

<template>
  <Transition name="drawer">
    <div v-if="asset" class="drawer-layer" @click.self="emit('close')">
      <aside class="product-drawer asset-drawer">
        <header>
          <div>
            <span class="eyebrow">{{ STATE_META[asset.state] }} · {{ asset.code }}</span>
            <h2>{{ asset.product?.kit_name || '未知产品' }}</h2>
            <p class="sub">{{ [asset.product?.manufacturer, asset.product?.product_line].filter(Boolean).join(' · ') }}</p>
          </div>
          <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')"><X :size="20" /></button>
        </header>

        <div class="state-row">
          <button v-for="[value, label] in actions" :key="value" class="secondary-button" type="button" :disabled="busy" @click="moveTo(value)">{{ label }}</button>
          <span v-if="!actions.length" class="sub">已卖出，无后续动作</span>
        </div>

        <section class="field-section">
          <h3>买卖与拼装</h3>
          <div class="field-grid">
            <label><span>买入日期</span><input v-model="form.acquired_on" type="date" /></label>
            <label><span>买入价</span><input v-model="form.purchase_price" inputmode="decimal" placeholder="买入价" /></label>
            <label><span>拼装日期</span><input v-model="form.built_on" type="date" /></label>
            <label><span>评分</span><select v-model.number="form.rating"><option :value="0">未评分</option><option v-for="n in 5" :key="n" :value="n">{{ '★'.repeat(n) }}</option></select></label>
            <label class="full"><span>评价</span><textarea v-model="form.review" rows="2" placeholder="关节松紧、分色、补色难度…"></textarea></label>
            <label><span>卖出日期</span><input v-model="form.sold_on" type="date" /></label>
            <label><span>卖出价</span><input v-model="form.sold_price" inputmode="decimal" /></label>
            <label class="full"><span>备注</span><textarea v-model="form.note" rows="2"></textarea></label>
          </div>
          <div class="save-row"><button class="primary-button" type="button" :disabled="busy" @click="save"><Save :size="16" />保存</button></div>
        </section>

        <section class="field-section">
          <header class="section-head">
            <h3>再加一个袋</h3>
            <span class="sub">地台、配件包在这里补；码按 -2、-3 往下排</span>
          </header>
          <div class="tag-add">
            <div class="presets">
              <button v-for="preset in PRESETS" :key="preset" type="button" :class="{ active: draftTitle === preset }" @click="draftTitle = preset">{{ preset }}</button>
            </div>
            <div class="tag-add-row">
              <input v-model="draftTitle" maxlength="24" placeholder="袋名，如 配件包 2" />
              <button class="secondary-button" type="button" :disabled="busy" @click="addTag">加一个</button>
            </div>
          </div>
        </section>

        <section class="field-section">
          <header class="section-head"><h3>状态记录</h3></header>
          <ul v-if="audit.length" class="audit-line">
            <li v-for="item in audit" :key="item.id">
              <span class="when">{{ (item.changed_at || '').slice(0, 10) }}</span>
              <span>{{ item.from_state ? `${STATE_META[item.from_state] || item.from_state} → ` : '建档 → ' }}{{ STATE_META[item.to_state] || item.to_state }}</span>
            </li>
          </ul>
          <p v-else class="sub">暂无记录</p>
        </section>

        <footer class="asset-footer">
          <button class="text-button danger" type="button" :disabled="busy" @click="remove"><Trash2 :size="15" />删除资产</button>
        </footer>
      </aside>
    </div>
  </Transition>

  <p v-if="message" class="asset-message" :class="{ 'is-error': messageError }">{{ message }}</p>
</template>

<style scoped>
.asset-drawer { width: min(100%, 520px); }
.eyebrow { margin-bottom: 4px; }
h2 { margin: 0; font-size: 21px; line-height: 1.35; color: #1b2925; }
.sub { margin: 4px 0 0; color: #7a8782; font-size: 12px; }
.state-row { display: flex; flex-wrap: wrap; gap: 8px; margin: 20px 0 6px; }
.field-section { padding-top: 18px; margin-top: 18px; border-top: 1px solid #e4eae6; }
.field-section h3 { display: flex; align-items: center; gap: 6px; margin: 0 0 10px; color: #31443d; font-size: 14px; }
.section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.field-grid label { display: grid; gap: 4px; color: #5d6d67; font-size: 12px; }
.field-grid label.full { grid-column: 1 / -1; }
.field-grid input, .field-grid select, .field-grid textarea { width: 100%; padding: 7px 9px; color: #22302b; background: #fbfcfa; border: 1px solid #cfd9d4; border-radius: 5px; }
.save-row { display: flex; justify-content: flex-end; margin-top: 12px; }
.audit-line { margin: 0; padding: 0; list-style: none; display: grid; gap: 4px; font-size: 12px; color: #5d6d67; }
.audit-line li { display: flex; gap: 10px; }
.when { color: #8b9793; font-variant-numeric: tabular-nums; }
.tag-add { display: grid; gap: 8px; }
.presets { display: flex; flex-wrap: wrap; gap: 6px; }
.presets button { padding: 4px 10px; color: #2f554c; font-size: 12px; background: #fff; border: 1px solid #cbd7d2; border-radius: 999px; }
.presets button:hover { background: #f4f8f5; }
.presets button.active { color: #fff; background: #24705f; border-color: #24705f; }
.tag-add-row { display: flex; gap: 8px; }
.tag-add-row input { flex: 1; min-width: 0; padding: 7px 9px; color: #22302b; background: #fbfcfa; border: 1px solid #cfd9d4; border-radius: 5px; }
.asset-footer { margin-top: 22px; padding-top: 14px; border-top: 1px solid #e4eae6; }
.danger { color: #a4402c; }
.asset-message { position: fixed; right: 28px; bottom: 28px; padding: 10px 14px; color: #1f4a3c; font-size: 13px; background: #e8f5ec; border: 1px solid #b9d9c4; border-radius: 7px; }
.asset-message.is-error { color: #8d3423; background: #fdeee9; border-color: #efc6ba; }
</style>
