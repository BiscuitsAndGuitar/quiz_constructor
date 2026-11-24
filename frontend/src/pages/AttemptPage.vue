<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { finishAttempt } from '../api/attempts.js'
import { loadAttempt, saveAttempt, removeAttempt } from '../utils/attemptStorage.js'
import { visibleContent, finishAnswers, remainingMilliseconds } from '../utils/attempt.js'
import AttemptFlow from '../components/AttemptFlow.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import MessageDialog from '../components/MessageDialog.vue'

const route = useRoute(), router = useRouter(), auth = useAuthStore()
const state = ref(null), busy = ref(false), done = ref(false), expired = ref(false), timedOut = ref(false)
const now = ref(Date.now()), confirm = ref(null), messages = ref(null), flow = ref(null)
let clock = null
let unmounted = false
watch(() => route.params.id, id => {
  state.value = null
  busy.value = false
  done.value = false
  expired.value = false
  timedOut.value = false
  try { state.value = loadAttempt(sessionStorage, id) } catch { /* Покажем прерванную попытку. */ }
}, { immediate: true })
const form = computed(() => state.value?.form)
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
  let answers = finishAnswers(questions, state.value.answers)
  if (!automatic) {
    const prepared = await flow.value.prepareFinish()
    if (!prepared || unmounted || state.value?.id !== attemptId || busy.value || done.value || timedOut.value) return
    answers = prepared.answers
  }
  busy.value = true
  try {
    await finishAttempt(attemptId, answers, auth.token)
    try { removeAttempt(sessionStorage, attemptId) } catch { /* Результат уже сохранён на сервере. */ }
    // Ответ старого запроса не должен уводить пользователя с уже открытой другой страницы.
    if (unmounted || state.value?.id !== attemptId) return
    await result()
  } catch (error) {
    if (unmounted || state.value?.id !== attemptId) return
    if (error.status === 422 && error.missing_question_ids?.length) await flow.value?.showMissing(error.missing_question_ids)
    else if (error.status === 409 && error.message.includes('уже завершена')) await result()
    else if (error.status === 409 && error.message.toLowerCase().includes('время')) {
      expired.value = true
      done.value = true
      clearState()
    } else messages.value.show(error.detail || error.message)
  } finally { if (state.value?.id === attemptId) busy.value = false }
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
    <template v-if="timedOut">
      <p>Время вышло. Отправляем ответы.</p>
      <button :disabled="busy" @click="finish(true)">Повторить отправку</button>
    </template>
    <AttemptFlow v-show="!timedOut" :key="state.id" ref="flow" :state="state" :busy="busy || timedOut"
      @change="persist" @finish="finish()" />
  </section>
  <ConfirmDialog ref="confirm" /><MessageDialog ref="messages" />
</template>
