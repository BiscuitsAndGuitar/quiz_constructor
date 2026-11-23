<script setup>
import { computed, onBeforeUnmount, ref, toRaw, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { getForm, saveForm, publishForm, copyForm } from '../api/forms.js'
import { participantLink, copyParticipantLink, isReadOnly } from '../utils/formPublication.js'
import { addBlock, formSavePayload, formSnapshot, hasFormChanges, moveBlock, moveQuestion,
  newBlock, prepareFormForEditor, questionNumbers, removeBlock, totalPoints } from '../utils/formEditor.js'
import BlockEditor from '../components/BlockEditor.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import FormSettings from '../components/FormSettings.vue'
import GradingScaleEditor from '../components/GradingScaleEditor.vue'
import NoAccessPage from './NoAccessPage.vue'
import NotFoundPage from './NotFoundPage.vue'
import { deletionReferences, referenceErrors } from '../utils/conditions.js'
import MessageDialog from '../components/MessageDialog.vue'
import { collapseAllSections, settingsSection, gradingSection, expandForErrors, remapCollapsed, toggleCollapsed } from '../utils/editorDisplay.js'

const route = useRoute()
const router = useRouter()
const form = ref(null)
const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const errorStatus = ref(null)
const saved = ref(false)
const snapshot = ref('')
const leaveDialog = ref(null)
const deleteDialog = ref(null)
const messageDialog = ref(null)
const publishDialog = ref(null)
const publishing = ref(false)
const copying = ref(false)
const copiedLink = ref(false)
let copyNoticeTimer
const readOnly = computed(() => isReadOnly(form.value))
const busy = computed(() => saving.value || publishing.value || copying.value)
const publicLink = computed(() => form.value ? participantLink(window.location.origin, form.value.public_code) : '')
onBeforeUnmount(() => clearTimeout(copyNoticeTimer))
// Только состояние отображения: не входит в форму, снимок и запрос сохранения.
const collapsed = ref(new Set())
const dirty = computed(() => !!form.value && !form.value.is_published && hasFormChanges(form.value, snapshot.value))
const numbers = computed(() => questionNumbers(form.value?.blocks || []))

async function confirmLeave() {
  if (!dirty.value) return true
  return leaveDialog.value.ask({ title: 'Несохранённые изменения',
    message: 'Несохранённые изменения будут потеряны. Сохраните их',
    cancelText: 'Остаться', confirmText: 'Уйти без сохранения' })
}

onBeforeRouteLeave(confirmLeave)
onBeforeRouteUpdate((to, from) => to.params.id !== from.params.id ? confirmLeave() : true)

function beforeUnload(event) {
  if (!dirty.value) return
  event.preventDefault()
  event.returnValue = ''
}

watch(dirty, changed => {
  if (changed) window.addEventListener('beforeunload', beforeUnload)
  else window.removeEventListener('beforeunload', beforeUnload)
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload))

function showMessage(message) {
  messageDialog.value.show(message)
}

function handleError(error, savingError = false) {
  if (savingError) {
    const detail = error.detail ?? error.message
    collapsed.value = expandForErrors(collapsed.value, detail)
    messageDialog.value.show(detail, 'Не удалось сохранить форму')
  } else errorMessage.value = error.message
  errorStatus.value = error.status
  if (error.status === 401) router.replace({ path: '/login', query: { redirect: route.fullPath } })
  if (error.status === 409 && form.value) form.value.is_published = true
}

async function loadForm(id) {
  copiedLink.value = false
  loading.value = true
  errorMessage.value = ''
  errorStatus.value = null
  saved.value = false
  form.value = null
  collapsed.value = new Set()
  try {
    const result = await getForm(id)
    if (route.params.id === id) {
      form.value = prepareFormForEditor(result)
      snapshot.value = formSnapshot(form.value)
    }
  } catch (error) {
    if (route.params.id === id) handleError(error)
  } finally {
    if (route.params.id === id) loading.value = false
  }
}

async function deleteBlock(index) {
  if (saving.value || form.value.is_published || form.value.blocks.length === 1) return
  const block = form.value.blocks[index]
  const places = deletionReferences(form.value.blocks, block.questions.map(question => question.key), null, index)
  if (places.length) {
    showMessage(['Нельзя удалить блок. Сначала удалите ссылки:', ...places])
    return
  }
  if (block.questions.length && !await deleteDialog.value.ask({ title: 'Удалить блок?',
    message: `Будут удалены блок и вопросы в нём (${block.questions.length}). Продолжить?`,
    confirmText: 'Удалить блок' })) return
  const currentIndex = form.value.blocks.findIndex(item => item.key === block.key)
  form.value.blocks = removeBlock(form.value.blocks, currentIndex)
}

function applyMove(blocks) {
  const errors = referenceErrors(blocks)
  if (errors.length) {
    showMessage(['Нельзя переместить. Сначала измените условия:', ...errors])
    return
  }
  errorMessage.value = ''
  form.value.blocks = blocks
}

async function save() {
  if (busy.value || readOnly.value) return
  saving.value = true
  saved.value = false
  errorMessage.value = ''
  errorStatus.value = null
  const id = route.params.id
  try {
    // Снимок всего ответа GET сохраняет настройки и остальные блоки, если они созданы через API.
    const result = await saveForm(id, formSavePayload(toRaw(form.value)))
    if (route.params.id === id) {
      collapsed.value = remapCollapsed(collapsed.value, form.value.blocks, result.blocks)
      form.value = result
      snapshot.value = formSnapshot(form.value)
      saved.value = true
    }
  } catch (error) {
    if (route.params.id === id) handleError(error, true)
  } finally {
    saving.value = false
  }
}

async function publish() {
  if (busy.value || readOnly.value) return
  if (dirty.value) { showMessage('Сначала сохраните изменения'); return }
  if (!await publishDialog.value.ask({ title: 'Опубликовать форму?',
    message: 'После публикации форму нельзя редактировать. Для изменений нужно создать копию. Опубликовать?',
    confirmText: 'Опубликовать' })) return
  const id = route.params.id
  publishing.value = true
  try {
    const result = await publishForm(id)
    if (route.params.id === id) {
      Object.assign(form.value, result)
      saved.value = false
      // В черновике могли показываться ещё не сохранённые значения по умолчанию.
      // В режиме просмотра показываем только опубликованные данные сервера.
      try {
        const published = await getForm(id)
        if (route.params.id === id) form.value = published
      } catch (error) {
        if (route.params.id === id) messageDialog.value.show(error.detail ?? error.message, 'Форма опубликована, но не удалось обновить просмотр')
      }
    }
  } catch (error) {
    if (route.params.id === id) {
      const detail = error.problems?.length ? error.problems : (error.detail ?? error.message)
      collapsed.value = expandForErrors(collapsed.value, detail)
      messageDialog.value.show(detail, 'Не удалось опубликовать форму')
      if (error.status === 409) await loadForm(id)
      if (error.status === 401) router.replace({ path: '/login', query: { redirect: route.fullPath } })
    }
  } finally { publishing.value = false }
}

async function createCopy() {
  if (busy.value) return
  copying.value = true
  try {
    const result = await copyForm(form.value.id)
    await router.push(`/forms/${result.id}/edit`)
  } catch (error) { showMessage(error.detail ?? error.message) }
  finally { copying.value = false }
}

async function copyLink() {
  copiedLink.value = await copyParticipantLink(publicLink.value, navigator.clipboard)
  if (!copiedLink.value) showMessage(['Скопируйте ссылку вручную:', publicLink.value])
  clearTimeout(copyNoticeTimer)
  copyNoticeTimer = setTimeout(() => { copiedLink.value = false }, 3000)
}

watch(() => route.params.id, loadForm, { immediate: true })
</script>

<template>
  <NoAccessPage v-if="errorStatus === 403" />
  <NotFoundPage v-else-if="errorStatus === 404" />
  <section v-else>
    <p v-if="loading" role="status">Загрузка…</p>
    <template v-else>
      <h1>{{ form?.is_test ? 'Конструктор теста' : 'Конструктор опроса' }}</h1>
      <p v-if="errorMessage" role="alert" class="error">{{ errorMessage }}</p>
      <button v-if="!form" @click="loadForm(route.params.id)">Повторить</button>
      <template v-else>
        <div v-if="readOnly">
          <p role="status">Форма опубликована и не редактируется</p>
          <div class="actions"><a :href="publicLink">{{ publicLink }}</a><button type="button" @click="copyLink">Копировать</button>
            <span v-if="copiedLink" role="status">Скопировано</span>
            <button type="button" :disabled="busy" @click="createCopy">Создать копию для редактирования</button>
          </div>
        </div>
        <form novalidate @submit.prevent="save">
          <div class="editor-toolbar">
            <div class="field"><label for="form-title">Название</label><input id="form-title" v-model="form.title" :disabled="busy || readOnly"></div>
            <button v-if="!readOnly" :disabled="busy">{{ saving ? 'Сохраняем…' : 'Сохранить' }}</button>
            <button v-if="!readOnly" type="button" :disabled="busy" @click="publish">{{ publishing ? 'Публикуем…' : 'Опубликовать' }}</button>
            <span v-if="dirty" role="status">Есть несохранённые изменения</span>
            <span v-else-if="saved && !readOnly" role="status">Сохранено</span>
            <RouterLink to="/my/forms">К списку</RouterLink>
          </div>
          <div class="actions collapse-actions">
            <button type="button" @click="collapsed = collapseAllSections(form)">Свернуть всё</button>
            <button type="button" @click="collapsed = new Set()">Развернуть всё</button>
          </div>
          <fieldset :disabled="busy">
            <FormSettings :read-only="readOnly" :form="form" :collapsed="collapsed.has(settingsSection)" @toggle="collapsed = toggleCollapsed(collapsed, settingsSection)" />
            <BlockEditor v-for="(block, index) in form.blocks" :key="block.key" :blocks="form.blocks" :index="index"
              :numbers="numbers[index]" :is-test="form.is_test" :disabled="busy" :read-only="readOnly"
              :collapsed="collapsed" @toggle="collapsed = toggleCollapsed(collapsed, $event)"
              @error="showMessage"
              @remove="deleteBlock(index)" @move="applyMove(moveBlock(form.blocks, index, $event))"
              @move-question="(questionIndex, direction) => applyMove(moveQuestion(form.blocks, index, questionIndex, direction))" />
            <button v-if="!readOnly" type="button" @click="form.blocks = addBlock(form.blocks, newBlock())">Добавить блок</button>
            <GradingScaleEditor v-if="form.is_test" :read-only="readOnly" :scale="form.grading_scale" :collapsed="collapsed.has(gradingSection)" @toggle="collapsed = toggleCollapsed(collapsed, gradingSection)" />
            <p v-if="form.is_test" class="total-points">Всего баллов: {{ totalPoints(form) }}</p>
          </fieldset>
        </form>
      </template>
    </template>
  </section>
  <ConfirmDialog ref="leaveDialog" />
  <ConfirmDialog ref="deleteDialog" />
  <MessageDialog ref="messageDialog" />
  <ConfirmDialog ref="publishDialog" />
</template>
