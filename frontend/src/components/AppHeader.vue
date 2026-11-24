<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import FormCodeInput from './FormCodeInput.vue'

const auth = useAuthStore()
const router = useRouter()
async function logout() {
  if (auth.logoutRequested) return
  if (router.currentRoute.value.path === '/') { auth.logout(); return }
  // Удаляем токен только после разрешения редактора покинуть страницу.
  auth.logoutRequested = true
  try {
    await router.replace('/')
  } finally {
    auth.logoutRequested = false
  }
}
</script>

<template>
  <header class="app-header">
    <RouterLink to="/" class="logo">Конструктор</RouterLink>
    <nav aria-label="Главное меню">
      <template v-if="!auth.user">
        <RouterLink to="/login">Войти</RouterLink>
        <RouterLink to="/register">Регистрация</RouterLink>
      </template>
      <template v-else>
        <template v-if="auth.user.is_author">
          <RouterLink to="/my/forms">Мои опросы и тесты</RouterLink>
          <button disabled title="Раздел появится позже">Библиотека блоков</button>
        </template>
        <template v-else>
          <RouterLink to="/my/attempts">Мои прохождения</RouterLink>
          <details class="header-code"><summary>Ввести код</summary><FormCodeInput /></details>
        </template>
        <span>{{ auth.user.name }}</span>
        <button @click="logout">Выйти</button>
      </template>
    </nav>
  </header>
</template>
