import { createRouter, createWebHistory } from 'vue-router'
import WorkDetailPage from '../pages/WorkDetailPage.vue'
import WorksPage from '../pages/WorksPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'works',
      component: WorksPage,
    },
    {
      path: '/works/:id',
      name: 'work-detail',
      component: WorkDetailPage,
    },
  ],
})

export default router
