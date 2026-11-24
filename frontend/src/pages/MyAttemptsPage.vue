<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { getMyAttempts } from '../api/attempts.js'
import { historyResult, filterAttempts, completionDate } from '../utils/participant.js'
import FormCodeInput from '../components/FormCodeInput.vue'
const router = useRouter(), auth = useAuthStore()
const attempts = ref([]), type = ref('all'), loading = ref(true), error = ref('')
const filtered = computed(() => filterAttempts(attempts.value, type.value))
async function load() {
  loading.value = true
  error.value = ''
  try { attempts.value = await getMyAttempts(auth.token) }
  catch (failure) {
    if (failure.status === 401) await router.replace({ path: '/login', query: { redirect: '/my/attempts' } })
    else error.value = failure.message
  } finally { loading.value = false }
}
function open(attempt) { if (attempt.is_finished) router.push(`/attempt/${attempt.attempt_id}/result`) }
onMounted(load)
</script>
<template>
  <section>
    <h1>Мои прохождения</h1><FormCodeInput />
    <label class="history-filter">Тип <select v-model="type"><option value="all">Все</option><option value="survey">Опросы</option><option value="test">Тесты</option></select></label>
    <p v-if="loading">Загрузка…</p>
    <div v-else-if="error"><p class="error" role="alert">{{ error }}</p><button @click="load">Повторить</button></div>
    <p v-else-if="!attempts.length">Вы ещё ничего не проходили</p>
    <p v-else-if="!filtered.length">Нет прохождений выбранного типа</p>
    <div v-else class="table-scroll"><table>
      <thead><tr><th>Название</th><th>Тип</th><th>Дата завершения</th><th>Результат</th></tr></thead>
      <tbody><tr v-for="attempt in filtered" :key="attempt.attempt_id" :class="{ 'history-link-row': attempt.is_finished }" @click="open(attempt)">
        <td><RouterLink v-if="attempt.is_finished" :to="`/attempt/${attempt.attempt_id}/result`" @click.stop>{{ attempt.form.title }}</RouterLink><span v-else>{{ attempt.form.title }}</span></td>
        <td>{{ attempt.form.is_test ? 'Тест' : 'Опрос' }}</td>
        <td>{{ attempt.is_finished ? completionDate(attempt.finished_at)?.toLocaleString() : 'не завершена' }}</td>
        <td>{{ historyResult(attempt) }}</td>
      </tr></tbody>
    </table></div>
  </section>
</template>
