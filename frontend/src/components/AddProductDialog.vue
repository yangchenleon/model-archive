<script setup>
import { reactive, ref, watch } from 'vue'
import { LoaderCircle, Plus, X } from 'lucide-vue-next'
import ManufacturerPicker from './ManufacturerPicker.vue'
import { CHANNEL_OPTIONS } from '../taxonomy'

const props = defineProps({
  open: { type: Boolean, required: true },
  defaultManufacturerId: { type: String, default: '' },
})
const emit = defineEmits(['close', 'created'])

const manufacturers = ref([])
const lines = ref([])
const form = reactive({
  kit_name: '',
  manufacturer_id: '',
  product_code: '',
  product_line_id: '',
  release_channel: '',
  detail: '',
  source: '手动录入',
})
const submitting = ref(false)
const error = ref('')

async function loadManufacturers() {
  try {
    const response = await fetch('/api/v1/manufacturers?limit=500')
    if (!response.ok) throw new Error('厂商读取失败')
    manufacturers.value = await response.json()
  } catch (exc) {
    error.value = exc.message
  }
}

async function loadLines(manufacturerId = form.manufacturer_id) {
  if (!manufacturerId) {
    lines.value = []
    return
  }
  try {
    const response = await fetch(`/api/v1/product-lines?manufacturer_id=${manufacturerId}&limit=500`)
    if (!response.ok) throw new Error('系列读取失败')
    lines.value = await response.json()
  } catch {
    lines.value = []
  }
}

function onManufacturerChange() {
  form.product_line_id = ''
  loadLines()
}

watch(() => props.open, async (open) => {
  if (!open) return
  error.value = ''
  if (!manufacturers.value.length) await loadManufacturers()
  if (props.defaultManufacturerId) form.manufacturer_id = props.defaultManufacturerId
  await loadLines()
})

function valueOrNull(value) {
  const trimmed = value.trim()
  return trimmed || null
}

async function submit() {
  if (!form.kit_name.trim()) {
    error.value = '请填写产品名称。'
    return
  }
  if (!form.manufacturer_id) {
    error.value = '请选择厂商；没有就去「厂家管理」新建。'
    return
  }
  if (!form.source.trim()) {
    error.value = '请填写资料来源。'
    return
  }
  submitting.value = true
  error.value = ''
  try {
    const response = await fetch('/api/v1/products', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        kit_name: form.kit_name.trim(),
        manufacturer_id: form.manufacturer_id,
        product_line_id: form.product_line_id || null,
        release_channel: form.release_channel || null,
        source: form.source.trim(),
        product_code: valueOrNull(form.product_code),
        detail: valueOrNull(form.detail),
      }),
    })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(body.detail || '保存失败')
    Object.assign(form, {
      kit_name: '', manufacturer_id: '', product_code: '', product_line_id: '', release_channel: '', detail: '', source: '手动录入',
    })
    lines.value = []
    emit('created', body)
    emit('close')
  } catch (exc) {
    error.value = exc.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Transition name="dialog">
    <div v-if="open" class="dialog-layer">
      <form class="dialog" @submit.prevent="submit">
        <header>
          <div><span class="eyebrow">新增条目</span><h2>录入产品</h2></div>
          <button class="icon-button" type="button" aria-label="关闭录入窗口" @click="$emit('close')"><X :size="20" /></button>
        </header>
        <div class="form-grid">
          <label class="form-field full"><span>产品名称 <b>*</b></span><input v-model="form.kit_name" required autofocus placeholder="例如：MG 1/100 RX-78-2 Ver.Ka" /></label>
          <label class="form-field"><span>厂商 <b>*</b></span>
            <ManufacturerPicker
              v-model="form.manufacturer_id"
              :manufacturers="manufacturers"
              @change="onManufacturerChange"
            />
          </label>
          <label class="form-field"><span>产品编号</span><input v-model="form.product_code" placeholder="例如：MDH-12E / RG32" /></label>
          <label class="form-field"><span>系列</span>
            <select v-model="form.product_line_id">
              <option value="">未知</option>
              <option v-for="line in lines" :key="line.id" :value="line.id">{{ line.name }}</option>
            </select>
          </label>
          <label class="form-field"><span>渠道</span>
            <select v-model="form.release_channel">
              <option value="">未知</option>
              <option v-for="channel in CHANNEL_OPTIONS" :key="channel.value" :value="channel.value">{{ channel.label }}</option>
            </select>
          </label>
          <label class="form-field"><span>资料来源 <b>*</b></span><input v-model="form.source" required placeholder="手动录入" /></label>
          <label class="form-field full"><span>详情</span><textarea v-model="form.detail" rows="3" placeholder="可留空，后续完善即可"></textarea></label>
        </div>
        <p v-if="!manufacturers.length" class="form-hint">还没有厂商。先去「厂家管理」新建一个，再回来录入。</p>
        <p v-if="error" class="form-error">{{ error }}</p>
        <footer><button class="text-button" type="button" @click="$emit('close')">取消</button><button class="primary-button" type="submit" :disabled="submitting"><LoaderCircle v-if="submitting" class="spin" :size="17" /><Plus v-else :size="17" />保存产品</button></footer>
      </form>
    </div>
  </Transition>
</template>

<style scoped>
.form-hint { margin: 8px 0 0; color: #a4402c; font-size: 12px; }
</style>
