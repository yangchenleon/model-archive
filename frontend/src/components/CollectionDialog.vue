<script setup>
import { reactive, ref, watch } from 'vue'
import { LoaderCircle, Save, X } from 'lucide-vue-next'
import { COLLECTION_STATUSES } from '../collectionMeta'

const props = defineProps({
  open: { type: Boolean, default: false },
  collection: { type: Object, default: null },
})
const emit = defineEmits(['close', 'saved'])

const form = reactive({
  title: '',
  description: '',
  status: 'active',
  started_on: '',
  target_on: '',
})
const busy = ref(false)
const error = ref('')

function reset() {
  error.value = ''
  form.title = props.collection?.title || ''
  form.description = props.collection?.description || ''
  form.status = props.collection?.status || 'active'
  form.started_on = props.collection?.started_on || ''
  form.target_on = props.collection?.target_on || ''
}

watch(
  () => [props.open, props.collection?.id],
  ([open]) => {
    if (open) reset()
  },
  { immediate: true },
)

function valueOrNull(value) {
  const trimmed = value.trim()
  return trimmed || null
}

async function submit() {
  if (busy.value) return
  if (!form.title.trim()) {
    error.value = '请填写收藏集名称。'
    return
  }
  busy.value = true
  error.value = ''
  try {
    const editing = Boolean(props.collection)
    const response = await fetch(editing ? `/api/v1/collections/${props.collection.id}` : '/api/v1/collections', {
      method: editing ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: form.title.trim(),
        description: valueOrNull(form.description),
        status: form.status,
        started_on: form.started_on || null,
        target_on: form.target_on || null,
      }),
    })
    const body = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(body.detail || `保存失败 (${response.status})`)
    emit('saved', body)
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
      <form class="dialog" @submit.prevent="submit">
        <header>
          <div>
            <span class="eyebrow">{{ collection ? '编辑收藏集' : '新建收藏集' }}</span>
            <h2>{{ collection ? collection.title : '定义一个范围' }}</h2>
            <p class="dialog-hint">范围就是清单。只加入已经录入的产品；还没录入的，先在产品目录补。</p>
          </div>
          <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')"><X :size="20" /></button>
        </header>

        <div class="form-grid">
          <label class="form-field full"><span>名称 <b>*</b></span><input v-model="form.title" required autofocus maxlength="160" placeholder="例如：RG 扎古全制霸" /></label>
          <label class="form-field"><span>状态</span>
            <select v-model="form.status">
              <option v-for="item in COLLECTION_STATUSES" :key="item.value" :value="item.value">{{ item.label }}（{{ item.hint }}）</option>
            </select>
          </label>
          <label class="form-field"><span>开始日期</span><input v-model="form.started_on" type="date" /></label>
          <label class="form-field"><span>目标日期</span><input v-model="form.target_on" type="date" /></label>
          <label class="form-field full"><span>描述</span><textarea v-model="form.description" rows="4" placeholder="为什么收、只收哪些版本、难度和注意事项都写在这里。"></textarea></label>
        </div>

        <p v-if="error" class="form-error">{{ error }}</p>
        <footer>
          <button class="text-button" type="button" @click="emit('close')">取消</button>
          <button class="primary-button" type="submit" :disabled="busy">
            <LoaderCircle v-if="busy" class="spin" :size="17" /><Save v-else :size="17" />
            {{ collection ? '保存' : '创建' }}
          </button>
        </footer>
      </form>
    </div>
  </Transition>
</template>

<style scoped>
.dialog { width: min(100%, 640px); }
.dialog-hint { margin: 6px 0 0; color: #71807c; font-size: 12px; }
</style>
