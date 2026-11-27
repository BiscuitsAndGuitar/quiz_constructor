<script setup>
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { createLibraryBlock, updateLibraryBlock, libraryTags } from '../api/library.js'
import { libraryPayload, normalizeTags } from '../utils/library.js'
import { messageLines } from '../utils/editorDisplay.js'
const props = defineProps({ item: Object, block: Object, isTest: Boolean })
const emit = defineEmits(['close', 'saved', 'error'])
const dialog = ref(null), busy = ref(false), errors = ref([])
const metadata = reactive({ title: props.item?.title ?? props.block?.title ?? '', description: props.item?.description ?? '',
  tags: [...(props.item?.tags ?? [])], is_public: props.item?.is_public ?? false })
const tagInput = ref(''), tagError = ref(''), suggestions = ref([]), suggestionError = ref('')
let timer, generation = 0, active = true
function close() { if (!busy.value) emit('close') }
function addTags(value = tagInput.value) {
  try {
    metadata.tags = normalizeTags([...metadata.tags, ...value.split(',')])
    tagInput.value = ''
    tagError.value = ''
    suggestions.value = []
    return true
  } catch (error) { tagError.value = error.message; return false }
}
function tagKey(event) {
  if (event.isComposing || !['Enter', ','].includes(event.key)) return
  event.preventDefault()
  addTags()
}
watch(tagInput, value => {
  clearTimeout(timer)
  const current = ++generation
  suggestions.value = []
  suggestionError.value = ''
  if (!value.trim()) return
  timer = setTimeout(async () => {
    try {
      const rows = await libraryTags(value.trim().replace(/\s+/gu, ' ').toLowerCase())
      if (current === generation) suggestions.value = rows.filter(row => !metadata.tags.includes(row.name))
    } catch (error) {
      if (current !== generation) return
      suggestionError.value = 'Не удалось загрузить подсказки. Тег можно ввести вручную.'
      emit('error', error)
    }
  }, 300)
})
async function save() {
  if (busy.value) return
  errors.value = []
  if (!addTags()) return
  const title = metadata.title.trim()
  if (!title || [...title].length > 255) { errors.value = ['Название должно содержать от 1 до 255 символов']; return }
  busy.value = true
  try {
    const result = props.item
      ? await updateLibraryBlock(props.item.id, { ...metadata, title, description: metadata.description.trim() || null })
      : await createLibraryBlock(libraryPayload(props.block, props.isTest, metadata))
    if (active) emit('saved', result)
  } catch (error) {
    if (!active) return
    errors.value = messageLines(error.detail ?? error.message)
    emit('error', error)
  } finally { busy.value = false }
}
onMounted(() => dialog.value.showModal())
onBeforeUnmount(() => { active = false; generation++; clearTimeout(timer) })
</script>

<template>
  <dialog ref="dialog" class="library-metadata-dialog" aria-labelledby="library-metadata-heading" @cancel.prevent="close">
    <h2 id="library-metadata-heading">{{ item ? 'Изменить блок библиотеки' : 'Сохранить в библиотеку' }}</h2>
    <form novalidate @submit.prevent="save">
      <fieldset :disabled="busy" class="editor-fields">
        <div class="field"><label for="library-title">Название</label><input id="library-title" v-model="metadata.title" autofocus required></div>
        <div class="field"><label for="library-description">Описание</label><textarea id="library-description" v-model="metadata.description" rows="3"></textarea></div>
        <div class="field">
          <label for="library-tags">Теги</label><input id="library-tags" v-model="tagInput" @keydown="tagKey" aria-describedby="library-tag-hint">
          <p id="library-tag-hint" class="hint">Enter или запятая — добавить тег. До 10 тегов, до 30 символов каждый.</p>
          <div class="actions"><span v-for="tag in metadata.tags" :key="tag">{{ tag }} <button type="button" :aria-label="`Удалить тег ${tag}`" @click="metadata.tags = metadata.tags.filter(value => value !== tag); tagError = ''">×</button></span></div>
          <p v-if="tagError" class="error" role="alert">{{ tagError }}</p>
          <p v-if="suggestionError" class="hint">{{ suggestionError }}</p>
          <div v-if="suggestions.length" class="actions" aria-label="Подсказки тегов"><button v-for="tag in suggestions" :key="tag.name" type="button" @click="addTags(tag.name)">{{ tag.name }} ({{ tag.count }})</button></div>
        </div>
        <label class="checkbox-label"><input v-model="metadata.is_public" type="checkbox"> Публичный</label>
        <p v-if="isTest && metadata.is_public" role="note">Публичный блок показывает правильные ответы всем составителям</p>
      </fieldset>
      <ul v-if="errors.length" class="error" role="alert"><li v-for="(error, index) in errors" :key="index">{{ error }}</li></ul>
      <div class="actions"><button :disabled="busy">{{ busy ? 'Сохраняем…' : 'Сохранить' }}</button><button type="button" :disabled="busy" @click="close">Отмена</button></div>
    </form>
  </dialog>
</template>

<style scoped>
.library-metadata-dialog { width: min(600px, calc(100vw - 48px)); max-height: 85vh; overflow-y: auto; overflow-wrap: anywhere; }
</style>
