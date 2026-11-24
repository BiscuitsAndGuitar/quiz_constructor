<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { visibleContent, attemptPages, pageIndex, missingRequired, finishAnswers, hasAnswer } from '../utils/attempt.js'
import AttemptQuestion from './AttemptQuestion.vue'
import ConfirmDialog from './ConfirmDialog.vue'
const props = defineProps({ state: { type: Object, required: true }, busy: Boolean })
const emit = defineEmits(['change', 'finish'])
const state = computed(() => props.state)
const form = computed(() => state.value.form)
const missing = ref([]), confirm = ref(null)
const content = computed(() => visibleContent(form.value, state.value.answers))
const pages = computed(() => attemptPages(form.value, content.value.blocks))
const index = computed(() => pageIndex(pages.value, state.value.pageKey, state.value.position || 0))
const page = computed(() => pages.value[index.value])
function go(position) {
  if (!pages.value[position]) return
  state.value.position = position
  state.value.pageKey = pages.value[position].key
  emit('change')
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
async function prepareFinish() {
  const visible = visibleContent(form.value, state.value.answers, true)
  const questions = visible.blocks.flatMap(block => block.questions)
  const ids = missingRequired(form.value, questions, state.value.answers)
  if (ids.length) { await showMissing(ids); return null }
  const count = questions.filter(q => q.type !== 'info' && !hasAnswer(state.value.answers[q.id])).length
  if (form.value.is_test && count && !await confirm.value.ask({ title: 'Завершение теста',
    message: `Вы не ответили на ${count} вопросов. Завершить?`, confirmText: 'Завершить', cancelText: 'Продолжить' })) return null
  return { answers: finishAnswers(questions, state.value.answers), rule: visible.rule }
}
async function forward() {
  if (props.busy) return
  if (index.value >= pages.value.length - 1) return emit('finish')
  const ids = missingRequired(form.value, page.value?.questions || [], state.value.answers)
  if (ids.length) return showMissing(ids)
  const currentRule = visibleContent(form.value, state.value.answers, true, page.value?.questions.map(q => q.id) || []).rule
  if (currentRule) emit('finish')
  else go(index.value + 1)
}
watch(() => pages.value.map(p => p.key).join(','), () => go(index.value))
defineExpose({ prepareFinish, showMissing })
</script>
<template>
  <div>
    <progress v-if="!form.is_test" :value="pages.length ? index + 1 : 0" :max="Math.max(1, pages.length)" aria-label="Прогресс прохождения" />
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
    <ConfirmDialog ref="confirm" />
  </div>
</template>
