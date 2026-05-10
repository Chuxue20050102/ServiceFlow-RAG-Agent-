<script setup lang="ts">
import * as echarts from 'echarts'
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { generateTicketReport, getTicketItems, getTicketSummary } from '@/api/serviceflow'
import type { TicketItem, TicketSummary } from '@/types/serviceflow'

const route = useRoute()
const router = useRouter()
const batchId = Number(route.params.batchId)

const summary = ref<TicketSummary | null>(null)
const items = ref<TicketItem[]>([])
const loading = ref(false)
const message = ref('')
const traceItem = ref<TicketItem | null>(null)

const typeChartRef = ref<HTMLElement | null>(null)
const severityChartRef = ref<HTMLElement | null>(null)
const teamChartRef = ref<HTMLElement | null>(null)

function severityBadge(level?: string | null) {
  const map: Record<string, string> = {
    高: 'badge badge-danger',
    中: 'badge badge-warning',
    低: 'badge badge-success',
  }
  return map[level ?? ''] ?? 'badge badge-info'
}

async function loadData() {
  loading.value = true
  try {
    const [summaryData, itemData] = await Promise.all([
      getTicketSummary(batchId),
      getTicketItems(batchId),
    ])
    summary.value = summaryData
    items.value = itemData
  } catch (error) {
    message.value = error instanceof Error ? error.message : '加载失败'
  } finally {
    loading.value = false
  }
}

async function createReport() {
  loading.value = true
  try {
    await generateTicketReport(batchId)
    router.push(`/tickets/report/${batchId}`)
  } catch (error) {
    message.value = error instanceof Error ? error.message : '日报生成失败'
  } finally {
    loading.value = false
  }
}

async function copyReply(text?: string | null) {
  if (!text) return
  await navigator.clipboard.writeText(text)
  message.value = '回复模板已复制。'
}

function openTrace(item: TicketItem) {
  traceItem.value = item
}

function closeTrace() {
  traceItem.value = null
}

function renderCharts() {
  if (!summary.value) return
  renderDonutChart(typeChartRef.value, summary.value.type_stats, ['#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#1d4ed8'])
  renderDonutChart(severityChartRef.value, summary.value.severity_stats, ['#dc2626', '#f59e0b', '#16a34a'])
  renderDonutChart(teamChartRef.value, summary.value.team_stats, ['#7c3aed', '#8b5cf6', '#a78bfa', '#6d28d9'])
}

function renderDonutChart(el: HTMLElement | null, stats: Record<string, number>, colors: string[]) {
  if (!el) return
  const chart = echarts.init(el)
  const data = Object.entries(stats).map(([name, value]) => ({ name, value }))

  chart.setOption({
    color: colors,
    tooltip: {
      trigger: 'item',
      formatter: '{b}<br/>{c} 条 · {d}%',
    },
    legend: {
      bottom: 0,
      type: 'scroll',
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: '#667085', fontSize: 12 },
    },
    series: [
      {
        type: 'pie',
        radius: ['54%', '74%'],
        center: ['50%', '43%'],
        avoidLabelOverlap: true,
        data,
        label: {
          formatter: '{b}\n{d}%',
          color: '#344054',
          fontSize: 12,
          lineHeight: 16,
        },
        labelLine: {
          length: 12,
          length2: 8,
          lineStyle: { color: '#98a2b3' },
        },
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 3,
          borderRadius: 4,
        },
      },
    ],
  })
}

watch(summary, async () => {
  await nextTick()
  renderCharts()
})

onMounted(loadData)
</script>

<template>
  <main class="page result-page">
    <section class="page-header result-header">
      <div>
        <p class="eyebrow">Ticket Result</p>
        <h1>分析结果</h1>
      </div>
      <button class="primary-button" :disabled="loading" @click="createReport">
        {{ loading ? '生成中...' : '生成客服日报' }}
      </button>
    </section>

    <p v-if="message" class="message">{{ message }}</p>

    <section v-if="summary" class="stats-grid">
      <article class="stat-card">
        <span>工单总数</span>
        <strong>{{ summary.total_count }}</strong>
        <small>已完成 AI 分析</small>
      </article>
      <article class="stat-card">
        <span>高优先级</span>
        <strong>{{ summary.high_severity_count }}</strong>
        <small>需要优先跟进</small>
      </article>
      <article class="stat-card">
        <span>最多类型</span>
        <strong>{{ summary.top_ticket_type }}</strong>
        <small>高频问题方向</small>
      </article>
      <article class="stat-card">
        <span>主要责任部门</span>
        <strong>{{ summary.top_responsible_team }}</strong>
        <small>建议重点协同</small>
      </article>
    </section>

    <section v-if="summary" class="chart-grid">
      <article class="panel chart-card">
        <div class="panel-title-row">
          <h2>工单类型占比</h2>
          <span>按类型统计</span>
        </div>
        <div ref="typeChartRef" class="echart"></div>
      </article>
      <article class="panel chart-card">
        <div class="panel-title-row">
          <h2>严重程度占比</h2>
          <span>按优先级统计</span>
        </div>
        <div ref="severityChartRef" class="echart"></div>
      </article>
      <article class="panel chart-card">
        <div class="panel-title-row">
          <h2>责任部门占比</h2>
          <span>按协同部门统计</span>
        </div>
        <div ref="teamChartRef" class="echart"></div>
      </article>
    </section>

    <section class="panel table-panel">
      <div class="panel-title-row">
        <h2>工单处理结果</h2>
        <span>{{ items.length }} 条记录</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>原始问题</th>
            <th>类型</th>
            <th>严重程度</th>
            <th>责任部门</th>
            <th>处理建议</th>
            <th>回复模板</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td class="content-cell">{{ item.content }}</td>
            <td><span class="tag">{{ item.ticket_type }}</span></td>
            <td><span :class="severityBadge(item.severity)">{{ item.severity }}</span></td>
            <td>{{ item.responsible_team }}</td>
            <td>{{ item.suggestion }}</td>
            <td>{{ item.reply_template }}</td>
            <td>
              <div class="table-actions">
                <button class="small-button" @click="copyReply(item.reply_template)">复制</button>
                <button class="small-button secondary-small" @click="openTrace(item)">Trace</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <div v-if="traceItem" class="modal-mask" @click.self="closeTrace">
      <section class="trace-modal">
        <header>
          <div>
            <p class="eyebrow">Agent Trace</p>
            <h2>{{ traceItem.ticket_id }} · {{ traceItem.ticket_type }}</h2>
          </div>
          <button class="secondary-button" @click="closeTrace">关闭</button>
        </header>

        <div class="trace-status">
          <span :class="traceItem.parse_success ? 'badge badge-success' : 'badge badge-danger'">
            {{ traceItem.parse_success ? 'JSON 解析成功' : 'JSON 解析失败' }}
          </span>
          <span class="tag">规则片段 {{ traceItem.matched_rules.length }}</span>
        </div>

        <article class="trace-section">
          <h3>检索到的规则</h3>
          <div v-if="traceItem.matched_rules.length" class="trace-list">
            <pre v-for="(rule, index) in traceItem.matched_rules" :key="index">{{ rule }}</pre>
          </div>
          <p v-else class="hint">没有检索到匹配规则。</p>
        </article>

        <article class="trace-section">
          <h3>模型原始输出</h3>
          <pre>{{ traceItem.raw_ai_result || '暂无模型输出。' }}</pre>
        </article>

        <article v-if="traceItem.parse_error" class="trace-section">
          <h3>解析错误</h3>
          <pre>{{ traceItem.parse_error }}</pre>
        </article>
      </section>
    </div>
  </main>
</template>

