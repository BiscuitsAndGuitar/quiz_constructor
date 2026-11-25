<script setup>
import { baseUrl } from '../api/client.js'
import { imageUrl } from '../utils/images.js'
import { limitTextAnswer } from '../utils/attempt.js'
const props = defineProps({ question: Object, answer: Object, number: Number, required: Boolean, invalid: Boolean, disabled: Boolean })
const emit = defineEmits(['answer'])
function inputText(event) {
  const text = limitTextAnswer(event.target.value)
  // Исправляем и само поле, даже если новое обрезанное значение равно прежнему ответу.
  event.target.value = text
  emit('answer', { text })
}
function choose(id, checked) {
  const selected = props.answer?.option_ids || []
  emit('answer', { option_ids: props.question.type === 'single' ? [id] :
    checked ? [...new Set([...selected, id])] : selected.filter(value => value !== id) })
}
</script>

<template>
  <fieldset :id="`question-${question.id}`" class="attempt-question" :class="{ 'answer-missing': invalid }" :disabled="disabled">
    <legend v-if="question.type !== 'info'">Вопрос {{ number }} <span v-if="required" aria-label="обязательный">*</span></legend>
    <img v-if="question.image" :src="imageUrl(question.image.url, baseUrl)" alt="Иллюстрация к вопросу" class="question-image">
    <p class="plain-text">{{ question.text }}</p>
    <template v-if="question.type === 'single' || question.type === 'multiple'">
      <label v-for="option in question.options" :key="option.id" class="attempt-option">
        <input :type="question.type === 'single' ? 'radio' : 'checkbox'" :name="`answer-${question.id}`"
          :checked="answer?.option_ids?.includes(option.id) || false" :aria-invalid="invalid"
          @change="choose(option.id, $event.target.checked)">
        {{ option.text }}
      </label>
      <button v-if="question.type === 'single' && answer?.option_ids?.length" type="button" @click="emit('answer', { option_ids: [] })">Очистить ответ</button>
    </template>
    <textarea v-else-if="question.type === 'text'" :value="limitTextAnswer(answer?.text)" maxlength="1000" rows="3"
      :aria-label="question.text" :aria-invalid="invalid" @input="inputText" />
    <p v-if="invalid" class="wrong-answer" role="alert">Ответьте на обязательный вопрос</p>
  </fieldset>
</template>
