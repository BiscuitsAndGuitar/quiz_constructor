import assert from 'node:assert/strict'
import test from 'node:test'
import { changeQuestionType, formSavePayload, newOption, newQuestion } from './formEditor.js'

test('Сохранение передаёт все настройки и делает независимый снимок', () => {
  const form = { id: 1, is_test: true, is_published: false, public_code: 'abcd1234', title: 'Тест',
    description: null, requires_login: true, max_attempts: 2, time_limit_minutes: 30,
    take_by_blocks: true, allow_free_navigation: true, shuffle_questions: true,
    shuffle_answer_options: true, show_correct_answers: true, show_results_by_block: true,
    completion_message: 'Спасибо', blocks: [{ key: 'b1', title: null, questions: [newQuestion()] },
      { key: 'b2', title: 'Второй', questions: [] }] }
  const payload = formSavePayload(form)
  assert.deepEqual(Object.keys(payload).sort(), Object.keys(form).filter(key => !['id', 'is_test', 'is_published', 'public_code'].includes(key)).sort())
  for (const key of Object.keys(payload)) assert.deepEqual(payload[key], form[key])
  form.blocks[0].questions[0].text = 'Позднее изменение'
  assert.equal(payload.blocks[0].questions[0].text, '')
})

test('Смена на текстовый тип удаляет варианты, смена single/multiple сохраняет их', () => {
  const question = newQuestion()
  const option = newOption()
  question.options.push(option)
  changeQuestionType(question, 'multiple')
  assert.deepEqual(question.options, [option])
  changeQuestionType(question, 'text')
  assert.equal(question.type, 'text')
  assert.deepEqual(question.options, [])
})

test('Новые элементы имеют разные временные ключи', () => {
  const elements = [newQuestion(), newQuestion(), newOption(), newOption()]
  assert.equal(new Set(elements.map(element => element.key)).size, elements.length)
})
