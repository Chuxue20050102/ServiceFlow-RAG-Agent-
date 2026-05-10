<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listKnowledgeDocuments, uploadKnowledgeDocument } from '@/api/serviceflow'
import type { KnowledgeDocument } from '@/types/serviceflow'

const documentName = ref('退款与支付处理规则')
const documentType = ref('支付处理规则')
const file = ref<File | null>(null)
const documents = ref<KnowledgeDocument[]>([])
const loading = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  file.value = target.files?.[0] ?? null
}

async function refreshDocuments() {
  documents.value = await listKnowledgeDocuments()
}

async function submit() {
  if (!file.value) {
    message.value = '请先选择 txt 或 md 规则文档。'
    messageType.value = 'error'
    return
  }
  loading.value = true
  message.value = ''
  try {
    await uploadKnowledgeDocument(documentName.value, documentType.value, file.value)
    message.value = '规则文档上传成功。'
    messageType.value = 'success'
    await refreshDocuments()
  } catch (error) {
    message.value = error instanceof Error ? error.message : '上传失败'
    messageType.value = 'error'
  } finally {
    loading.value = false
  }
}

onMounted(refreshDocuments)
</script>

<template>
  <main class="page">
    <section class="page-header">
      <div>
        <p class="eyebrow">RAG Knowledge Base</p>
        <h1>规则知识库</h1>
      </div>
      <RouterLink class="secondary-button" to="/tickets/upload">上传工单表</RouterLink>
    </section>

    <section class="panel form-panel">
      <label>
        文档名称
        <input v-model="documentName" />
      </label>
      <label>
        文档类型
        <select v-model="documentType">
          <option>退款规则</option>
          <option>支付处理规则</option>
          <option>账号问题处理流程</option>
          <option>客服回复话术</option>
          <option>课程故障处理流程</option>
        </select>
      </label>
      <label>
        规则文件
        <input accept=".txt,.md" type="file" @change="onFileChange" />
      </label>
      <button class="primary-button" :disabled="loading" @click="submit">
        <span v-if="loading" class="spinner"></span>
        {{ loading ? '处理中...' : '上传并切分' }}
      </button>
      <p v-if="message" class="message" :class="messageType">{{ message }}</p>
    </section>

    <section class="panel">
      <h2>已上传文档</h2>
      <div class="table-panel">
        <table>
          <thead>
            <tr>
              <th>文档名</th>
              <th>类型</th>
              <th>切分片段数</th>
              <th>上传时间</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in documents" :key="item.id">
              <td>{{ item.document_name }}</td>
              <td><span class="tag">{{ item.document_type }}</span></td>
              <td>{{ item.chunk_count }}</td>
              <td>{{ new Date(item.created_at).toLocaleString() }}</td>
              <td>
                <span :class="item.status === 'completed' ? 'badge badge-success' : item.status === 'processing' ? 'badge badge-warning' : 'badge badge-info'">
                  {{ item.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
</template>
