<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

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
    const redirect = route.query.redirect
    // Возврат только на внутренний адрес приложения.
    const safe = typeof redirect === 'string' && redirect.startsWith('/') &&
      !redirect.startsWith('//') && !redirect.includes('\\')
    await router.replace(safe ? redirect : auth.homePath)
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
    <p>Нет аккаунта? <RouterLink to="/register">Зарегистрироваться</RouterLink></p>
  </section>
</template>
