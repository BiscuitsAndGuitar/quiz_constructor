<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { listLibraryBlocks } from '../api/library.js'
import { libraryParams } from '../utils/library.js'
const props = defineProps({ fixedType: { default: null }, selecting: Boolean, disabled: Boolean })
const emit = defineEmits(['edit', 'delete', 'select', 'error'])
const filters = reactive({ query: '', scope: 'all', type: 'all', tag: '' })
const items = ref([]), loading = ref(false), error = ref(''), more = ref(false)
let timer, generation = 0, retryOffset = 0
const filtered = computed(() => !!filters.query.trim() || !!filters.tag || filters.scope !== 'all' || filters.type !== 'all')
async function load(offset = 0) {
  clearTimeout(timer)
  const current = ++generation
  retryOffset = offset
  loading.value = true
  error.value = ''
  try {
    const rows = await listLibraryBlocks(libraryParams(filters, offset, props.fixedType))
    if (current !== generation) return
    items.value = offset ? [...items.value, ...rows] : rows
    more.value = rows.length === 20
  } catch (err) {
    if (current !== generation) return
    error.value = err.message
    emit('error', err)
  } finally { if (current === generation) loading.value = false }
}
function refresh() {
  items.value = []
  more.value = false
  load()
}
watch(() => [filters.query, filters.scope, filters.type, filters.tag, props.fixedType], () => {
  // Ответ прежнего поиска не должен подменять список после смены фильтров.
  generation++
  clearTimeout(timer)
  items.value = []
  error.value = ''
  more.value = false
  loading.value = true
  timer = setTimeout(() => load(), 300)
}, { flush: 'sync' })
load()
onBeforeUnmount(() => { clearTimeout(timer); generation++ })
defineExpose({ refresh })
</script>

<template>
  <div>
    <div class="filters">
      <label>Поиск <input v-model="filters.query" type="search" placeholder="Название, описание или тег"></label>
      <label>Доступ <select v-model="filters.scope"><option value="all">Все</option><option value="mine">Мои</option><option value="public">Публичные</option></select></label>
      <label v-if="fixedType === null">Тип <select v-model="filters.type"><option value="all">Все</option><option value="survey">Опросы</option><option value="test">Тесты</option></select></label>
    </div>
    <p v-if="filters.tag">Тег: {{ filters.tag }} <button type="button" aria-label="Сбросить фильтр по тегу" @click="filters.tag = ''">×</button></p>
    <article v-for="item in items" :key="item.id" class="library-card">
      <h2>{{ item.title }}</h2><p v-if="item.description" class="plain-text">{{ item.description }}</p>
      <p>{{ item.is_test ? 'Тест' : 'Опрос' }} · Вопросов: {{ item.questions_count }} · Автор: {{ item.is_mine ? 'Вы' : item.owner_name }} <span v-if="item.is_public">· Публичный</span></p>
      <div class="actions"><button v-for="tag in item.tags" :key="tag" type="button" @click="filters.tag = tag">{{ tag }}</button></div>
      <div class="actions">
        <button v-if="selecting" type="button" :disabled="disabled" @click="emit('select', item)">Добавить</button>
        <template v-else-if="item.is_mine"><button type="button" :disabled="disabled" @click="emit('edit', item)">Изменить</button><button type="button" :disabled="disabled" @click="emit('delete', item)">Удалить</button></template>
      </div>
    </article>
    <p v-if="loading" role="status">Загрузка…</p>
    <div v-else-if="error" role="alert"><p class="error">{{ error }}</p><button type="button" @click="load(retryOffset)">Повторить</button></div>
    <p v-else-if="!items.length">{{ filtered ? 'Ничего не найдено' : 'В библиотеке пока нет блоков' }}</p>
    <button v-if="more && !error" type="button" :disabled="loading" @click="load(items.length)">Показать ещё</button>
  </div>
</template>

<style scoped>
.library-card { border: 1px solid #ccc; padding: 1rem; margin: 1rem 0; overflow-wrap: anywhere; }
.library-card .actions { margin-top: 0.5rem; }
</style>
