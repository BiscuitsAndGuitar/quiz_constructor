<script setup>
import QuestionEditor from './QuestionEditor.vue'
import ConditionEditor from './ConditionEditor.vue'
import { availableQuestions, deletionReferences } from '../utils/conditions.js'
import { canMoveQuestion, newQuestion } from '../utils/formEditor.js'

const props = defineProps({
  blocks: { type: Array, required: true }, index: { type: Number, required: true },
  numbers: { type: Array, required: true }, isTest: Boolean, disabled: Boolean, readOnly: Boolean,
  collapsed: { type: Set, required: true },
})
const emit = defineEmits(['remove', 'move', 'move-question', 'error', 'toggle'])

function removeQuestion(index) {
  const question = props.blocks[props.index].questions[index]
  const places = deletionReferences(props.blocks, [question.key])
  if (places.length) {
    emit('error', `Нельзя удалить вопрос: на него ссылаются ${places.join('; ')}. Сначала удалите ссылки.`)
    return
  }
  props.blocks[props.index].questions.splice(index, 1)
}

function addQuestion() {
  props.blocks[props.index].questions.push(newQuestion(props.isTest))
}
</script>

<template>
  <fieldset class="block-editor" :disabled="disabled">
    <legend v-if="!collapsed.has(blocks[index].key)">Блок {{ index + 1 }}</legend>
    <div class="actions block-actions">
      <button type="button" :title="collapsed.has(blocks[index].key) ? 'Развернуть блок' : 'Свернуть блок'"
        :aria-expanded="!collapsed.has(blocks[index].key)" @click="$emit('toggle', blocks[index].key)">{{ collapsed.has(blocks[index].key) ? '▸' : '▾' }}</button>
      <span class="card-summary">{{ blocks[index].title?.trim() || `Блок ${index + 1}` }} · Вопросов: {{ blocks[index].questions.length }}</span>
      <span v-if="blocks[index].condition" class="hint">есть условие</span>
      <button v-if="!readOnly" type="button" title="Вверх" :aria-label="`Блок ${index + 1}: вверх`" :disabled="disabled || index === 0" @click="$emit('move', -1)">↑</button>
      <button v-if="!readOnly" type="button" title="Вниз" :aria-label="`Блок ${index + 1}: вниз`" :disabled="disabled || index === blocks.length - 1" @click="$emit('move', 1)">↓</button>
      <button v-if="!readOnly" type="button" :disabled="disabled || blocks.length === 1" @click="$emit('remove')">Удалить блок</button>
      <span v-if="!readOnly && blocks.length === 1" class="hint">В форме должен быть хотя бы один блок</span>
    </div>
    <div v-show="!collapsed.has(blocks[index].key)">
    <div class="field">
      <label :for="`${blocks[index].key}-title`">Название блока</label>
      <input :id="`${blocks[index].key}-title`" v-model="blocks[index].title" :disabled="readOnly">
      <p class="hint">Необязательно, до 255 символов</p>
    </div>
    <section v-if="!isTest"><h3>Условие показа блока</h3>
      <ConditionEditor :read-only="readOnly" v-model="blocks[index].condition" :questions="availableQuestions(blocks, index)" />
    </section>
    <QuestionEditor v-for="(question, questionIndex) in blocks[index].questions" :key="question.key"
      :blocks="blocks" :block-index="index" :question-index="questionIndex"
      :read-only="readOnly" :question="question" :number="numbers[questionIndex]" :is-test="isTest" :disabled="disabled"
      :collapsed="collapsed.has(question.key)" @toggle="$emit('toggle', question.key)"
      :can-move-up="canMoveQuestion(blocks, index, questionIndex, -1)"
      :can-move-down="canMoveQuestion(blocks, index, questionIndex, 1)"
      @move="$emit('move-question', questionIndex, $event)" @remove="removeQuestion(questionIndex)" @error="$emit('error', $event)" />
    <button v-if="!readOnly" type="button" @click="addQuestion">Добавить вопрос</button>
    </div>
  </fieldset>
</template>
