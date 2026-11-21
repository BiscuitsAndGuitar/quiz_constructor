<script setup>
import { operatorNames, operatorsFor } from '../utils/conditions.js'

const props = defineProps({ modelValue: { type: Object, default: null }, questions: { type: Array, required: true }, required: Boolean })
const emit = defineEmits(['update:modelValue'])

function newItem() {
  return { question: props.questions[0]?.question.key || '', operator: 'answered' }
}
function add() {
  if (!props.modelValue) emit('update:modelValue', { match_all: true, items: [newItem()] })
  else props.modelValue.items.push(newItem())
}
function source(item) {
  return props.questions.find(entry => entry.question.key === item.question)?.question
}
function changeQuestion(item) {
  item.operator = 'answered'
  changeOperator(item)
}
function changeOperator(item) {
  delete item.option
  delete item.text_answer
  if (['chosen', 'not_chosen'].includes(item.operator)) item.option = source(item)?.options[0]?.key || ''
  if (['equals', 'contains'].includes(item.operator)) item.text_answer = ''
}
</script>

<template>
  <div class="condition-editor">
    <p v-if="!questions.length" class="hint">Нет подходящих вопросов выше</p>
    <template v-else>
      <template v-if="modelValue">
        <label>Выполняются:
          <select v-model="modelValue.match_all" aria-label="Связка условий">
            <option :value="true">Все условия</option><option :value="false">Любое из условий</option>
          </select>
        </label>
        <div v-for="(item, index) in modelValue.items" :key="index" class="condition-row">
          <label>Вопрос
            <select v-model="item.question" @change="changeQuestion(item)">
              <option v-for="entry in questions" :key="entry.question.key" :value="entry.question.key">Вопрос {{ entry.number }}: {{ entry.question.text || 'Без текста' }}</option>
            </select>
          </label>
          <label>Оператор
            <select v-model="item.operator" @change="changeOperator(item)">
              <option v-for="operator in operatorsFor(source(item)?.type)" :key="operator" :value="operator">{{ operatorNames[operator] }}</option>
            </select>
          </label>
          <label v-if="['chosen', 'not_chosen'].includes(item.operator)">Вариант
            <select v-model="item.option"><option disabled value="">Выберите вариант</option><option v-for="(option, optionIndex) in source(item)?.options || []" :key="option.key" :value="option.key">{{ option.text || `Вариант ${optionIndex + 1}` }}</option></select>
          </label>
          <label v-if="['equals', 'contains'].includes(item.operator)">Текст ответа<input v-model="item.text_answer"></label>
          <button type="button" @click="modelValue.items.splice(index, 1)">Удалить условие</button>
        </div>
      </template>
      <button type="button" @click="add">Добавить условие</button>
      <button v-if="modelValue && !required" type="button" @click="emit('update:modelValue', null)">Удалить все</button>
    </template>
  </div>
</template>
