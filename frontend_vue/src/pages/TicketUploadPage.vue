<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { analyzeTicketBatch, uploadTicketBatch } from '@/api/serviceflow'
import type { TicketBatch } from '@/types/serviceflow'

const router = useRouter()
const batchName = ref('2026年5月售后工单')
const file = ref<File | null>(null)
const batch = ref<TicketBatch | null>(null)
const loading = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  file.value = target.files?.[0] ?? null
  batch.value = null
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

    message.value = 'AI 正在分析工单，请稍等。'
    messageType.value = 'success'
    await analyzeTicketBatch(currentBatch.batch_id)
    router.push(`/tickets/result/${currentBatch.batch_id}`)
  } catch (error) {
    message.value = error instanceof Error ? error.message : '分析失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
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
