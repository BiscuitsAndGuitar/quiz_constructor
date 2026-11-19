<script setup>
import { changeQuestionType, newOption } from '../utils/formEditor.js'

const props = defineProps({ question: { type: Object, required: true }, number: Number, isTest: Boolean, disabled: Boolean })
defineEmits(['remove', 'change'])

function changeType(event) {
  changeQuestionType(props.question, event.target.value)
}
</script>

<template>
  <fieldset class="question-editor" :disabled="disabled" @input="$emit('change')" @change="$emit('change')">
    <legend>Вопрос {{ number }}</legend>
    <div class="field"><label :for="`${question.key}-text`">Текст вопроса</label><textarea :id="`${question.key}-text`" v-model="question.text" rows="3"></textarea></div>
    <div class="field">
      <label :for="`${question.key}-type`">Тип вопроса</label>
      <select :id="`${question.key}-type`" :value="question.type" @change="changeType">
        <option value="single">Один ответ</option><option value="multiple">Несколько ответов</option><option value="text">Текстовый ответ</option>
      </select>
    </div>
    <label v-if="!isTest" class="checkbox-label"><input v-model="question.is_answer_required" type="checkbox"> Обязательный</label>
    <div v-if="question.type !== 'text'" class="options-editor">
      <div v-for="(option, index) in question.options" :key="option.key" class="option-row">
        <label :for="option.key">Вариант {{ index + 1 }}</label>
        <input :id="option.key" v-model="option.text">
        <button type="button" :aria-label="`Удалить вариант ${index + 1}`" @click="question.options.splice(index, 1); $emit('change')">Удалить</button>
      </div>
      <button type="button" @click="question.options.push(newOption()); $emit('change')">Добавить вариант</button>
    </div>
    <button type="button" class="remove-question" @click="$emit('remove')">Удалить вопрос</button>
  </fieldset>
</template>
