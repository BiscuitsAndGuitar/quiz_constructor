<script setup>
import { computed, ref, toRaw, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getForm, saveForm } from '../api/forms.js'
import { formSavePayload, newQuestion } from '../utils/formEditor.js'
import QuestionEditor from '../components/QuestionEditor.vue'
import NoAccessPage from './NoAccessPage.vue'
import NotFoundPage from './NotFoundPage.vue'

const route = useRoute()
const router = useRouter()
const form = ref(null)
const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const errorStatus = ref(null)
const saved = ref(false)
const firstBlock = computed(() => form.value?.blocks[0])

function handleError(error) {
  errorMessage.value = error.message
  errorStatus.value = error.status
  if (error.status === 401) router.replace({ path: '/login', query: { redirect: route.fullPath } })
  if (error.status === 409 && form.value) form.value.is_published = true
}

async function loadForm(id) {
  loading.value = true
  errorMessage.value = ''
  errorStatus.value = null
  saved.value = false
  form.value = null
  try {
    const result = await getForm(id)
    if (route.params.id === id) form.value = result
  } catch (error) {
    if (route.params.id === id) handleError(error)
  } finally {
    if (route.params.id === id) loading.value = false
  }
}

function addQuestion() {
  firstBlock.value.questions.push(newQuestion())
  saved.value = false
}

function removeQuestion(index) {
  firstBlock.value.questions.splice(index, 1)
  saved.value = false
}

async function save() {
  if (saving.value || form.value.is_published) return
  saving.value = true
  saved.value = false
  errorMessage.value = ''
  errorStatus.value = null
  const id = route.params.id
  try {
    // Снимок всего ответа GET сохраняет настройки и остальные блоки, если они созданы через API.
    const result = await saveForm(id, formSavePayload(toRaw(form.value)))
    if (route.params.id === id) {
      form.value = result
      saved.value = true
    }
  } catch (error) {
    if (route.params.id === id) handleError(error)
  } finally {
    saving.value = false
  }
}

watch(() => route.params.id, loadForm, { immediate: true })
</script>

<template>
  <NoAccessPage v-if="errorStatus === 403" />
  <NotFoundPage v-else-if="errorStatus === 404" />
  <section v-else>
    <p v-if="loading" role="status">Загрузка…</p>
    <template v-else>
      <div class="actions"><h1>{{ form?.is_test ? 'Конструктор теста' : 'Конструктор опроса' }}</h1><RouterLink to="/my/forms">К списку</RouterLink></div>
      <p v-if="errorMessage" role="alert" class="error">{{ errorMessage }}</p>
      <button v-if="!form" @click="loadForm(route.params.id)">Повторить</button>
      <template v-else>
        <p v-if="form.is_test">Баллы, правильные ответы и шкала оценок появятся на следующем этапе</p>
        <p v-if="form.is_published" role="status">Опубликованную форму нельзя редактировать</p>
        <form novalidate @submit.prevent="save">
          <fieldset :disabled="saving || form.is_published">
            <div class="field"><label for="form-title">Название</label><input id="form-title" v-model="form.title" @input="saved = false"></div>
            <div class="actions"><button :disabled="saving || form.is_published">{{ saving ? 'Сохраняем…' : 'Сохранить' }}</button><span v-if="saved" role="status">Сохранено</span></div>
            <div class="field form-description"><label for="form-description">Описание</label><textarea id="form-description" v-model="form.description" rows="3" @input="saved = false"></textarea></div>
            <template v-if="firstBlock">
              <QuestionEditor v-for="(question, index) in firstBlock.questions" :key="question.key" :question="question" :number="index + 1" :is-test="form.is_test" :disabled="saving || form.is_published" @remove="removeQuestion(index)" @change="saved = false" />
              <button type="button" @click="addQuestion">Добавить вопрос</button>
            </template>
          </fieldset>
        </form>
      </template>
    </template>
  </section>
</template>
