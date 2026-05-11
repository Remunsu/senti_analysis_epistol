import { createRouter, createWebHistory } from 'vue-router'
import NotFoundPage from '../pages/NotFoundPage.vue'
import UploadPage from '../pages/UploadPage.vue'
import VolumeDetailPage from '../pages/VolumeDetailPage.vue'
import VolumesPage from '../pages/VolumesPage.vue'
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
    {
      path: '/volumes',
      name: 'volumes',
      component: VolumesPage,
    },
    {
      path: '/volumes/:id',
      name: 'volume-detail',
      component: VolumeDetailPage,
    },
    {
      path: '/upload',
      name: 'upload',
      component: UploadPage,
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFoundPage,
    },
  ],
})

export default router
