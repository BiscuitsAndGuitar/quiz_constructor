<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { getAttemptResult } from '../api/attempts.js'
const route = useRoute(), auth = useAuthStore()
const result = ref(null), error = ref(''), loading = ref(true)
async function load() {
  loading.value = true
  error.value = ''
  try { result.value = await getAttemptResult(route.params.id, auth.token) }
  catch (failure) {
    error.value = { 401: 'Для просмотра результата войдите в аккаунт или откройте его в браузере, где проходили форму.',
      403: 'Нет доступа к этой попытке.', 404: 'Попытка не найдена.', 409: 'Попытка ещё не завершена.' }[failure.status] || failure.message
  } finally { loading.value = false }
}
watch(() => route.params.id, load, { immediate: true })
</script>

<template>
  <section>
    <h1>Результат</h1>
    <p v-if="loading">Загрузка…</p>
    <div v-else-if="error"><p role="alert">{{ error }}</p><button @click="load">Повторить</button></div>
    <template v-else-if="result">
      <h2 v-if="result.is_test">{{ result.score }} из {{ result.max_score }}, {{ result.percent }}%<template v-if="result.grade !== null">, оценка {{ result.grade }}</template></h2>
      <p class="plain-text">{{ result.message }}</p>
      <p v-if="result.is_test && result.better_than_percent !== null">Вы справились лучше, чем {{ result.better_than_percent }}% участников</p>
      <div v-if="result.block_results !== null && result.block_results" class="table-scroll">
        <table><caption>Результаты по блокам</caption><thead><tr><th>Блок</th><th>Баллы</th><th>Процент</th></tr></thead>
          <tbody><tr v-for="(block, index) in result.block_results" :key="block.block_id"><td>{{ block.title || `Блок ${index + 1}` }}</td><td>{{ block.score }} из {{ block.max_score }}</td><td>{{ block.percent }}%</td></tr></tbody>
        </table>
      </div>
      <section v-if="result.review"><h2>Разбор ответов</h2>
        <article v-for="(question, index) in result.review" :key="question.question_id" class="attempt-question">
          <h3>{{ index + 1 }}. {{ question.text }}</h3>
          <p>Баллы: {{ question.score }} из {{ question.max_points }}</p>
          <template v-if="question.your_options">
            <p>Ваш ответ:</p><p v-if="!question.your_options.length">Нет ответа</p>
            <ul><li v-for="option in question.your_options" :key="option.id" :class="question.correct_option_ids.includes(option.id) ? 'right-answer' : 'wrong-answer'">
              {{ option.text }} — {{ question.correct_option_ids.includes(option.id) ? 'верно' : 'неверно' }}
            </li></ul>
            <p>Правильный ответ:</p><ul><li v-for="option in question.correct_options" :key="option.id" class="right-answer">{{ option.text }}</li></ul>
          </template>
          <template v-else>
            <p class="plain-text" :class="question.score === question.max_points ? 'right-answer' : 'wrong-answer'">Ваш ответ: {{ question.your_text || 'Нет ответа' }} ({{ question.score === question.max_points ? 'верно' : 'неверно' }})</p>
            <p>Допустимые ответы:</p><ul><li v-for="text in question.correct_text_answers" :key="text" class="right-answer plain-text">{{ text }}</li></ul>
          </template>
        </article>
      </section>
    </template>
    <div class="actions"><RouterLink to="/">На главную</RouterLink><RouterLink v-if="auth.user" to="/my/attempts">Мои прохождения</RouterLink></div>
    <p v-if="!auth.user"><RouterLink to="/register">Зарегистрируйтесь</RouterLink>, чтобы сохранять историю прохождений</p>
  </section>
</template>
