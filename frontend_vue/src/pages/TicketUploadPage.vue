<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { analyzeTicketBatch, getAnalyzeStatus, uploadTicketBatch } from '@/api/serviceflow'
import type { AnalyzeResponse, TicketBatch } from '@/types/serviceflow'

const router = useRouter()
const batchName = ref('2026年5月售后工单')
const file = ref<File | null>(null)
const batch = ref<TicketBatch | null>(null)
const loading = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')
const analysisStatus = ref<AnalyzeResponse | null>(null)

const progressPercent = computed(() => analysisStatus.value?.progress_percent ?? 0)

const sleep = (ms: number) => new Promise((resolve) => window.setTimeout(resolve, ms))

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  file.value = target.files?.[0] ?? null
  batch.value = null
  analysisStatus.value = null
  message.value = ''
}

async function upload() {
  if (!file.value) {
    message.value = '请先选择 Excel 或 CSV 工单文件。'
    messageType.value = 'error'
    return null
  }

  const uploadedBatch = await uploadTicketBatch(batchName.value, file.value)
  batch.value = uploadedBatch
  message.value = '工单上传成功。'
  messageType.value = 'success'
  return uploadedBatch
}

async function uploadOnly() {
  loading.value = true
  message.value = ''
  analysisStatus.value = null
  try {
    await upload()
  } catch (error) {
    message.value = error instanceof Error ? error.message : '上传失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

async function analyze() {
  if (!file.value) {
    message.value = '请先选择 Excel 或 CSV 工单文件。'
    messageType.value = 'error'
    return
  }

  loading.value = true
  message.value = ''
  try {
    const currentBatch = batch.value ?? (await upload())
    if (!currentBatch) return

    message.value = 'AI 分析任务已开始，请稍等。'
    messageType.value = 'success'
    const started = await analyzeTicketBatch(currentBatch.batch_id)
    analysisStatus.value = started
    await waitForAnalysis(currentBatch.batch_id, started)
    router.push(`/tickets/result/${currentBatch.batch_id}`)
  } catch (error) {
    message.value = error instanceof Error ? error.message : '分析失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

async function waitForAnalysis(batchId: number, initialStatus: AnalyzeResponse) {
  let status = initialStatus
  for (let attempt = 0; attempt < 240; attempt += 1) {
    if (batch.value) {
      batch.value = { ...batch.value, status: status.status }
    }
    analysisStatus.value = status
    message.value = `AI 分析中：已完成 ${status.analyzed_count} 条，失败 ${status.failed_count} 条。`

    if (status.status === 'completed') {
      return
    }
    if (status.status === 'failed') {
      throw new Error('AI 分析失败，请查看后端日志。')
    }

    await sleep(1500)
    status = await getAnalyzeStatus(batchId)
  }

  throw new Error('AI 分析超时，请查看后端状态。')
}
</script>

<template>
  <main class="page">
    <section class="page-header">
      <div>
        <p class="eyebrow">Ticket Upload</p>
        <h1>工单上传与分析</h1>
      </div>
      <RouterLink class="secondary-button" to="/knowledge">规则知识库</RouterLink>
    </section>

    <section class="panel form-panel">
      <label>
        批次名称
        <input v-model="batchName" />
      </label>
      <label>
        工单文件
        <input accept=".csv,.xls,.xlsx" type="file" @change="onFileChange" />
      </label>
      <p class="hint">
        请上传包含 ticket_id、user_id、content、source、created_at 字段的 Excel / CSV 文件。
      </p>
      <div class="button-row">
        <button class="secondary-button" :disabled="!file || loading" @click="uploadOnly">
          只上传工单表
        </button>
        <button class="primary-button" :disabled="!file || loading" @click="analyze">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '处理中...' : '上传并开始 AI 分析' }}
        </button>
      </div>
      <div v-if="analysisStatus" class="progress-box">
        <div class="progress-meta">
          <span>AI 分析进度</span>
          <strong>{{ progressPercent }}%</strong>
        </div>
        <div class="progress-track">
          <span :style="{ width: `${progressPercent}%` }"></span>
        </div>
        <p>
          已完成 {{ analysisStatus.analyzed_count }} / {{ analysisStatus.total_count }} 条，
          失败 {{ analysisStatus.failed_count }} 条，状态 {{ analysisStatus.status }}
        </p>
      </div>
      <p v-if="message" class="message" :class="messageType">{{ message }}</p>
    </section>

    <section v-if="batch" class="panel success-panel">
      <h2>上传成功</h2>
      <p>批次 ID：{{ batch.batch_id }}</p>
      <p>工单数量：{{ batch.total_count }} 条</p>
      <p>状态：
        <span :class="batch.status === 'completed' ? 'badge badge-success' : 'badge badge-info'">
          {{ batch.status }}
        </span>
      </p>
    </section>
  </main>
</template>
