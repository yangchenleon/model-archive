<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, LoaderCircle, Printer } from 'lucide-vue-next'

// ?preview=1 renders a fixed sample sheet (never the real queue, never marks
// anything printed) so the layout can be judged on screen.
const preview = new URLSearchParams(window.location.search).has('preview')
const PREVIEW_SAMPLE = [
  { id: 'p1', code: 'DVG1D', title: '本体', kit_name: 'MB 红异端改战术复合武装（飞行背包）', manufacturer: '大班', product_line: '88系列' },
  { id: 'p2', code: 'R4TB9', title: '本体', kit_name: '神器共鸣者·帕西瓦尔（豪华版）', manufacturer: 'SNAA', product_line: '圆桌骑士团系列' },
  { id: 'p3', code: 'W8NZ3', title: '地台', kit_name: '雷鸣收割者·格雷斯', manufacturer: 'SNAA', product_line: '圆桌骑士团系列' },
  { id: 'p4', code: 'C5PV7', title: '本体', kit_name: '灵皇守护者·高文（KK版）', manufacturer: 'SNAA', product_line: '圆桌骑士团系列' },
  { id: 'p5', code: 'PMZXX', title: '本体', kit_name: '巨鸣斧·兰斯洛特', manufacturer: 'SNAA', product_line: '圆桌骑士团系列' },
]
const tags = ref([])
const loading = ref(true)
const error = ref('')
const status = ref('')

// 优化标点符号避头尾，避免斜杠 / 或左括号（ 留在行末，同时保持中英文自然连排
function formatKitName(name) {
  if (!name) return '—'
  return name
    .trim()
    // 防止英文与汉字之间的空格导致整串汉字提前换行（转为不间断空格或微距）
    .replace(/([A-Za-z0-9])\s+(?=[\u4e00-\u9fa5])/g, '$1\u00A0')
    // 斜杠、& 符号后方锁死不断行，避免留在行末
    .replace(/\s*([/&／])\s*/g, '\u200B$1\u2060')
    // 中点 · 紧贴前字，避免出现在行首
    .replace(/·/g, '\u2060·\u200B')
    // 左括号后锁死不断行（禁止左括号在行末）
    .replace(/([（(])/g, '$1\u2060')
    // 右括号前锁死不断行（禁止右括号在行首）
    .replace(/([）)])/g, '\u2060$1')
}

function badgeClass(title) {
  const value = title || '本体'
  if (value === '本体') return 'role-body'
  if (value.includes('地台')) return 'role-base'
  return 'role-extras'
}

const labels = computed(() => tags.value.map((tag) => {
  return {
    ...tag,
    displayName: formatKitName(tag.kit_name),
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
    if (!tags.value.length) error.value = '选中的标签已不在待打印队列，刷新标签队列后再试。'
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

        <!-- 2. 主体区：类 Word 文本框四周环绕排版 -->
        <div class="label-body">
          <!-- 右上角隐形撑开器（宽度为0，把二维码推到右下角，释放二维码上方的全部横向空间给第1~2行标题） -->
          <div class="qr-spacer"></div>

          <!-- 右下角二维码框（浮动在右下角，第3~4行长文字会自动环绕在它的左侧、即编码的上方） -->
          <div class="qr-box">
            <img class="qr" :src="`/api/v1/qr?data=${encodeURIComponent(label.code)}`" alt="" />
          </div>

          <!-- 机体名称（自然流式环绕：前两行全宽，第三四行自动缩进填满编码上方空白） -->
          <div class="title">{{ label.displayName }}</div>

          <!-- 左下角编码框（固定在左下角） -->
          <div class="code-box">
            <strong class="code">{{ label.code }}</strong>
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

/* --- 1. 顶部栏：恢复原尺寸（2.1mm / 2.0mm）确保「SNAA·圆桌骑士团系列」完整显示 --- */
.label-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1mm;
  padding-bottom: 1mm;
  border-bottom: 0.35mm solid #000;
  flex: 0 0 auto;
}

.meta {
  display: flex;
  align-items: baseline;
  gap: 0.6mm;
  overflow: hidden;
  white-space: nowrap;
  /* 最初是 2.1mm，这里设为 2.15mm 刚好完整放下「SNAA · 圆桌骑士团系列」 */
  font-size: 2.15mm;
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

.badge {
  flex: 0 0 auto;
  padding: 0.4mm 1mm;
  /* 恢复最初的 2mm */
  font-size: 2mm;
  font-weight: 800;
  line-height: 1;
  color: #fff;
  background: #000;
  border: 0.3mm solid #000;
  border-radius: 0.5mm;
}
.badge.role-extras {
  color: #000;
  background: #fff;
}
.badge.role-base {
  color: #000;
  background: #fff;
  border-style: dashed;
}

/* --- 2. 下部主区：Word 式四周文本环绕布局 --- */
.label-body {
  position: relative;
  flex: 1;
  padding-top: 1.2mm;
  overflow: hidden;
}

/* 顶部隐形推块：宽度为 0，高度约等于前 2 行文字（8.2mm），把下方的二维码精准推到右下角 */
.qr-spacer {
  float: right;
  width: 0;
  height: 8.2mm;
}

/* 右下角正方形二维码框：紧贴在推块下方（即右下角），文字流到这里会自动绕开它 */
.qr-box {
  float: right;
  clear: right;
  width: 12mm;
  height: 12mm;
  margin-left: 1.2mm;
  margin-top: 0.3mm;
  display: flex;
  align-items: center;
  justify-content: center;
}

.qr {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  image-rendering: -moz-crisp-edges;
  image-rendering: pixelated;
}

/* 机体名称：
   - 第 1~2 行：占满整张标签宽度（约 21~22 个字）
   - 第 3~4 行：自动环绕在二维码左侧、填满编码上方的空白（额外多容纳 12~14 个字，总计可容纳 35 字以上！） */
.title {
  font-size: 3.2mm;
  font-weight: 800;
  line-height: 1.25;
  /* 关键修复：使用 normal 而不是 keep-all，防止 MB 后面跟一长串汉字时直接断行 */
  word-break: normal;
  overflow-wrap: break-word;
  line-break: strict;
  /* 限制最大高度，避免极端超长文本压到左下角的编码（16mm 足够排下完整 4 行） */
  max-height: 16mm;
  overflow: hidden;
}

/* 左下角编码框：固定在左下角，背景兜底防重叠 */
.code-box {
  position: absolute;
  left: 0;
  bottom: 0;
  background: #fff;
  padding-right: 1mm;
  padding-top: 0.4mm;
}

.code {
  display: block;
  font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, Consolas, monospace;
  font-size: 3.5mm;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.05mm;
  white-space: nowrap;
}

@media print {
  .print-page { padding: 0; background: #fff; }
  .print-toolbar, .print-status, .print-empty { display: none; }
  .sheet { padding: 0; margin: 0; box-shadow: none; }
  .label { outline: none; }
}

@page { size: A4; margin: 5mm; }
</style>