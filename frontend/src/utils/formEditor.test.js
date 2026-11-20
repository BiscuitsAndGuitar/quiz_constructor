import assert from 'node:assert/strict'
import test from 'node:test'
import { changeQuestionType, defaultGradingScale, formSavePayload, newOption, newQuestion,
  prepareFormForEditor, sortGradingScale, totalPoints } from './formEditor.js'

test('Сохранение передаёт все настройки и делает независимый снимок', () => {
  const form = { id: 1, is_test: true, is_published: false, public_code: 'abcd1234', title: 'Тест',
    description: null, requires_login: true, max_attempts: 2, time_limit_minutes: 30,
    take_by_blocks: true, allow_free_navigation: true, shuffle_questions: true,
    shuffle_answer_options: true, show_correct_answers: true, show_results_by_block: true,
    completion_message: 'Спасибо', blocks: [{ key: 'b1', title: null, questions: [newQuestion(true)] },
      { key: 'b2', title: 'Второй', questions: [] }] }
  const payload = formSavePayload(form)
  assert.deepEqual(Object.keys(payload).sort(), Object.keys(form).filter(key => !['id', 'is_test', 'is_published', 'public_code'].includes(key)).sort())
  for (const key of Object.keys(payload).filter(key => key !== 'blocks')) assert.deepEqual(payload[key], form[key])
  const expectedBlocks = structuredClone(form.blocks)
  delete expectedBlocks[0].questions[0].is_answer_required
  assert.deepEqual(payload.blocks, expectedBlocks)
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

test('Баллы суммируются по всем вопросам и пересчитываются после изменения и удаления', () => {
  const form = { blocks: [{ questions: [{ points: 2 }, { points: 3 }] }, { questions: [{ points: 4 }] }] }
  assert.equal(totalPoints(form), 9)
  form.blocks[0].questions[0].points = 10
  assert.equal(totalPoints(form), 17)
  form.blocks[1].questions.pop()
  assert.equal(totalPoints(form), 13)
  form.blocks[0].questions[1].points = ''
  assert.equal(totalPoints(form), 10)
})

test('Стандартная шкала и старые null-баллы подставляются без изменения исходной формы', () => {
  const form = { is_test: true, grading_scale: [], blocks: [{ questions: [{ points: null }, { points: 7 }] }] }
  const result = prepareFormForEditor(form)
  assert.deepEqual(result.grading_scale.map(row => [row.min_percent, row.grade]), [[0, '2'], [50, '3'], [70, '4'], [85, '5']])
  assert.deepEqual(result.blocks[0].questions.map(q => q.points), [1, 7])
  assert.equal(form.blocks[0].questions[0].points, null)
  assert.deepEqual(form.grading_scale, [])
  result.grading_scale[0].grade = 'Изменено'
  assert.equal(defaultGradingScale()[0].grade, '2')
  form.grading_scale = [{ min_percent: 0, grade: 'Зачёт', message: 'Готово' }]
  assert.deepEqual(prepareFormForEditor(form).grading_scale, form.grading_scale)
})

test('Смена типа очищает верные варианты, частичные баллы и допустимые ответы', () => {
  const question = newQuestion(true)
  question.options = [{ ...newOption(true), text: 'А', is_correct: true }, { ...newOption(true), text: 'Б', is_correct: true }]
  question.type = 'multiple'
  question.allow_partial_scoring = true
  changeQuestionType(question, 'single')
  assert.deepEqual(question.options.map(o => o.is_correct), [false, false])
  assert.equal(question.allow_partial_scoring, false)
  assert.deepEqual(question.options.map(o => o.text), ['А', 'Б'])
  changeQuestionType(question, 'text')
  assert.deepEqual(question.options, [])
  assert.deepEqual(question.correct_text_answers, [])
  question.correct_text_answers.push('Ответ')
  changeQuestionType(question, 'multiple')
  assert.equal('correct_text_answers' in question, false)
  assert.equal(question.points, 1)
})

test('Шкала сортируется в запросе, исходный порядок редактора не меняется', () => {
  const scale = [{ min_percent: 70, grade: '4' }, { min_percent: 0, grade: '2' }]
  assert.deepEqual(sortGradingScale(scale).map(row => row.min_percent), [0, 70])
  const form = { is_test: true, requires_login: false, max_attempts: null, grading_scale: scale, blocks: [] }
  assert.deepEqual(formSavePayload(form).grading_scale.map(row => row.min_percent), [0, 70])
  assert.equal(scale[0].min_percent, 70)
  form.grading_scale = []
  assert.deepEqual(formSavePayload(form).grading_scale, [])
})

test('Опрос отправляет общие настройки, но ни одного поля теста', () => {
  const question = newQuestion(true)
  question.correct_text_answers = ['А']
  question.options = [{ ...newOption(true), is_correct: true }]
  const form = { is_test: false, title: 'Опрос', requires_login: false, max_attempts: 4,
    time_limit_minutes: null, shuffle_questions: false, show_correct_answers: false,
    show_results_by_block: false, grading_scale: [], completion_message: '',
    take_by_blocks: true, allow_free_navigation: true, shuffle_answer_options: true,
    blocks: [{ key: 'b1', questions: [question] }] }
  const payload = formSavePayload(form)
  for (const key of ['grading_scale', 'time_limit_minutes', 'shuffle_questions', 'show_correct_answers', 'show_results_by_block']) assert.equal(key in payload, false)
  const savedQuestion = payload.blocks[0].questions[0]
  for (const key of ['points', 'allow_partial_scoring', 'correct_text_answers']) assert.equal(key in savedQuestion, false)
  assert.equal('is_correct' in savedQuestion.options[0], false)
  assert.equal(savedQuestion.is_answer_required, false)
  assert.equal(payload.max_attempts, null)
  assert.equal(payload.completion_message, null)
  assert.ok(payload.take_by_blocks && payload.allow_free_navigation && payload.shuffle_answer_options)
  assert.equal(question.options[0].is_correct, true)
})

test('Запрос теста сохраняет баллы, верные варианты, ответы и сообщения', () => {
  const question = { ...newQuestion(true), type: 'text', points: 8, correct_text_answers: ['Москва'] }
  const form = { is_test: true, requires_login: true, max_attempts: '', completion_message: 'Спасибо',
    blocks: [{ questions: [question] }], grading_scale: [{ min_percent: 0, grade: '5', message: 'Отлично' }] }
  const payload = formSavePayload(form)
  assert.equal(payload.blocks[0].questions[0].points, 8)
  assert.deepEqual(payload.blocks[0].questions[0].correct_text_answers, ['Москва'])
  assert.equal(payload.max_attempts, null)
  assert.equal(payload.grading_scale[0].message, 'Отлично')
})
