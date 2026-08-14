<script setup>
import { Archive, Boxes, ClipboardList, Heart, LayoutDashboard } from 'lucide-vue-next'

defineProps({
  active: { type: String, required: true },
  total: { type: Number, required: true },
})

const emit = defineEmits(['change'])

const items = [
  { id: 'directory', label: '产品目录', icon: Archive },
  { id: 'inventory', label: '资产清点', icon: Boxes, mock: true },
  { id: 'wishlist', label: '愿望单', icon: Heart, mock: true },
  { id: 'activity', label: '活动记录', icon: ClipboardList, mock: true },
]
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true"><LayoutDashboard :size="19" /></div>
      <div>
        <strong>模型档案室</strong>
        <span>Model Archive</span>
      </div>
    </div>

    <nav aria-label="主导航">
      <button
        v-for="item in items"
        :key="item.id"
        class="nav-item"
        :class="{ active: active === item.id }"
        type="button"
        @click="emit('change', item.id)"
      >
        <component :is="item.icon" :size="18" />
        <span>{{ item.label }}</span>
        <small v-if="item.id === 'directory'">{{ total }}</small>
        <small v-else-if="item.mock">模拟</small>
      </button>
    </nav>

    <div class="sidebar-footer">
      <span class="status-dot" aria-hidden="true"></span>
      <span>本地资料库</span>
    </div>
  </aside>
</template>
