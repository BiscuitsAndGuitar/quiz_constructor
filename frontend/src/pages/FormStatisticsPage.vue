<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { getStatistics, getStatisticsForm, getFormAttempts, getAttemptDetails } from '../api/statistics.js'
import { formContext, attemptDetails, gradesChart, daysChart, blocksChart, optionsChart, sortedQuestions, shortText, duration, attemptRow } from '../utils/statistics.js'
import StatisticsChart from '../components/StatisticsChart.vue'
import AttemptDetailsDialog from '../components/AttemptDetailsDialog.vue'
import MessageDialog from '../components/MessageDialog.vue'
import NotFoundPage from './NotFoundPage.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const stats = ref(null)
const context = ref(formContext(null))
const loading = ref(false)
const errorText = ref('')
const status = ref(null)
const tab = ref('summary')
const difficult = ref(false)
const attempts = ref(null)
const attemptsLoading = ref(false)
const attemptsError = ref('')
const details = ref(null)
const detailsLoading = ref(false)
const detailsError = ref('')
const selectedAttempt = ref(null)
const messageDialog = ref(null)
let generation = 0
onBeforeUnmount(() => { generation++ })

const questions = computed(() => sortedQuestions(stats.value?.questions ?? [], difficult.value).map(question => ({ ...question, chart: optionsChart(question.options ?? []) })))
const grades = computed(() => gradesChart(stats.value?.grade_distribution ?? []))
const days = computed(() => daysChart(stats.value?.daily_finished ?? []))
const blocks = computed(() => blocksChart(stats.value?.blocks ?? []))
const rows = computed(() => (attempts.value ?? []).map(attempt => ({ ...attempt, ...attemptRow(attempt, stats.value.form.is_test) })))
const displayedDetails = computed(() => details.value ? attemptDetails(details.value, context.value.questionBlocks, stats.value.form.is_test) : null)

function handleError(error) {
  if (error.status === 401) {
    auth.logout()
    router.replace({ path: '/login', query: { redirect: route.fullPath } })
  } else if ([403, 404].includes(error.status)) {
    status.value = error.status
  } else messageDialog.value?.show(error.detail ?? error.message)
}

async function loadStatistics() {
  const current = generation
  loading.value = true
  errorText.value = ''
  status.value = null
  try {
    const data = await getStatistics(route.params.id)
    if (current === generation) stats.value = data
  } catch (error) {
    if (current !== generation) return
    errorText.value = error.message
    handleError(error)
  } finally { if (current === generation) loading.value = false }
}

async function loadAttempts() {
  if (attemptsLoading.value) return
  const current = generation
  attemptsLoading.value = true
  attemptsError.value = ''
  try {
    const data = await getFormAttempts(route.params.id)
    if (current === generation) attempts.value = data
  } catch (error) {
    if (current !== generation) return
    attemptsError.value = error.message
    handleError(error)
  } finally { if (current === generation) attemptsLoading.value = false }
}

function selectTab(value) {
  tab.value = value
  if (value === 'attempts' && attempts.value === null) loadAttempts()
}

async function openAttempt(attempt) {
  if (!attempt.is_finished || detailsLoading.value) return
  const current = generation
  selectedAttempt.value = attempt
  detailsLoading.value = true
  detailsError.value = ''
  try {
    const data = await getAttemptDetails(attempt.attempt_id)
    if (current !== generation) return
    details.value = data
  } catch (error) {
    if (current !== generation) return
    detailsError.value = error.message
    handleError(error)
  } finally { if (current === generation) detailsLoading.value = false }
}

watch(() => route.params.id, async id => {
  const current = ++generation
  stats.value = null
  attempts.value = null
  attemptsLoading.value = false
  attemptsError.value = ''
  details.value = null
  detailsLoading.value = false
  detailsError.value = ''
  tab.value = 'summary'
  difficult.value = false
  context.value = formContext(null)
  loadStatistics()
  // Дополнительные сведения не блокируют статистику и не вызывают окно ошибки.
  try {
    const form = await getStatisticsForm(id)
    if (current === generation) context.value = formContext(form)
  } catch { /* Оставляем запасные подписи и пояснение для опроса. */ }
}, { immediate: true })
</script>

<template>
  <NotFoundPage v-if="status === 404" />
  <section v-else-if="status === 403"><h1>Нет доступа к этой форме</h1></section>
  <section v-else>
    <p v-if="loading" role="status">Загрузка…</p>
    <div v-else-if="errorText" role="alert"><p>{{ errorText }}</p><button @click="loadStatistics">Повторить</button></div>
    <template v-else-if="stats">
      <h1>Статистика: {{ stats.form.title }}</h1>
      <RouterLink :to="`/forms/${route.params.id}/edit`">Открыть форму</RouterLink>
      <nav class="actions statistics-tabs" aria-label="Разделы статистики">
        <button :aria-pressed="tab === 'summary'" @click="selectTab('summary')">Сводка</button>
        <button :aria-pressed="tab === 'questions'" @click="selectTab('questions')">Вопросы</button>
        <button :aria-pressed="tab === 'attempts'" @click="selectTab('attempts')">Прохождения</button>
      </nav>
      <div v-if="tab === 'summary'">
        <div class="statistics-cards">
          <p>Начато: {{ stats.summary.started }}</p><p>Завершено: {{ stats.summary.finished }}</p>
          <p>Процент завершения: {{ stats.summary.completion_percent }}%</p>
          <p>Типичное время: {{ duration(stats.summary.median_time_seconds) }}</p>
          <p v-if="stats.form.is_test">Средний балл: {{ stats.summary.avg_score == null ? '—' : `${stats.summary.avg_score} (${stats.summary.avg_percent}%)` }}</p>
          <p v-else>Завершили досрочно: {{ stats.summary.finished_early }}</p>
        </div>
        <p v-if="!stats.summary.finished">Пока нет завершённых прохождений</p>
        <template v-else>
          <StatisticsChart v-if="stats.form.is_test && grades.labels.length" :data="grades" title="Распределение оценок" />
          <StatisticsChart v-if="days.labels.length" :data="days" line title="Завершения по дням (дни по UTC)" />
        </template>
        <template v-if="!stats.form.is_test && context.hasRules">
          <h2>Досрочное завершение</h2>
          <p v-if="!stats.early_finish_rules.length">Нет сработавших правил</p>
          <div v-else class="table-scroll"><table><thead><tr><th>Вопрос</th><th>Сообщение правила</th><th>Попыток</th></tr></thead><tbody><tr v-for="rule in stats.early_finish_rules" :key="rule.rule_id"><td>{{ rule.question_text }}</td><td class="plain-text">{{ rule.message || 'без сообщения' }}</td><td>{{ rule.count }}</td></tr></tbody></table></div>
        </template>
      </div>
      <div v-else-if="tab === 'questions'">
        <StatisticsChart v-if="stats.summary.finished && stats.form.is_test && blocks.labels.length >= 2" :data="blocks" horizontal percent title="Результаты по блокам, %" />
        <label v-if="stats.form.is_test">Порядок вопросов <select v-model="difficult"><option :value="false">По порядку в тесте</option><option :value="true">Сначала сложные</option></select></label>
        <article v-for="question in questions" :key="question.question_id" class="statistics-question">
          <h2 class="plain-text">{{ question.number }}. {{ question.text }}</h2>
          <p>Показан: {{ question.shown }}, пропустили: {{ question.skipped }}</p>
          <p v-if="stats.form.is_test">Верных ответов: {{ question.correct_percent }}% · Средний балл за вопрос: {{ question.avg_score_percent }}%</p>
          <StatisticsChart v-if="stats.summary.finished && question.chart.labels.length" :data="question.chart" horizontal title="Варианты ответов" />
          <template v-if="question.type === 'text'">
            <p v-if="!question.top_answers.length">Нет текстовых ответов</p>
            <table v-else><thead><tr><th>Ответ</th><th>Число</th></tr></thead><tbody><tr v-for="answer in question.top_answers" :key="answer.value"><td :title="answer.value">{{ shortText(answer.value) }}</td><td>{{ answer.count }}</td></tr></tbody></table>
          </template>
        </article>
        <p v-if="!stats.form.is_test" class="statistics-note">Число показов вопроса может быть меньше числа прохождений: часть вопросов участнику не показывается (условия показа или досрочное завершение).</p>
      </div>
      <div v-else>
        <p v-if="attemptsLoading || detailsLoading" role="status">Загрузка…</p>
        <div v-if="attemptsError" role="alert"><p>{{ attemptsError }}</p><button @click="loadAttempts">Повторить</button></div>
        <div v-if="detailsError" role="alert"><p>{{ detailsError }}</p><button @click="openAttempt(selectedAttempt)">Повторить</button></div>
        <p v-if="attempts && !attempts.length">Пока нет прохождений</p>
        <div v-if="rows.length" class="table-scroll"><table><thead><tr><th>Участник</th><th>Начало</th><th>Статус</th><th>Результат</th></tr></thead><tbody>
          <tr v-for="attempt in rows" :key="attempt.attempt_id" :class="{ 'history-link-row': attempt.is_finished }" @click="openAttempt(attempt)">
            <td><button v-if="attempt.is_finished" :disabled="detailsLoading" @click.stop="openAttempt(attempt)">{{ attempt.name }}</button><span v-else>{{ attempt.name }}</span></td><td>{{ attempt.date }}</td><td>{{ attempt.status }}</td><td>{{ attempt.result }}</td>
          </tr>
        </tbody></table></div>
      </div>
    </template>
  </section>
  <AttemptDetailsDialog v-if="displayedDetails && !status" :details="displayedDetails" :is-test="stats.form.is_test" @close="details = null" />
  <MessageDialog ref="messageDialog" />
</template>

<style scoped>
.statistics-tabs { margin: 1rem 0; }
.statistics-tabs [aria-pressed="true"] { font-weight: bold; outline: 2px solid #555; }
.statistics-cards { display: flex; flex-wrap: wrap; gap: 1rem; }
.statistics-cards p, .statistics-question { border: 1px solid #ccc; padding: 1rem; }
.statistics-question { margin: 1rem 0; min-width: 0; overflow-wrap: anywhere; }
.statistics-note { color: #888; font-size: 0.875rem; }
td { overflow-wrap: anywhere; }
</style>
