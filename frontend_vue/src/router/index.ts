import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '@/pages/HomePage.vue'
import KnowledgePage from '@/pages/KnowledgePage.vue'
import TicketReportPage from '@/pages/TicketReportPage.vue'
import TicketResultPage from '@/pages/TicketResultPage.vue'
import TicketUploadPage from '@/pages/TicketUploadPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomePage,
    },
    {
      path: '/knowledge',
      name: 'knowledge',
      component: KnowledgePage,
    },
    {
      path: '/tickets/upload',
      name: 'ticket-upload',
      component: TicketUploadPage,
    },
    {
      path: '/tickets/result/:batchId',
      name: 'ticket-result',
      component: TicketResultPage,
    },
    {
      path: '/tickets/report/:batchId',
      name: 'ticket-report',
      component: TicketReportPage,
    },
  ],
})

export default router

