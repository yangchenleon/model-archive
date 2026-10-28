<script setup>
import { computed } from 'vue'

const props = defineProps({
  built: { type: Number, default: 0 },
  owned: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  height: { type: Number, default: 10 },
})

const percent = (value) => (props.total > 0 ? Math.max(0, Math.min(100, (value / props.total) * 100)) : 0)
const builtWidth = computed(() => percent(props.built))
const unbuiltWidth = computed(() => percent(Math.max(0, props.owned - props.built)))
const hasTotal = computed(() => props.total > 0)
</script>

<template>
  <div
    class="collection-progress"
    :class="{ empty: !hasTotal }"
    :style="{ height: `${height}px` }"
    :role="hasTotal ? 'progressbar' : undefined"
    :aria-valuemin="hasTotal ? 0 : undefined"
    :aria-valuemax="hasTotal ? total : undefined"
    :aria-valuenow="hasTotal ? owned : undefined"
    :aria-label="hasTotal ? `已拥有 ${owned} / ${total}` : '尚未定义范围'"
  >
    <span class="segment built" :style="{ width: `${builtWidth}%` }"></span>
    <span class="segment unbuilt" :style="{ width: `${unbuiltWidth}%` }"></span>
  </div>
</template>

<style scoped>
.collection-progress {
  display: flex;
  overflow: hidden;
  background: #e6e9e6;
  border-radius: 999px;
}
.collection-progress.empty {
  background: transparent;
  border: 1px dashed #cbd6d0;
}
.segment {
  display: block;
  height: 100%;
  transition: width .3s ease;
}
.segment.built { background: #1f6f5c; }
.segment.unbuilt { background: #8fc7b4; }
</style>
