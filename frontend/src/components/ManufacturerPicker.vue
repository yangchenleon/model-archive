<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  manufacturers: { type: Array, default: () => [] },
  placeholder: { type: String, default: '搜索厂商' },
})
const emit = defineEmits(['update:modelValue', 'change'])

const query = ref('')
const open = ref(false)
const selected = computed(() => props.manufacturers.find((row) => row.id === props.modelValue) || null)
const filtered = computed(() => {
  const term = query.value.trim().toLowerCase()
  const rows = term
    ? props.manufacturers.filter((row) => row.name.toLowerCase().includes(term))
    : props.manufacturers
  return rows.slice(0, 60)
})

watch(() => props.modelValue, (id) => {
  const current = props.manufacturers.find((row) => row.id === id)
  if (current) query.value = current.name
  else if (!open.value) query.value = ''
}, { immediate: true })

watch(() => props.manufacturers, () => {
  const current = props.manufacturers.find((row) => row.id === props.modelValue)
  if (current) query.value = current.name
})

function onInput(event) {
  query.value = event.target.value
  open.value = true
  if (props.modelValue && selected.value?.name !== query.value) {
    emit('update:modelValue', '')
  }
}

function choose(row) {
  query.value = row.name
  open.value = false
  emit('update:modelValue', row.id)
  emit('change', row)
}
</script>

<template>
  <div class="maker-picker">
    <input
      :value="query"
      :placeholder="placeholder"
      autocomplete="off"
      @input="onInput"
      @focus="open = true"
      @blur="open = false"
    />
    <div v-if="open" class="picker-pop">
      <button
        v-for="row in filtered"
        :key="row.id"
        type="button"
        class="picker-row"
        @mousedown.prevent="choose(row)"
      >
        <span>{{ row.name }}</span>
        <small>{{ row.category || '未分类' }} · T{{ row.tier }}</small>
      </button>
      <p v-if="!filtered.length" class="picker-empty">没有匹配的厂商；去「厂家管理」新建后再回来。</p>
    </div>
  </div>
</template>

<style scoped>
.maker-picker { position: relative; }
.maker-picker input { width: 100%; }
.picker-pop { position: absolute; z-index: 50; top: calc(100% + 4px); left: 0; width: min(100%, 360px); max-height: 260px; padding: 4px; overflow: auto; background: #fff; border: 1px solid #cfd9d4; border-radius: 6px; box-shadow: 0 10px 28px #17271f26; }
.picker-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; width: 100%; padding: 7px 9px; text-align: left; color: #2c3b36; font-size: 12px; background: transparent; border: 0; border-radius: 4px; }
.picker-row:hover { background: #eef6f2; }
.picker-row small { color: #87938f; font-size: 10px; white-space: nowrap; }
.picker-empty { margin: 0; padding: 10px; color: #a4402c; font-size: 12px; }
</style>
