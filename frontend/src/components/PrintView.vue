<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, LoaderCircle, Printer } from 'lucide-vue-next'

// ?preview=1 renders a fixed sample sheet (never the real queue, never marks
// anything printed) so the layout can be judged on screen.
const preview = new URLSearchParams(window.location.search).has('preview')
const PREVIEW_SAMPLE = [
  { id: 'p1', code: 'M-001', title: '本体', kit_name: '灵枪·马尔洛克', manufacturer: 'SNAA', product_line: '圆桌骑士团系列' },
  { id: 'p2', code: 'M-002', title: '本体', kit_name: '神器共鸣者·帕西瓦尔（豪华版）', manufacturer: 'SNAA', product_line: '圆桌骑士团系列' },
  { id: 'p3', code: 'M-003', title: '地台', kit_name: '雷鸣收割者·格雷斯', manufacturer: 'SNAA', product_line: '圆桌骑士团系列' },
  { id: 'p4', code: 'M-004', title: '本体', kit_name: '灵皇守护者·高文（KK版）', manufacturer: 'SNAA', product_line: '圆桌骑士团系列' },
  { id: 'p5', code: 'M-005-2', title: '余件', kit_name: '钢镰·凯', manufacturer: 'SNAA', product_line: '圆桌骑士团系列' },
]
const tags = ref([])
const loading = ref(true)
const error = ref('')
const status = ref('')

function splitName(name) {
  if (!name) return { main: '—', sub: null }
  const head = name.split('（')[0]
  if (head.includes('&')) {
    const [main, tail] = head.split('&')
    return { main: main.trim(), sub: tail.trim() || null }
  }
  const match = name.match(/^(.*?)（([^）]*)）/s)
  const sub = match ? match[2].split(/[、,，]/)[0].trim() : null
  return { main: head.trim(), sub: sub || null }
}

// The badge carries the bag name; the style only encodes the common presets so
// the three kinds stay distinguishable in pure black and white.
function badgeClass(title) {
  const value = title || '本体'
  if (value === '本体') return 'role-body'
  if (value.includes('地台')) return 'role-base'
  return 'role-extras'
}

const labels = computed(() => tags.value.map((tag) => {
  const { main, sub } = splitName(tag.kit_name)
  return {
    ...tag,
    main,
    sub,
    productLine: tag.product_line || '',
    badge: tag.title || '本体',
    badgeClass: badgeClass(tag.title),
  }
}))

async function load() {
  if (preview) {
    tags.value = PREVIEW_SAMPLE
    loading.value = false
    return
  }
  const raw = window.sessionStorage.getItem('print-tag-ids')
  const ids = raw ? new Set(JSON.parse(raw)) : new Set()
  if (!ids.size) {
    error.value = '没有选中标签。回到「标签队列」勾选后再打印。'
    loading.value = false
    return
  }
  try {
    const response = await fetch('/api/v1/tags?status=open&limit=2000')
    const all = await response.json()
    tags.value = all.filter((tag) => ids.has(tag.id))
    if (!tags.value.length) error.value = '选中的标签已经打印过，去标签队列的「已打印」里重新打印。'
  } catch (exc) {
    error.value = `读取失败：${exc.message}`
  } finally {
    loading.value = false
  }
}

function waitForImages() {
  const pending = [...document.images].filter((img) => !img.complete)
  return Promise.all(pending.map((img) => new Promise((resolve) => {
    img.onload = img.onerror = resolve
  })))
}

async function markPrinted() {
  const ids = tags.value.map((tag) => tag.id)
  if (!ids.length || preview) return
  try {
    await fetch('/api/v1/tags/bulk/printed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tag_ids: ids }),
    })
    status.value = `已打印 ${ids.length} 张，并标记为已贴`
  } catch (exc) {
    status.value = `打印完成，但标记失败：${exc.message}`
  }
}

async function doPrint() {
  window.print()
  await markPrinted()
}

function back() {
  window.sessionStorage.removeItem('print-tag-ids')
  window.location.hash = 'labels'
}

onMounted(async () => {
  await load()
  if (preview || !tags.value.length) return
  await waitForImages()
  // Give the browser a beat to finish layout before opening the dialog.
  window.setTimeout(doPrint, 300)
})
</script>

<template>
  <div class="print-page">
    <header class="print-toolbar">
      <button class="text-button" type="button" @click="back"><ArrowLeft :size="16" />返回标签队列</button>
      <span class="count">{{ labels.length }} 张 · 40 × 30 mm</span>
      <button class="primary-button" type="button" :disabled="!labels.length" @click="doPrint"><Printer :size="16" />重新打印</button>
    </header>

    <p v-if="status" class="print-status">{{ status }}</p>
    <p v-if="loading" class="print-empty"><LoaderCircle class="spin" :size="20" />准备标签…</p>
    <p v-else-if="error" class="print-empty">{{ error }}</p>

    <main v-else class="sheet">
      <article v-for="label in labels" :key="label.id" class="label">
        <!-- 1. 顶部栏：左侧厂商与系列，右侧部位标识 -->
        <header class="label-head">
          <div class="meta">
            <span v-if="label.manufacturer" class="maker">{{ label.manufacturer }}</span>
            <span v-if="label.manufacturer && label.productLine" class="sep">·</span>
            <span v-if="label.productLine" class="series">{{ label.productLine }}</span>
          </div>
          <span class="badge" :class="label.badgeClass">{{ label.badge }}</span>
        </header>

        <!-- 2. 下部主区：左侧机体名+编号，右侧二维码 -->
        <div class="label-body">
          <div class="info-col">
            <div class="title-group">
              <div class="title">{{ label.main }}</div>
              <div v-if="label.sub" class="sub">{{ label.sub }}</div>
            </div>
            <div class="code-box">
              <strong class="code">{{ label.code }}</strong>
            </div>
          </div>

          <div class="qr-col">
            <img class="qr" :src="`/api/v1/qr?data=${encodeURIComponent(label.code)}`" alt="" />
          </div>
        </div>
      </article>
    </main>
  </div>
</template>

<style scoped>
.print-page { min-height: 100vh; padding: 18px; background: #eef1ee; font-family: "PingFang SC", "Microsoft YaHei", "Heiti SC", sans-serif; }
.print-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; max-width: 900px; margin: 0 auto 16px; }
.print-toolbar .count { color: #5d6d67; font-size: 13px; }
.print-status { max-width: 900px; margin: 0 auto 12px; padding: 9px 12px; color: #1f4a3c; font-size: 13px; background: #e8f5ec; border: 1px solid #b9d9c4; border-radius: 6px; }
.print-empty { display: flex; align-items: center; justify-content: center; gap: 8px; min-height: 160px; color: #6d7b77; }

/* 纸张画布（默认 A4 拼版，屏幕预览带阴影） */
.sheet {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  width: 200mm;
  margin: 0 auto;
  padding: 5mm;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

/* 40x30mm 单张标签容器 */
.label {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  width: 40mm;
  height: 30mm;
  padding: 2mm 2.2mm;
  overflow: hidden;
  color: #000;
  background: #fff;
  outline: 0.2mm dashed #c8ccc9;
  page-break-inside: avoid;
  break-inside: avoid;
}

/* --- 1. 顶部栏：厂商 + 角色徽章 --- */
.label-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1mm;
  padding-bottom: 1.1mm;
  border-bottom: 0.35mm solid #000;
  flex: 0 0 auto;
}

.meta {
  display: flex;
  align-items: baseline;
  gap: 0.6mm;
  overflow: hidden;
  white-space: nowrap;
  font-size: 2.1mm;
  line-height: 1.1;
}

.maker {
  font-weight: 800;
  letter-spacing: 0.05mm;
  flex-shrink: 0;
}

.sep {
  font-weight: 700;
  flex-shrink: 0;
}

.series {
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

/* 部位徽章：利用黑白框区分不同类型（全黑白打印也极易分辨） */
.badge {
  flex: 0 0 auto;
  padding: 0.4mm 1mm;
  font-size: 2mm;
  font-weight: 800;
  line-height: 1;
  color: #fff;
  background: #000;
  border: 0.3mm solid #000;
  border-radius: 0.5mm;
}
/* 余件采用反白空心框，地台采用斜纹/粗框感，方便肉眼一秒分拣 */
.badge.role-extras {
  color: #000;
  background: #fff;
}
.badge.role-base {
  color: #000;
  background: #fff;
  border-style: dashed;
}

/* --- 2. 下部主区：左文右码 --- */
.label-body {
  display: flex;
  flex: 1;
  align-items: stretch;
  justify-content: space-between;
  gap: 1.5mm;
  padding-top: 1.3mm;
  overflow: hidden;
}

.info-col {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: space-between;
  min-width: 0;
   overflow: hidden;
}

.title-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.7mm;
}

.title {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2; /* 允许最多两行，防止长机体名被截断 */
  overflow: hidden;
  font-size: 3.3mm;
  font-weight: 800;
  line-height: 1.18;
  /* 中文按字断行，拉丁词不拆；两行时尽量平衡，避免出现「高」+「文」这种孤字 */
  word-break: keep-all;
  overflow-wrap: anywhere;
  text-wrap: balance;
}

.sub {
  display: inline-block;
  max-width: 100%;
  padding: 0.25mm 0.8mm;
  overflow: hidden;
  font-size: 2.1mm;
  font-weight: 600;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 0.25mm solid #000;
  border-radius: 0.4mm;
}

.code-box {
  padding-top: 0.6mm;
}

.code {
  display: block;
  overflow: hidden;
  font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, Consolas, monospace;
  font-size: 3.4mm;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.05mm;
  white-space: nowrap;
}

/* 右下角二维码区域 */
.qr-col {
  display: flex;
  flex: 0 0 auto;
   flex-direction: column;
  justify-content: flex-end;
}

.qr {
   display: block;
  width: 12mm;
  height: 12mm;
  object-fit: contain;
  /* 确保二维码像素边缘锐利，热敏打印不发虚 */
  image-rendering: -moz-crisp-edges;
  image-rendering: pixelated;
}

@media print {
  .print-page { padding: 0; background: #fff; }
  .print-toolbar, .print-status, .print-empty { display: none; }
  .sheet { padding: 0; margin: 0; box-shadow: none; }
  .label { outline: none; }
}

/* 默认：A4 不干胶拼版打印 (每行 5 张: 5 * 40mm = 200mm) */
@page { size: A4; margin: 5mm; }

/* 💡 如果你使用的是 40x30mm 独立热敏标签打印机（如佳博、精臣、得力等），
   可以把上面的 .sheet 宽度设为 40mm，并将 @page 替换为下面这行：
   @page { size: 40mm 30mm; margin: 0; }
*/
</style>