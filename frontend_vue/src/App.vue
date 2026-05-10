<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">S</span>
        <span>
          <strong>ServiceFlow</strong>
          <small>RAG Agent</small>
        </span>
      </RouterLink>

      <div class="side-section">导航</div>
      <nav class="side-nav">
        <RouterLink to="/">工作台</RouterLink>
        <RouterLink to="/knowledge">规则知识库</RouterLink>
        <RouterLink to="/tickets/upload">工单上传</RouterLink>
      </nav>

      <div class="side-footer">
        <div class="sf-icon">AI</div>
        <span class="sf-label">Powered by RAG</span>
        <span class="sf-text">工单分流 · 规则检索 · 回复生成</span>
      </div>
    </aside>

    <RouterView v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
  </div>
</template>

<style>
.page-enter-active,
.page-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
