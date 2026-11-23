<script setup>
import { changeQuestionType, newOption } from '../utils/formEditor.js'
import { availableQuestions, deletionReferences, typeChangeErrors } from '../utils/conditions.js'
import ConditionEditor from './ConditionEditor.vue'
import FinishRulesEditor from './FinishRulesEditor.vue'
import { questionSummary, questionTypeNames, conditionSummary } from '../utils/editorDisplay.js'

const props = defineProps({ question: { type: Object, required: true }, number: Number, isTest: Boolean, disabled: Boolean, canMoveUp: Boolean, canMoveDown: Boolean,
  blocks: { type: Array, required: true }, blockIndex: Number, questionIndex: Number, collapsed: Boolean, readOnly: Boolean,
  conditionCollapsed: Boolean, rulesCollapsed: Boolean })
const emit = defineEmits(['remove', 'change', 'move', 'error', 'toggle', 'toggle-condition', 'toggle-rules'])

function changeType(event) {
  const errors = typeChangeErrors(props.blocks, props.question.key, event.target.value)
  if (errors.length) {
    event.target.value = props.question.type
    emit('error', `Нельзя изменить тип. ${errors.join('; ')}. Сначала измените условия.`)
    return
  }
  changeQuestionType(props.question, event.target.value)
}

function removeOption(index) {
  const places = deletionReferences(props.blocks, [], props.question.options[index].key)
  if (places.length) {
    emit('error', `Нельзя удалить вариант: на него ссылаются ${places.join('; ')}. Сначала удалите ссылки.`)
    return
  }
  props.question.options.splice(index, 1)
}

function chooseCorrect(selected) {
  for (const option of props.question.options) option.is_correct = option === selected
}
</script>

<template>
  <fieldset class="question-editor" :disabled="disabled" @input="$emit('change')" @change="$emit('change')">
    <legend>Вопрос {{ number }}</legend>
    <div class="actions question-actions">
      <button type="button" :title="collapsed ? 'Развернуть вопрос' : 'Свернуть вопрос'" :aria-expanded="!collapsed" @click="$emit('toggle')">{{ collapsed ? '▸' : '▾' }}</button>
      <span v-if="collapsed" class="card-summary" :title="question.text">{{ questionSummary(question) }} · {{ questionTypeNames[question.type] }}</span>
      <span v-if="question.condition" class="hint">есть условие</span>
      <span v-if="!isTest && question.finish_rules?.length" class="hint">правила завершения: {{ question.finish_rules.length }}</span>
      <button v-if="!readOnly" type="button" title="Вверх" :aria-label="`Вопрос ${number}: вверх`" :disabled="disabled || !canMoveUp" @click="$emit('move', -1)">↑</button>
      <button v-if="!readOnly" type="button" title="Вниз" :aria-label="`Вопрос ${number}: вниз`" :disabled="disabled || !canMoveDown" @click="$emit('move', 1)">↓</button>
      <button v-if="!readOnly" type="button" class="remove-question" @click="$emit('remove')">Удалить вопрос</button>
    </div>
    <fieldset v-show="!collapsed" :disabled="readOnly" class="editor-fields">
    <div class="field"><label :for="`${question.key}-text`">Текст вопроса</label><textarea :id="`${question.key}-text`" v-model="question.text" rows="3"></textarea></div>
    <div class="field">
      <label :for="`${question.key}-type`">Тип вопроса</label>
      <select :id="`${question.key}-type`" :value="question.type" @change="changeType">
        <option value="single">Один ответ</option><option value="multiple">Несколько ответов</option><option value="text">Текстовый ответ</option>
      </select>
    </div>
    <label v-if="!isTest" class="checkbox-label"><input v-model="question.is_answer_required" type="checkbox"> Обязательный</label>
    <template v-if="isTest">
      <div class="field"><label :for="`${question.key}-points`">Баллы</label><input :id="`${question.key}-points`" v-model.number="question.points" type="number" min="1" max="1000" step="1"></div>
      <div v-if="question.type === 'multiple'" class="field">
        <label :for="`${question.key}-scoring`">Режим оценки</label>
        <select :id="`${question.key}-scoring`" v-model="question.allow_partial_scoring"><option :value="false">Всё или ничего</option><option :value="true">Частичные баллы</option></select>
        <p v-if="question.allow_partial_scoring" class="hint">Для частичных баллов задайте не меньше баллов, чем верных вариантов</p>
      </div>
    </template>
    <div v-if="question.type !== 'text'" class="options-editor">
      <div v-for="(option, index) in question.options" :key="option.key" class="option-row">
        <label :for="option.key">Вариант {{ index + 1 }}</label>
        <input :id="option.key" v-model="option.text">
        <label v-if="isTest" class="correct-option">
          <input v-if="question.type === 'single'" type="radio" :name="`${question.key}-correct`" :checked="option.is_correct" @change="chooseCorrect(option)">
          <input v-else v-model="option.is_correct" type="checkbox"> Верный
        </label>
        <button v-if="!readOnly" type="button" :aria-label="`Удалить вариант ${index + 1}`" @click="removeOption(index)">Удалить</button>
      </div>
      <button v-if="!readOnly" type="button" @click="question.options.push(newOption(isTest)); $emit('change')">Добавить вариант</button>
      <p v-if="isTest" class="hint">Если нужен вариант «все перечисленные», формулируйте его как «Все варианты верны»: при перемешивании порядок вариантов меняется</p>
    </div>
    <div v-if="isTest && question.type === 'text'">
      <h3>Допустимые ответы</h3>
      <div v-for="(answer, index) in question.correct_text_answers" :key="index" class="option-row">
        <label :for="`${question.key}-answer-${index}`">Ответ {{ index + 1 }}</label>
        <input :id="`${question.key}-answer-${index}`" v-model="question.correct_text_answers[index]">
        <button v-if="!readOnly" type="button" :aria-label="`Удалить ответ ${index + 1}`" @click="question.correct_text_answers.splice(index, 1); $emit('change')">Удалить</button>
      </div>
      <button v-if="!readOnly" type="button" @click="question.correct_text_answers.push(''); $emit('change')">Добавить ответ</button>
    </div>
    </fieldset>
    <div v-if="!isTest" v-show="!collapsed">
      <h3><button type="button" :title="conditionCollapsed ? 'Развернуть условие показа вопроса' : 'Свернуть условие показа вопроса'" :aria-expanded="!conditionCollapsed" @click="$emit('toggle-condition')">{{ conditionCollapsed ? '▸' : '▾' }}</button> Условие показа вопроса</h3>
      <p v-if="conditionCollapsed">{{ conditionSummary(question.condition) }}</p>
      <ConditionEditor v-show="!conditionCollapsed" :read-only="readOnly" v-model="question.condition" :questions="availableQuestions(blocks, blockIndex, questionIndex)" />
      <FinishRulesEditor :collapsed="rulesCollapsed" @toggle="$emit('toggle-rules')" :read-only="readOnly" v-if="question.type !== 'info'" :question="question" :questions="availableQuestions(blocks, blockIndex, questionIndex, true)" />
    </div>
  </fieldset>
</template>
