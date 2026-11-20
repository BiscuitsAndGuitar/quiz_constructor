<script setup>
import QuestionEditor from './QuestionEditor.vue'
import { canMoveQuestion, newQuestion } from '../utils/formEditor.js'

const props = defineProps({
  blocks: { type: Array, required: true }, index: { type: Number, required: true },
  numbers: { type: Array, required: true }, isTest: Boolean, disabled: Boolean,
})
defineEmits(['remove', 'move', 'move-question'])

function addQuestion() {
  props.blocks[props.index].questions.push(newQuestion(props.isTest))
}
</script>

<template>
  <fieldset class="block-editor" :disabled="disabled">
    <legend>Блок {{ index + 1 }}</legend>
    <div class="actions block-actions">
      <button type="button" title="Вверх" :aria-label="`Блок ${index + 1}: вверх`" :disabled="disabled || index === 0" @click="$emit('move', -1)">↑</button>
      <button type="button" title="Вниз" :aria-label="`Блок ${index + 1}: вниз`" :disabled="disabled || index === blocks.length - 1" @click="$emit('move', 1)">↓</button>
      <button type="button" :disabled="disabled || blocks.length === 1" @click="$emit('remove')">Удалить блок</button>
      <span v-if="blocks.length === 1" class="hint">В форме должен быть хотя бы один блок</span>
    </div>
    <div class="field">
      <label :for="`${blocks[index].key}-title`">Название блока</label>
      <input :id="`${blocks[index].key}-title`" v-model="blocks[index].title">
      <p class="hint">Необязательно, до 255 символов</p>
    </div>
    <QuestionEditor v-for="(question, questionIndex) in blocks[index].questions" :key="question.key"
      :question="question" :number="numbers[questionIndex]" :is-test="isTest" :disabled="disabled"
      :can-move-up="canMoveQuestion(blocks, index, questionIndex, -1)"
      :can-move-down="canMoveQuestion(blocks, index, questionIndex, 1)"
      @move="$emit('move-question', questionIndex, $event)" @remove="blocks[index].questions.splice(questionIndex, 1)" />
    <button type="button" @click="addQuestion">Добавить вопрос</button>
  </fieldset>
</template>
