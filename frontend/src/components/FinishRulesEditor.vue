<script setup>
import ConditionEditor from './ConditionEditor.vue'
import { rulesSummary } from '../utils/editorDisplay.js'

const props = defineProps({ question: { type: Object, required: true }, questions: { type: Array, required: true }, readOnly: Boolean, collapsed: Boolean })
defineEmits(['toggle'])
function addRule() {
  props.question.finish_rules ??= []
  props.question.finish_rules.push({ key: crypto.randomUUID(), message: null,
    condition: { match_all: true, items: [{ question: props.question.key, operator: 'answered' }] } })
}
function move(index, direction) {
  const rules = props.question.finish_rules
  const target = index + direction
  if (target < 0 || target >= rules.length) return
  ;[rules[index], rules[target]] = [rules[target], rules[index]]
}
</script>

<template>
  <section class="finish-rules">
    <h3><button type="button" :title="collapsed ? 'Развернуть правила завершения' : 'Свернуть правила завершения'" :aria-expanded="!collapsed" @click="$emit('toggle')">{{ collapsed ? '▸' : '▾' }}</button> Завершить опрос, если…</h3>
    <p v-if="collapsed">{{ rulesSummary(question.finish_rules) }}</p>
    <div v-show="!collapsed">
    <p class="hint">Опрос закончится после этого вопроса, остальные вопросы участник не увидит. Срабатывает первое подходящее правило.</p>
    <fieldset :disabled="readOnly" v-for="(rule, index) in question.finish_rules || []" :key="rule.key">
      <legend>Правило {{ index + 1 }}</legend>
      <button v-if="!readOnly" type="button" :disabled="index === 0" :aria-label="`Правило ${index + 1}: вверх`" @click="move(index, -1)">↑</button>
      <button v-if="!readOnly" type="button" :disabled="index === question.finish_rules.length - 1" :aria-label="`Правило ${index + 1}: вниз`" @click="move(index, 1)">↓</button>
      <button v-if="!readOnly" type="button" @click="question.finish_rules.splice(index, 1)">Удалить правило</button>
      <ConditionEditor :read-only="readOnly" v-model="rule.condition" :questions="questions" required />
      <label :for="`${rule.key}-message`">Сообщение участнику</label>
      <textarea :id="`${rule.key}-message`" v-model="rule.message" rows="2" maxlength="1000"></textarea>
      <p class="hint">{{ (rule.message || '').length }} / 1000. Простой текст, без форматирования</p>
    </fieldset>
    <button v-if="!readOnly" type="button" @click="addRule">Добавить правило завершения</button>
    </div>
  </section>
</template>
