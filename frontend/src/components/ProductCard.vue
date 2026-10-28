<script setup>
import { Barcode, Building2, Plus, Tag } from 'lucide-vue-next'

defineProps({
  product: { type: Object, required: true },
  view: { type: String, default: 'grid' },
})

defineEmits(['select', 'own'])

function shortName(name) {
  return name.length > 46 ? `${name.slice(0, 46)}...` : name
}
</script>

<template>
  <article class="product-card" :class="`is-${view}`" @click="$emit('select', product)">
    <div class="product-thumb" :title="product.kit_name">
      <span>{{ shortName(product.kit_name) }}</span>
    </div>
    <div class="product-card-content">
      <div class="product-card-heading">
        <h3>{{ product.kit_name }}</h3>
      </div>
      <div class="meta-row">
        <span v-if="product.manufacturer"><Building2 :size="14" />{{ product.manufacturer }}</span>
        <span v-if="product.product_code"><Barcode :size="14" />{{ product.product_code }}</span>
        <span v-if="product.product_line"><Tag :size="14" />{{ product.product_line }}</span>
        <span v-if="product.price" class="price-tag">{{ product.price }}</span>
      </div>
      <footer>
        <span>来源：{{ product.source }}</span>
        <button class="own-button" type="button" title="加入资产（待拼）" @click.stop="$emit('own', product)">
          <Plus :size="13" />已有
        </button>
      </footer>
    </div>
  </article>
</template>

<style scoped>
.price-tag { color: #245a4c; font-variant-numeric: tabular-nums; }
footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
footer > span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.own-button { display: inline-flex; flex: 0 0 auto; align-items: center; gap: 3px; padding: 3px 8px; color: #2f554c; font-size: 11px; background: #f2f7f4; border: 1px solid #dbe7e0; border-radius: 999px; white-space: nowrap; }
.own-button:hover { color: #fff; background: #24705f; border-color: #24705f; }
</style>
