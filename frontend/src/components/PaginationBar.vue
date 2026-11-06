<script setup>
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

const props = defineProps({
  page: { type: Number, default: 1 },
  pageCount: { type: Number, default: 1 },
  total: { type: Number, default: 0 },
  pageSize: { type: Number, default: 0 },
  pageSizeOptions: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:page', 'update:pageSize'])

function go(step) {
  const next = Math.min(Math.max(1, props.page + step), Math.max(1, props.pageCount))
  if (next !== props.page) emit('update:page', next)
}

function changeSize(event) {
  emit('update:pageSize', Number(event.target.value))
  emit('update:page', 1)
}
</script>

<template>
  <nav v-if="total > 0" class="pagination-bar" aria-label="分页">
    <span class="pagination-total">共 {{ total }} 项</span>
    <label v-if="pageSizeOptions.length" class="pagination-size">
      每页
      <select :value="pageSize" aria-label="每页数量" @change="changeSize">
        <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }}</option>
      </select>
      条
    </label>
    <span class="pagination-page">第 {{ page }} / {{ pageCount }} 页</span>
    <div class="pagination-actions">
      <button type="button" :disabled="page <= 1" @click="go(-1)"><ChevronLeft :size="15" />上一页</button>
      <button type="button" :disabled="page >= pageCount" @click="go(1)">下一页<ChevronRight :size="15" /></button>
    </div>
  </nav>
</template>

<style scoped>
.pagination-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; margin-top: 18px; padding-top: 14px; color: #6b7774; font-size: 12px; border-top: 1px solid #e7ece8; }
.pagination-total { color: #52645e; font-weight: 600; }
.pagination-size { display: inline-flex; align-items: center; gap: 5px; }
.pagination-size select { min-height: 30px; padding: 0 6px; color: #315a52; background: #fff; border: 1px solid #cbd7d2; border-radius: 5px; font-size: 12px; }
.pagination-page { font-variant-numeric: tabular-nums; }
.pagination-actions { display: flex; gap: 6px; margin-left: auto; }
.pagination-actions button { display: inline-flex; align-items: center; gap: 4px; min-height: 32px; padding: 0 10px; color: #315a52; font-size: 12px; font-weight: 600; background: #fff; border: 1px solid #cbd7d2; border-radius: 6px; }
.pagination-actions button:hover:not(:disabled) { background: #f4f8f5; }
.pagination-actions button:disabled { color: #a8b2ae; background: #fafbf8; }
@media (max-width: 650px) {
  .pagination-actions { margin-left: 0; }
}
</style>
