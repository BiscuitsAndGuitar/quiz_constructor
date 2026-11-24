<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { finishAttempt } from '../api/attempts.js'
import { loadAttempt, saveAttempt, removeAttempt } from '../utils/attemptStorage.js'
import { visibleContent, attemptPages, pageIndex, missingRequired, finishAnswers, hasAnswer, remainingMilliseconds } from '../utils/attempt.js'
import AttemptQuestion from '../components/AttemptQuestion.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import MessageDialog from '../components/MessageDialog.vue'

const route = useRoute(), router = useRouter(), auth = useAuthStore()
const state = ref(null), missing = ref([]), busy = ref(false), done = ref(false), expired = ref(false), timedOut = ref(false)
const now = ref(Date.now()), confirm = ref(null), messages = ref(null)
let clock = null
let unmounted = false
watch(() => route.params.id, id => {
  state.value = null
  busy.value = false
  done.value = false
  expired.value = false
  timedOut.value = false
  missing.value = []
  try { state.value = loadAttempt(sessionStorage, id) } catch { /* Покажем прерванную попытку. */ }
}, { immediate: true })
const form = computed(() => state.value?.form)
const content = computed(() => state.value ? visibleContent(form.value, state.value.answers) : { blocks: [] })
const pages = computed(() => state.value ? attemptPages(form.value, content.value.blocks) : [])
const index = computed(() => pageIndex(pages.value, state.value?.pageKey, state.value?.position || 0))
const page = computed(() => pages.value[index.value])
const remaining = computed(() => state.value ? remainingMilliseconds(state.value.duration, state.value.receivedAt, now.value) : null)
const timerText = computed(() => {
  const seconds = Math.ceil((remaining.value || 0) / 1000)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
})
function persist() {
  if (!state.value || done.value || timedOut.value) return
  try { saveAttempt(sessionStorage, state.value) }
  catch { messages.value?.show('Не удалось сохранить прохождение в браузере. Не обновляйте страницу до завершения.') }
}
function clearState() {
  try { removeAttempt(sessionStorage, state.value.id) } catch { /* Недоступное хранилище уже нельзя восстановить. */ }
}
function go(position) {
  if (!pages.value[position]) return
  state.value.position = position
  state.value.pageKey = pages.value[position].key
  persist()
}
function answer(id, value) {
  state.value.answers[id] = value
  missing.value = missing.value.filter(qid => qid !== id || !hasAnswer(value))
  go(index.value)
}
async function showMissing(ids) {
  missing.value = ids
  const position = pages.value.findIndex(p => p.questions.some(q => ids.includes(q.id)))
  if (position >= 0) go(position)
  await nextTick()
  document.getElementById(`question-${ids[0]}`)?.scrollIntoView({ block: 'center' })
}
async function result() {
  done.value = true
  clearState()
  await router.replace(`/attempt/${state.value.id}/result`)
}
async function finish(automatic = false) {
  if (busy.value || done.value || expired.value) return
  const attemptId = state.value.id
  const visible = visibleContent(form.value, state.value.answers, true)
  const questions = visible.blocks.flatMap(block => block.questions)
  if (!automatic) {
    const ids = missingRequired(form.value, questions, state.value.answers)
    if (ids.length) return showMissing(ids)
    const count = questions.filter(q => q.type !== 'info' && !hasAnswer(state.value.answers[q.id])).length
    if (form.value.is_test && count && !await confirm.value.ask({ title: 'Завершение теста',
      message: `Вы не ответили на ${count} вопросов. Завершить?`, confirmText: 'Завершить', cancelText: 'Продолжить' })) return
    // Таймер мог отправить ответы, пока было открыто подтверждение.
    if (unmounted || state.value?.id !== attemptId || busy.value || done.value || timedOut.value) return
  }
  busy.value = true
  try {
    await finishAttempt(attemptId, finishAnswers(questions, state.value.answers), auth.token)
    try { removeAttempt(sessionStorage, attemptId) } catch { /* Результат уже сохранён на сервере. */ }
    // Ответ старого запроса не должен уводить пользователя с уже открытой другой страницы.
    if (unmounted || state.value?.id !== attemptId) return
    await result()
  } catch (error) {
    if (unmounted || state.value?.id !== attemptId) return
    if (error.status === 422 && error.missing_question_ids?.length) await showMissing(error.missing_question_ids)
    else if (error.status === 409 && error.message.includes('уже завершена')) await result()
    else if (error.status === 409 && error.message.toLowerCase().includes('время')) {
      expired.value = true
      done.value = true
      clearState()
    } else messages.value.show(error.detail || error.message)
  } finally { if (state.value?.id === attemptId) busy.value = false }
}
async function forward() {
  if (busy.value || timedOut.value) return
  if (index.value >= pages.value.length - 1) return finish()
  const ids = missingRequired(form.value, page.value?.questions || [], state.value.answers)
  if (ids.length) return showMissing(ids)
  const currentRule = visibleContent(form.value, state.value.answers, true, page.value?.questions.map(q => q.id) || []).rule
  if (currentRule) await finish()
  else go(index.value + 1)
}
async function leave() {
  if (!state.value || done.value) return true
  return confirm.value.ask({ title: 'Выход из прохождения', message: 'Попытка считается использованной. Выйти?',
    confirmText: 'Выйти', cancelText: 'Остаться' })
}
onBeforeRouteLeave(leave)
onBeforeRouteUpdate(async () => {
  if (!await leave()) return false
  // Новый номер попытки требует нового состояния и нового таймера.
  return true
})
function beforeUnload(event) {
  if (state.value && !done.value) { event.preventDefault(); event.returnValue = '' }
}
function tick() {
  now.value = Date.now()
  if (state.value && remaining.value === 0 && !timedOut.value && !done.value) {
    timedOut.value = true
    clearState()
    void finish(true)
  }
}
onMounted(() => { window.addEventListener('beforeunload', beforeUnload); tick(); clock = setInterval(tick, 500) })
onBeforeUnmount(() => { unmounted = true; clearInterval(clock); window.removeEventListener('beforeunload', beforeUnload) })
watch(() => pages.value.map(p => p.key).join(','), () => { if (state.value) go(index.value) })
</script>

<template>
  <section v-if="!state">
    <h1>Прохождение прервано</h1><p>Прохождение прервано. Попытка считается использованной</p>
    <RouterLink to="/">На главную</RouterLink>
  </section>
  <section v-else-if="expired"><h1>Время вышло, попытка не засчитана</h1><RouterLink to="/">На главную</RouterLink></section>
  <section v-else>
    <h1>{{ form.title }}</h1>
    <p v-if="remaining !== null" :class="{ 'wrong-answer': remaining <= 60000 }" role="timer">Осталось {{ timerText }}</p>
    <progress v-if="!form.is_test" :value="pages.length ? index + 1 : 0" :max="Math.max(1, pages.length)" aria-label="Прогресс прохождения" />
    <template v-if="timedOut">
      <p>Время вышло. Отправляем ответы.</p>
      <button :disabled="busy" @click="finish(true)">Повторить отправку</button>
    </template>
    <template v-else>
      <nav v-if="form.allow_free_navigation" class="actions attempt-navigation" aria-label="Навигация по форме">
        <button v-for="(item, position) in pages" :key="item.key" :disabled="busy" :aria-current="position === index ? 'step' : undefined"
          @click="go(position)">
          {{ form.take_by_blocks ? (item.title || `Блок ${position + 1}`) : (item.numbered.get(item.questions.find(q => q.type !== 'info')?.id) || 'Пояснение') }}
          {{ item.questions.some(q => q.type !== 'info' && hasAnswer(state.answers[q.id])) ? '✓' : '' }}
        </button>
      </nav>
      <h2 v-if="form.take_by_blocks && page">{{ page.title || `Блок ${index + 1}` }}</h2>
      <AttemptQuestion v-for="question in page?.questions || []" :key="question.id" :question="question"
        :answer="state.answers[question.id]" :number="page.numbered.get(question.id)" :required="!form.is_test && question.is_answer_required"
        :invalid="missing.includes(question.id)" :disabled="busy" @answer="answer(question.id, $event)" />
      <div class="actions">
        <button v-if="form.allow_free_navigation && index > 0" :disabled="busy" @click="go(index - 1)">{{ form.take_by_blocks ? 'Предыдущая страница' : 'Назад' }}</button>
        <button :disabled="busy" @click="forward">{{ index >= pages.length - 1 ? 'Завершить' : form.take_by_blocks && form.allow_free_navigation ? 'Следующая страница' : 'Далее' }}</button>
      </div>
    </template>
  </section>
  <ConfirmDialog ref="confirm" /><MessageDialog ref="messages" />
</template>
