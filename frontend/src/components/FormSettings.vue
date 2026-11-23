<script setup>
import { settingsSummary } from '../utils/editorDisplay.js'
defineProps({ form: { type: Object, required: true }, collapsed: Boolean, readOnly: Boolean })
defineEmits(['change', 'toggle'])

function changeAccess(form) {
  if (!form.requires_login) form.max_attempts = null
}

function toggleTime(form, checked) {
  form.time_limit_minutes = checked ? 30 : null
}
</script>

<template>
  <fieldset class="form-settings" @input="$emit('change')" @change="$emit('change')">
    <legend><h2><button type="button" :title="collapsed ? 'Развернуть настройки формы' : 'Свернуть настройки формы'" :aria-expanded="!collapsed" @click="$emit('toggle')">{{ collapsed ? '▸' : '▾' }}</button> Настройки формы</h2></legend>
    <p v-if="collapsed">{{ settingsSummary(form) }}</p>
    <fieldset v-show="!collapsed" :disabled="readOnly" class="editor-fields">
    <div class="field"><label for="form-description">Описание</label><textarea id="form-description" v-model="form.description" rows="3"></textarea></div>
    <div class="field">
      <label for="form-access">Доступ</label>
      <select id="form-access" v-model="form.requires_login" @change="changeAccess(form)">
        <option :value="false">Всем</option><option :value="true">Только авторизованным</option>
      </select>
    </div>
    <div v-if="form.requires_login" class="field">
      <label for="max-attempts">Максимум попыток</label><input id="max-attempts" v-model.number="form.max_attempts" type="number" min="1" max="1000" step="1">
      <p class="hint">Пусто — без ограничения</p>
    </div>
    <label class="checkbox-label"><input v-model="form.take_by_blocks" type="checkbox"> Проходить по блокам</label>
    <label class="checkbox-label"><input v-model="form.allow_free_navigation" type="checkbox"> Свободная навигация</label>
    <label class="checkbox-label"><input v-model="form.shuffle_answer_options" type="checkbox"> Перемешивать варианты ответов</label>
    <template v-if="form.is_test">
      <label class="checkbox-label"><input type="checkbox" :checked="form.time_limit_minutes !== null" @change="toggleTime(form, $event.target.checked)"> Ограничить время</label>
      <div v-if="form.time_limit_minutes !== null" class="field">
        <label for="time-limit">Минуты</label><input id="time-limit" v-model.number="form.time_limit_minutes" type="number" min="1" max="1440" step="1">
      </div>
      <label class="checkbox-label"><input v-model="form.shuffle_questions" type="checkbox"> Перемешивать вопросы</label>
      <label class="checkbox-label"><input v-model="form.show_correct_answers" type="checkbox"> Показывать правильные ответы после прохождения</label>
      <label class="checkbox-label"><input v-model="form.show_results_by_block" type="checkbox"> Показывать результат по блокам</label>
    </template>
    <div class="field">
      <label for="completion-message">Сообщение после завершения</label>
      <textarea id="completion-message" v-model="form.completion_message" rows="3" aria-describedby="completion-hint completion-count"></textarea>
      <p id="completion-count" class="hint">{{ [...(form.completion_message || '')].length }} / 1000</p>
      <p id="completion-hint" class="hint">Простой текст, без форматирования</p>
    </div>
    </fieldset>
  </fieldset>
</template>
