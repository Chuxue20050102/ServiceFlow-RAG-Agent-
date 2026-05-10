<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { generateTicketReport, getTicketReport } from '@/api/serviceflow'
import type { TicketReport } from '@/types/serviceflow'

const route = useRoute()
const batchId = Number(route.params.batchId)
const report = ref<TicketReport | null>(null)
const loading = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

async function loadReport() {
  loading.value = true
  try {
    report.value = await getTicketReport(batchId)
  } catch (error) {
    message.value = error instanceof Error ? error.message : '日报加载失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

async function regenerate() {
  loading.value = true
  try {
    report.value = await generateTicketReport(batchId)
    message.value = '日报已重新生成。'
    messageType.value = 'success'
  } catch (error) {
    message.value = error instanceof Error ? error.message : '重新生成失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

async function copyReport() {
  if (!report.value) return
  await navigator.clipboard.writeText(report.value.content)
  message.value = '日报已复制。'
  messageType.value = 'success'
}

onMounted(loadReport)
</script>

<template>
  <main class="page">
    <section class="page-header">
      <div>
        <p class="eyebrow">Daily Report</p>
        <h1>{{ report?.title ?? '客服工单分析日报' }}</h1>
      </div>
      <div class="button-row">
        <button class="secondary-button" :disabled="loading" @click="copyReport">复制日报</button>
        <button class="primary-button" :disabled="loading" @click="regenerate">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '生成中...' : '重新生成' }}
        </button>
        <RouterLink class="secondary-button" :to="`/tickets/result/${batchId}`">返回结果</RouterLink>
      </div>
    </section>

    <p v-if="message" class="message" :class="messageType">{{ message }}</p>

    <!-- Loading skeleton -->
    <article v-if="loading && !report" class="panel report-content">
      <div class="skeleton" style="width:60%;height:22px;margin-bottom:16px;"></div>
      <div class="skeleton" style="width:100%;height:14px;margin-bottom:10px;"></div>
      <div class="skeleton" style="width:100%;height:14px;margin-bottom:10px;"></div>
      <div class="skeleton" style="width:80%;height:14px;margin-bottom:10px;"></div>
      <div class="skeleton" style="width:90%;height:14px;margin-bottom:10px;"></div>
      <div class="skeleton" style="width:70%;height:14px;margin-bottom:10px;"></div>
    </article>

    <article v-if="report" class="panel report-content">
      <pre>{{ report.content }}</pre>
    </article>
  </main>
</template>
