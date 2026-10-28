<script setup>
import { Barcode, Building2, Check, Plus, Tag } from 'lucide-vue-next'

defineProps({
  product: { type: Object, required: true },
  view: { type: String, default: 'grid' },
  owned: { type: Number, default: 0 },
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
      <em v-if="owned" class="owned-badge">×{{ owned }}</em>
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
        <button
          class="own-button"
          :class="{ 'is-owned': owned }"
          type="button"
          :title="owned ? `已入库 ${owned} 台，点一下再入一台` : '加入资产（待拼）'"
          @click.stop="$emit('own', product)"
        >
          <template v-if="owned">
            <span class="state-owned"><Check :size="13" />已入 {{ owned }}</span>
            <span class="state-again"><Plus :size="13" />再入一台</span>
          </template>
          <template v-else><Plus :size="13" />已有</template>
        </button>
      </footer>
    </div>
  </article>
</template>

<style scoped>
.price-tag { color: #245a4c; font-variant-numeric: tabular-nums; }
footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
footer > span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 已入库的数量压在封面上，扫一眼就知道这盒有没有录过 */
.owned-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 7px;
  color: #eaf3ee;
  font-size: 11px;
  font-style: normal;
  font-weight: 600;
  background: #24705fcc;
  border-radius: 999px;
}
.product-thumb { position: relative; }

.own-button {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 3px;
  padding: 3px 8px;
  color: #2f554c;
  font-size: 11px;
  white-space: nowrap;
  background: #f2f7f4;
  border: 1px solid #dbe7e0;
  border-radius: 999px;
  transition: color .15s ease, background .15s ease, border-color .15s ease;
}
.own-button:hover { color: #fff; background: #24705f; border-color: #24705f; }

/* 已入库：默认显示状态，悬停才露出“再入一台” */
.own-button.is-owned { color: #556b64; background: #fff; border-color: #d5e0da; }
.own-button.is-owned .state-again { display: none; }
.own-button.is-owned:hover { color: #fff; background: #24705f; border-color: #24705f; }
.own-button.is-owned:hover .state-owned { display: none; }
.own-button.is-owned:hover .state-again { display: inline-flex; align-items: center; gap: 3px; }
.state-owned { display: inline-flex; align-items: center; gap: 3px; }
</style>
