import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import LoginPage from '../pages/LoginPage.vue'
import RegisterPage from '../pages/RegisterPage.vue'
import MyFormsPage from '../pages/MyFormsPage.vue'
import FormEditorPage from '../pages/FormEditorPage.vue'
import MyAttemptsPage from '../pages/MyAttemptsPage.vue'
import NotFoundPage from '../pages/NotFoundPage.vue'
import { useAuthStore } from '../stores/auth.js'
import PublicFormPage from '../pages/PublicFormPage.vue'
import AttemptPage from '../pages/AttemptPage.vue'
import AttemptResultPage from '../pages/AttemptResultPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomePage },
    { path: '/f/:code', component: PublicFormPage },
    { path: '/attempt/:id', component: AttemptPage },
    { path: '/attempt/:id/result', component: AttemptResultPage },
    { path: '/login', component: LoginPage, meta: { guestOnly: true } },
    { path: '/register', component: RegisterPage, meta: { guestOnly: true } },
    { path: '/my/forms', component: MyFormsPage, meta: { requiresAuth: true, isAuthor: true } },
    { path: '/forms/:id/edit', component: FormEditorPage, meta: { requiresAuth: true, isAuthor: true } },
    { path: '/my/attempts', component: MyAttemptsPage, meta: { requiresAuth: true, isAuthor: false } },
    { path: '/:pathMatch(.*)*', component: NotFoundPage },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.initialize()
  if (to.path === '/' && auth.logoutRequested) auth.logout()
  if (!auth.user && (to.meta.requiresAuth || to.path.startsWith('/my/'))) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (auth.user && to.meta.guestOnly) return auth.homePath
  if (auth.user?.is_author && to.path === '/my/attempts') return auth.homePath
  // Оставляем исходный адрес, но App вместо закрытой страницы показывает «Нет доступа».
  to.meta.accessDenied = !!auth.user && to.meta.isAuthor !== undefined &&
    auth.user.is_author !== to.meta.isAuthor
})

export default router
