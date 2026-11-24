<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { getPublicForm, startAttempt } from '../api/attempts.js'
import { createAttemptState, saveAttempt, saveAttemptKey } from '../utils/attemptStorage.js'
import MessageDialog from '../components/MessageDialog.vue'
import NotFoundPage from './NotFoundPage.vue'

const route = useRoute(), router = useRouter(), auth = useAuthStore()
const form = ref(null), loading = ref(true), busy = ref(false), notFound = ref(false), failure = ref('')
const messages = ref(null)
async function load() {
  loading.value = true
  notFound.value = false
  failure.value = ''
  try { form.value = await getPublicForm(route.params.code, auth.token) }
  catch (error) {
    notFound.value = error.status === 404
    failure.value = error.message
    if (!notFound.value) messages.value?.show(error.detail || error.message)
  } finally { loading.value = false }
}
watch(() => [route.params.code, auth.token], load, { immediate: true })
async function start() {
  if (busy.value) return
  busy.value = true
  try {
    // Проверяем доступность хранилищ до того, как потратится попытка.
    for (const storage of [sessionStorage, localStorage]) {
      storage.setItem('quiz_storage_check', '1')
      storage.removeItem('quiz_storage_check')
    }
    const response = await startAttempt(form.value.id, auth.token)
    saveAttemptKey(localStorage, response.attempt.id, response.attempt.attempt_key)
    saveAttempt(sessionStorage, createAttemptState(response, route.params.code))
    await router.push(`/attempt/${response.attempt.id}`)
  } catch (error) {
    messages.value.show(error.detail || error.message || 'Разрешите хранение данных сайта для прохождения')
    if (error.status === 409) await load()
  } finally { busy.value = false }
}
</script>

<template>
  <p v-if="loading">Загрузка…</p>
  <NotFoundPage v-else-if="notFound" />
  <section v-else-if="failure"><p role="alert">{{ failure }}</p><button @click="load">Повторить</button></section>
  <p v-else-if="auth.user?.is_author">Составители не могут проходить формы</p>
  <section v-else-if="form">
    <h1>{{ form.title }}</h1><p>{{ form.is_test ? 'Тест' : 'Опрос' }}</p>
    <p class="plain-text">{{ form.description }}</p>
    <p v-if="form.time_limit_minutes">Время: {{ form.time_limit_minutes }} мин.</p>
    <p v-if="auth.user && form.max_attempts !== null">Попыток осталось {{ form.attempts_left }} из {{ form.max_attempts }}</p>
    <div v-if="form.requires_login && !auth.user">
      <p>Для прохождения войдите</p>
      <div class="actions">
        <RouterLink :to="{ path: '/login', query: { redirect: route.path } }">Войти</RouterLink>
        <RouterLink :to="{ path: '/register', query: { redirect: route.path } }">Зарегистрироваться</RouterLink>
      </div>
    </div>
    <div v-else-if="form.attempts_left === 0"><p>Попытки исчерпаны</p><RouterLink to="/my/attempts">Мои прохождения</RouterLink></div>
    <div v-else><button :disabled="busy" @click="start">{{ busy ? 'Начинаем…' : 'Начать' }}</button>
      <p class="hint">Попытка считается использованной с момента начала</p></div>
  </section>
  <MessageDialog ref="messages" />
</template>
