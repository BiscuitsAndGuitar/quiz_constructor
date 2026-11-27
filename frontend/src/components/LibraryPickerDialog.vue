<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import LibraryList from './LibraryList.vue'
import { getLibraryBlock } from '../api/library.js'
import { messageLines } from '../utils/editorDisplay.js'
const props = defineProps({ isTest: Boolean })
const emit = defineEmits(['close', 'selected', 'error'])
const dialog = ref(null), busy = ref(false), errors = ref([])
let active = true
function close() { if (!busy.value) emit('close') }
async function select(item) {
  if (busy.value) return
  busy.value = true
  errors.value = []
  try {
    const result = await getLibraryBlock(item.id)
    if (!active) return
    if (result.is_test !== props.isTest) throw new Error('Блок можно добавить только в форму того же типа')
    emit('selected', result.block)
  } catch (error) {
    if (!active) return
    errors.value = messageLines(error.detail ?? error.message)
    emit('error', error)
  } finally { busy.value = false }
}
onMounted(() => dialog.value.showModal())
onBeforeUnmount(() => { active = false })
</script>

<template>
  <dialog ref="dialog" class="library-picker-dialog" aria-labelledby="library-picker-heading" @cancel.prevent="close">
    <h2 id="library-picker-heading">Добавить из библиотеки</h2>
    <LibraryList selecting :fixed-type="isTest" :disabled="busy" @select="select" @error="emit('error', $event)" />
    <p v-if="busy" role="status">Загрузка блока…</p>
    <ul v-if="errors.length" class="error" role="alert"><li v-for="(error, index) in errors" :key="index">{{ error }}</li></ul>
    <button type="button" :disabled="busy" @click="close">Закрыть</button>
  </dialog>
</template>

<style scoped>
.library-picker-dialog { width: min(900px, calc(100vw - 48px)); max-height: 85vh; overflow-y: auto; }
</style>
