<script setup>
import { ref, watch } from 'vue'
import { Barcode, Building2, CalendarDays, ExternalLink, Tag, Trophy, Truck, Wallet, X } from 'lucide-vue-next'
import { channelLabel } from '../taxonomy'

const props = defineProps({ product: { type: Object, default: null } })
const emit = defineEmits(['close', 'open-collection'])

const collections = ref([])
const loadingCollections = ref(false)

watch(() => props.product?.id, async (id) => {
  collections.value = []
  if (!id) return
  loadingCollections.value = true
  try {
    const response = await fetch(`/api/v1/products/${id}/collections`)
    if (response.ok) collections.value = await response.json()
  } catch {
    /* the drawer's main job does not depend on this */
  } finally {
    loadingCollections.value = false
  }
}, { immediate: true })

function formatDate(value) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(new Date(value)) : '—'
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
          </div>
        </section>
        <dl class="detail-grid">
          <div><dt><Building2 :size="15" />厂商</dt><dd>{{ product.manufacturer || '未填写' }}</dd></div>
          <div><dt><Barcode :size="15" />产品编号</dt><dd>{{ product.product_code || '未填写' }}</dd></div>
          <div><dt><Tag :size="15" />系列</dt><dd>{{ product.product_line || '未填写' }}</dd></div>
          <div><dt><Truck :size="15" />渠道</dt><dd>{{ channelLabel(product.release_channel) }}</dd></div>
          <div><dt><Wallet :size="15" />价格</dt><dd>{{ product.price || '未记录' }}</dd></div>
          <div><dt><CalendarDays :size="15" />入库时间</dt><dd>{{ formatDate(product.created_at) }}</dd></div>
          <div><dt><ExternalLink :size="15" />资料来源</dt><dd class="source-text">{{ product.source }}</dd></div>
        </dl>
        <section class="detail-section">
          <h3>详情</h3>
          <p>{{ product.detail || '尚未补充产品详情。' }}</p>
        </section>
        <section class="detail-section">
          <h3><Trophy :size="15" />所属收藏</h3>
          <p v-if="loadingCollections" class="collection-empty">读取中…</p>
          <div v-else-if="collections.length" class="collection-chips">
            <button
              v-for="collection in collections"
              :key="collection.id"
              type="button"
              class="collection-chip"
              @click="emit('open-collection', collection.id)"
            >
              <Trophy :size="13" />{{ collection.title }}
              <span v-if="collection.owned" class="owned-mark">✓</span>
            </button>
          </div>
          <p v-else class="collection-empty">尚未加入收藏集。</p>
        </section>
      </aside>
    </div>
  </Transition>
</template>

<style scoped>
.source-text { overflow-wrap: anywhere; }
.collection-chips { display: flex; flex-wrap: wrap; gap: 7px; }
.collection-chip { display: inline-flex; align-items: center; gap: 5px; padding: 5px 9px; color: #2f554c; font-size: 12px; background: #f2f7f4; border: 1px solid #dbe7e0; border-radius: 999px; }
.collection-chip:hover { color: #fff; background: #24705f; border-color: #24705f; }
.owned-mark { color: #24705f; font-weight: 700; }
.collection-chip:hover .owned-mark { color: #fff; }
.collection-empty { margin: 0; color: #87938f; font-size: 12px; }
</style>
