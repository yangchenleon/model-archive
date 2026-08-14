<script setup>
import { reactive, ref, watch } from 'vue'
import { LoaderCircle, Plus, X } from 'lucide-vue-next'

const props = defineProps({ open: { type: Boolean, required: true } })
const emit = defineEmits(['close', 'created'])

const form = reactive({
  kit_name: '',
  manufacturer: '',
  origin_type: '',
  product_line: '',
  variant_name: '',
  detail: '',
  source: '手动录入',
})
const submitting = ref(false)
const error = ref('')

watch(() => props.open, (open) => {
  if (open) error.value = ''
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
        source: form.source.trim(),
        manufacturer: valueOrNull(form.manufacturer),
        origin_type: valueOrNull(form.origin_type),
        product_line: valueOrNull(form.product_line),
        variant_name: valueOrNull(form.variant_name),
        detail: valueOrNull(form.detail),
      }),
    })
    if (!response.ok) throw new Error('保存失败')
    const product = await response.json()
    Object.assign(form, { kit_name: '', manufacturer: '', origin_type: '', product_line: '', variant_name: '', detail: '', source: '手动录入' })
    emit('created', product)
    emit('close')
  } catch {
    error.value = '无法连接资料库，请检查 API 服务是否运行。'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Transition name="dialog">
    <div v-if="open" class="dialog-layer" @click.self="$emit('close')">
      <form class="dialog" @submit.prevent="submit">
        <header>
          <div><span class="eyebrow">新增条目</span><h2>录入产品</h2></div>
          <button class="icon-button" type="button" aria-label="关闭录入窗口" @click="$emit('close')"><X :size="20" /></button>
        </header>
        <div class="form-grid">
          <label class="form-field full"><span>产品名称 <b>*</b></span><input v-model="form.kit_name" required autofocus placeholder="例如：MG 1/100 RX-78-2 Ver.Ka" /></label>
          <label class="form-field"><span>厂商</span><input v-model="form.manufacturer" placeholder="万代 / 大班 ..." /></label>
          <label class="form-field"><span>产品线</span><input v-model="form.product_line" placeholder="MG / HG / RG ..." /></label>
          <label class="form-field"><span>来源类型</span><input v-model="form.origin_type" placeholder="正版 / 国模原创 / KO ..." /></label>
          <label class="form-field"><span>变体名称</span><input v-model="form.variant_name" placeholder="可留空" /></label>
          <label class="form-field full"><span>详情</span><textarea v-model="form.detail" rows="3" placeholder="可留空，后续完善即可"></textarea></label>
          <label class="form-field full"><span>资料来源 <b>*</b></span><input v-model="form.source" required placeholder="手动录入" /></label>
        </div>
        <p v-if="error" class="form-error">{{ error }}</p>
        <footer><button class="text-button" type="button" @click="$emit('close')">取消</button><button class="primary-button" type="submit" :disabled="submitting"><LoaderCircle v-if="submitting" class="spin" :size="17" /><Plus v-else :size="17" />保存产品</button></footer>
      </form>
    </div>
  </Transition>
</template>
