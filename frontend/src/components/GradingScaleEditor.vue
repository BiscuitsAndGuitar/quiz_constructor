<script setup>
defineProps({ scale: { type: Array, required: true }, collapsed: Boolean, readOnly: Boolean })
defineEmits(['change', 'toggle'])
</script>

<template>
  <section class="grading-editor" @input="$emit('change')" @change="$emit('change')">
    <h2><button type="button" :title="collapsed ? 'Развернуть шкалу оценок' : 'Свернуть шкалу оценок'" :aria-expanded="!collapsed" @click="$emit('toggle')">{{ collapsed ? '▸' : '▾' }}</button> Шкала оценок</h2>
    <p v-if="collapsed">Строк: {{ scale.length }}</p>
    <fieldset v-show="!collapsed" :disabled="readOnly" class="editor-fields">
    <p class="hint">Если шкала заполнена, добавьте строку от 0%. Границы не должны повторяться.</p>
    <div class="table-scroll">
      <table>
        <thead><tr><th>От, %</th><th>Оценка</th><th>Сообщение для этой оценки</th><th v-if="!readOnly">Действия</th></tr></thead>
        <tbody>
          <tr v-for="(row, index) in scale" :key="index">
            <td><input v-model.number="row.min_percent" type="number" min="0" max="100" step="1" :aria-label="`Граница ${index + 1}, %`"></td>
            <td><input v-model="row.grade" :aria-label="`Оценка ${index + 1}`"></td>
            <td><textarea v-model="row.message" rows="2" :aria-label="`Сообщение оценки ${index + 1}`"></textarea><p class="hint">Необязательно, до 1000 символов</p></td>
            <td v-if="!readOnly"><button type="button" :aria-label="`Удалить оценку ${index + 1}`" @click="scale.splice(index, 1); $emit('change')">Удалить</button></td>
          </tr>
        </tbody>
      </table>
    </div>
    <button v-if="!readOnly" type="button" @click="scale.push({ min_percent: 0, grade: '', message: null }); $emit('change')">Добавить оценку</button>
    </fieldset>
  </section>
</template>
