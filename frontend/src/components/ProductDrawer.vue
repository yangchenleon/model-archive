<script setup>
import { Barcode, Building2, CalendarDays, Copy, ExternalLink, Tag, X } from 'lucide-vue-next'

defineProps({ product: { type: Object, default: null } })
defineEmits(['close'])

function formatDate(value) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(new Date(value)) : '-'
}
</script>

<template>
  <Transition name="drawer">
    <div v-if="product" class="drawer-layer" @click.self="$emit('close')">
      <aside class="product-drawer" aria-label="产品详情">
        <header>
          <span class="eyebrow">产品详情</span>
          <button class="icon-button" type="button" aria-label="关闭详情" @click="$emit('close')"><X :size="20" /></button>
        </header>
        <div class="drawer-thumb"><span>{{ product.kit_name }}</span></div>
        <section class="drawer-title">
          <div>
            <h2>{{ product.kit_name }}</h2>
            <p>{{ product.variant_name || '未记录变体名称' }}</p>
          </div>
          <span v-if="product.origin_type" class="origin-tag">{{ product.origin_type }}</span>
        </section>
        <dl class="detail-grid">
          <div><dt><Building2 :size="15" />厂商</dt><dd>{{ product.manufacturer || '未填写' }}</dd></div>
          <div><dt><Barcode :size="15" />厂家编号</dt><dd>{{ product.manufacturer_code || '未填写' }}</dd></div>
          <div><dt><Tag :size="15" />产品线</dt><dd>{{ product.product_line || '未填写' }}</dd></div>
          <div><dt><Copy :size="15" />资料来源</dt><dd>{{ product.source }}</dd></div>
          <div><dt><CalendarDays :size="15" />入库时间</dt><dd>{{ formatDate(product.created_at) }}</dd></div>
        </dl>
        <section class="detail-section">
          <h3>详情</h3>
          <p>{{ product.detail || '尚未补充产品详情。' }}</p>
        </section>
        <div class="drawer-actions">
          <button type="button" class="secondary-button" disabled title="资产模块仍为模拟功能"><ExternalLink :size="16" />关联资产</button>
        </div>
      </aside>
    </div>
  </Transition>
</template>
