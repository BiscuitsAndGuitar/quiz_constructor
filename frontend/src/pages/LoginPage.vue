<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { safeRedirect } from '../utils/attempt.js'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const email = ref('')
const password = ref('')
const errorMessage = ref('')
const submitting = ref(false)

async function submit() {
  if (submitting.value) return
  errorMessage.value = ''
  submitting.value = true
  try {
    await auth.login({ email: email.value.trim().toLowerCase(), password: password.value })
    await router.replace(safeRedirect(route.query.redirect) || auth.homePath)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="auth-page">
    <h1>Вход</h1>
    <form novalidate @submit.prevent="submit">
      <div class="field">
        <label for="email">Email</label>
        <input id="email" v-model="email" type="email" autocomplete="username">
      </div>
      <div class="field">
        <label for="password">Пароль</label>
        <input id="password" v-model="password" type="password" autocomplete="current-password" aria-describedby="login-error">
        <p v-if="errorMessage" id="login-error" class="error" role="alert">{{ errorMessage }}</p>
      </div>
      <button :disabled="submitting">{{ submitting ? 'Входим…' : 'Войти' }}</button>
    </form>
    <p>Нет аккаунта? <RouterLink :to="{ path: '/register', query: { redirect: safeRedirect(route.query.redirect) || undefined } }">Зарегистрироваться</RouterLink></p>
  </section>
</template>
