<script setup lang="ts">
const cards = [
  { label: '今日工单数', value: '0', hint: '待接入真实统计' },
  { label: '高优先级工单', value: '0', hint: '需优先处理' },
  { label: '待转技术工单', value: '0', hint: '需要协同' },
  { label: '已生成日报', value: '0', hint: '沉淀复盘' },
]

const capabilities = [
  '上传售后规则',
  '上传工单表格',
  'AI 自动分类分流',
  '生成回复模板',
  '生成客服日报',
]
</script>

<template>
  <main class="page">
    <section class="hero">
      <div class="hero-main">
        <p class="eyebrow">ServiceFlow RAG Agent</p>
        <h1>售后工单分流与处理建议系统</h1>
        <p class="hero-copy">
          上传公司售后规则与客服工单表，系统结合知识库为每条工单生成类型、优先级、
          责任部门、处理建议和可直接复制的回复模板。
        </p>
        <div class="hero-actions">
          <RouterLink class="primary-button" to="/knowledge">上传规则文档</RouterLink>
          <RouterLink class="secondary-button" to="/tickets/upload">上传工单表</RouterLink>
        </div>
      </div>

      <div class="hero-preview">
        <div class="preview-row strong">
          <span>支付 / 到账异常</span>
          <b>高</b>
        </div>
        <div class="preview-row">
          <span>责任部门</span>
          <b>技术团队 · 客服团队</b>
        </div>
        <div class="preview-row">
          <span>处理建议</span>
          <b>核查支付记录后同步会员状态</b>
        </div>
        <div class="preview-card">
          您好，我们已收到您的问题，会优先为您核查付款记录和会员到账状态，请您稍等。
        </div>
      </div>
    </section>

    <section class="stats-grid">
      <article v-for="card in cards" :key="card.label" class="stat-card">
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
        <small>{{ card.hint }}</small>
      </article>
    </section>

    <section class="panel workflow-panel">
      <div>
        <p class="eyebrow">Workflow</p>
        <h2>最小闭环</h2>
      </div>
      <div class="workflow-grid">
        <span v-for="item in capabilities" :key="item">{{ item }}</span>
      </div>
    </section>
  </main>
</template>
