<script setup>
import { Archive, Boxes, ClipboardCheck, Factory, LayoutDashboard, Printer, Settings, Trophy } from 'lucide-vue-next'

defineProps({
  active: { type: String, required: true },
  total: { type: Number, required: true },
  pending: { type: Number, default: 0 },
  later: { type: Number, default: 0 },
})

const emit = defineEmits(['change'])

// 分组表达优先级：目录与资产是日常，入库审核只是「来源」之一，管理页是维护。
// 它曾经和目录平级，让人误以为审核是核心流程。
const groups = [
  {
    label: '',
    items: [
      { id: 'directory', label: '产品目录', icon: Archive },
      { id: 'inventory', label: '我的资产', icon: Boxes },
      { id: 'collections', label: '收藏集', icon: Trophy },
    ],
  },
  {
    label: '来源',
    items: [
      { id: 'review', label: '入库审核', icon: ClipboardCheck },
      { id: 'labels', label: '标签队列', icon: Printer },
    ],
  },
  {
    label: '维护',
    items: [
      { id: 'admin', label: '后台管理', icon: Settings },
      { id: 'taxonomy', label: '厂家管理', icon: Factory },
    ],
  },
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
      <template v-for="group in groups" :key="group.label || 'main'">
        <p v-if="group.label" class="nav-group">{{ group.label }}</p>
        <button
          v-for="item in group.items"
          :key="item.id"
          class="nav-item"
          :class="{ active: active === item.id }"
          type="button"
          @click="emit('change', item.id)"
        >
          <component :is="item.icon" :size="18" />
          <span>{{ item.label }}</span>
          <small v-if="item.id === 'directory'">{{ total }}</small>
          <small v-else-if="item.id === 'review' && pending + later">{{ pending + later }}</small>
        </button>
      </template>
    </nav>

    <div class="sidebar-footer">
      <span class="status-dot" aria-hidden="true"></span>
      <span>本地资料库</span>
    </div>
  </aside>
</template>

<style scoped>
.nav-group { margin: 14px 0 4px; padding: 0 10px; color: #9aa6a1; font-size: 10px; letter-spacing: .12em; text-transform: uppercase; }
</style>
