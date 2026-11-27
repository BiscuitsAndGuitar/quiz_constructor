<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LibraryList from '../components/LibraryList.vue'
import LibraryMetadataDialog from '../components/LibraryMetadataDialog.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import MessageDialog from '../components/MessageDialog.vue'
import { deleteLibraryBlock } from '../api/library.js'
const router = useRouter(), route = useRoute()
const list = ref(null), edited = ref(null), confirm = ref(null), message = ref(null), busy = ref(false)
function handleError(error) {
  if (error.status === 401) router.replace({ path: '/login', query: { redirect: route.fullPath } })
}
function saved() { edited.value = null; list.value.refresh() }
async function remove(item) {
  if (busy.value) return
  if (!await confirm.value.ask({ title: 'Удалить блок?', message: 'Блок будет удалён из библиотеки. Формы, в которые он был вставлен, не изменятся', confirmText: 'Удалить' })) return
  busy.value = true
  try { await deleteLibraryBlock(item.id); list.value.refresh() }
  catch (error) { handleError(error); message.value.show(error.detail ?? error.message) }
  finally { busy.value = false }
}
</script>

<template>
  <section><h1>Библиотека блоков</h1><LibraryList ref="list" :disabled="busy" @edit="edited = $event" @delete="remove" @error="handleError" /></section>
  <LibraryMetadataDialog v-if="edited" :item="edited" :is-test="edited.is_test" @close="edited = null" @saved="saved" @error="handleError" />
  <ConfirmDialog ref="confirm" /><MessageDialog ref="message" />
</template>
