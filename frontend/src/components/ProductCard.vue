<script setup>
import { Building2, Tag } from 'lucide-vue-next'

defineProps({
  product: { type: Object, required: true },
  view: { type: String, default: 'grid' },
})

defineEmits(['select'])

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
        <span v-if="product.origin_type" class="origin-tag">{{ product.origin_type }}</span>
      </div>
      <p v-if="product.variant_name" class="variant">{{ product.variant_name }}</p>
      <div class="meta-row">
        <span v-if="product.manufacturer"><Building2 :size="14" />{{ product.manufacturer }}</span>
        <span v-if="product.product_line"><Tag :size="14" />{{ product.product_line }}</span>
      </div>
      <footer>来源：{{ product.source }}</footer>
    </div>
  </article>
</template>
