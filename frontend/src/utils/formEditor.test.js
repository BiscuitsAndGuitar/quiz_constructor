import assert from 'node:assert/strict'
import test from 'node:test'
import { reactive, toRaw } from 'vue'
import { changeQuestionType, defaultGradingScale, formSavePayload, newOption, newQuestion,
  prepareFormForEditor, sortGradingScale, totalPoints, addBlock, removeBlock, moveBlock,
  moveQuestion, canMoveQuestion, newBlock, questionNumbers, formSnapshot, hasFormChanges } from './formEditor.js'

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

function blocksWithQuestions(...counts) {
  let number = 0
  return counts.map((count, index) => ({ key: `b${index}`, title: null,
    questions: Array.from({ length: count }, () => ({ key: `q${++number}`, text: `Вопрос ${number}`, options: [] })) }))
}

test('Добавление и удаление блока не меняют исходный массив, единственный блок остаётся', () => {
  const blocks = blocksWithQuestions(1)
  const block = newBlock()
  const result = addBlock(blocks, block)
  assert.equal(blocks.length, 1)
  assert.equal(result.length, 2)
  assert.deepEqual(block.questions, [])
  assert.equal(block.title, null)
  assert.notEqual(block.key, newBlock().key)
  assert.deepEqual(removeBlock(result, 0), [block])
  assert.deepEqual(removeBlock(blocks, 0), blocks)
})

test('Блоки меняются местами; крайние стрелки ничего не меняют', () => {
  const blocks = blocksWithQuestions(1, 0, 2)
  assert.deepEqual(moveBlock(blocks, 1, -1).map(b => b.key), ['b1', 'b0', 'b2'])
  assert.deepEqual(moveBlock(blocks, 1, 1).map(b => b.key), ['b0', 'b2', 'b1'])
  assert.deepEqual(moveBlock(blocks, 0, -1), blocks)
  assert.deepEqual(moveBlock(blocks, 2, 1), blocks)
  assert.deepEqual(blocks.map(b => b.key), ['b0', 'b1', 'b2'])
})

test('Вопросы перемещаются внутри блока и через границу, сохраняя свои данные', () => {
  const blocks = blocksWithQuestions(2, 2)
  const original = structuredClone(blocks)
  assert.deepEqual(moveQuestion(blocks, 0, 0, 1)[0].questions.map(q => q.key), ['q2', 'q1'])
  assert.deepEqual(moveQuestion(blocks, 0, 1, -1)[0].questions.map(q => q.key), ['q2', 'q1'])
  const down = moveQuestion(blocks, 0, 1, 1)
  assert.deepEqual(down.map(b => b.questions.map(q => q.key)), [['q1'], ['q2', 'q3', 'q4']])
  const up = moveQuestion(blocks, 1, 0, -1)
  assert.deepEqual(up.map(b => b.questions.map(q => q.key)), [['q1', 'q2', 'q3'], ['q4']])
  assert.deepEqual(blocks, original)
  assert.equal(canMoveQuestion(blocks, 0, 0, -1), false)
  assert.equal(canMoveQuestion(blocks, 1, 1, 1), false)
  assert.deepEqual(moveQuestion(blocks, 0, 0, -1), blocks)
  assert.deepEqual(moveQuestion(blocks, 1, 1, 1), blocks)
})

test('Блок 1 пустой, единственный вопрос блока 2 переносится вверх; исходный блок остаётся', () => {
  const blocks = blocksWithQuestions(0, 1)
  assert.equal(canMoveQuestion(blocks, 1, 0, -1), true)
  const result = moveQuestion(blocks, 1, 0, -1)
  assert.deepEqual(result.map(b => b.questions.map(q => q.key)), [['q1'], []])
  assert.equal(result.length, 2)
  assert.equal(canMoveQuestion(result, 0, 0, 1), true)
  assert.deepEqual(moveQuestion(result, 0, 0, 1), blocks)
})

test('Цепочка пустых блоков не пропускается в обоих направлениях', () => {
  const blocks = blocksWithQuestions(0, 0, 1)
  const step1 = moveQuestion(blocks, 2, 0, -1)
  assert.deepEqual(step1.map(b => b.questions.length), [0, 1, 0])
  const step2 = moveQuestion(step1, 1, 0, -1)
  assert.deepEqual(step2.map(b => b.questions.length), [1, 0, 0])
  assert.equal(canMoveQuestion(step2, 0, 0, -1), false)
  const step3 = moveQuestion(step2, 0, 0, 1)
  assert.deepEqual(step3.map(b => b.questions.length), [0, 1, 0])
  assert.deepEqual(moveQuestion(step3, 1, 0, 1), blocks)
})

test('Один блок с одним вопросом: обе стрелки недоступны', () => {
  const blocks = blocksWithQuestions(1)
  for (const direction of [-1, 1]) {
    assert.equal(canMoveQuestion(blocks, 0, 0, direction), false)
    assert.deepEqual(moveQuestion(blocks, 0, 0, direction), blocks)
  }
})

test('Нумерация сквозная, пустые блоки не создают пропусков', () => {
  const blocks = blocksWithQuestions(2, 0, 1, 2)
  assert.deepEqual(questionNumbers(blocks), [[1, 2], [], [3], [4, 5]])
  assert.deepEqual(questionNumbers(moveBlock(blocks, 3, -1)), [[1, 2], [], [3, 4], [5]])
})

test('Сохранение после переноса реактивных вопросов Vue не содержит прокси', () => {
  const form = reactive({ is_test: false, title: 'Опрос', blocks: blocksWithQuestions(1, 0) })
  form.blocks = moveQuestion(form.blocks, 0, 0, 1)
  form.blocks = moveBlock(form.blocks, 1, -1)
  const payload = formSavePayload(toRaw(form))
  assert.deepEqual(payload.blocks.map(b => b.questions.map(q => q.key)), [['q1'], []])
  assert.doesNotThrow(() => structuredClone(payload))
  form.blocks[0].questions[0].text = 'Изменено позже'
  assert.equal(payload.blocks[0].questions[0].text, 'Вопрос 1')
})

test('Снимок замечает изменения любых данных и возврат к прежнему состоянию', () => {
  const form = { id: 1, is_test: true, public_code: 'abc', is_published: false, title: 'Тест',
    requires_login: true, max_attempts: 2, completion_message: null, blocks: blocksWithQuestions(1, 0),
    grading_scale: defaultGradingScale() }
  Object.assign(form.blocks[0].questions[0], { points: 1, type: 'text', allow_partial_scoring: false, correct_text_answers: [] })
  const snapshot = formSnapshot(form)
  assert.equal(hasFormChanges(form, snapshot), false)
  for (const change of [f => f.title += '!', f => f.max_attempts++, f => f.blocks[0].title = 'Блок',
    f => f.blocks[0].questions[0].points++, f => f.blocks[0].questions[0].correct_text_answers.push('Да'),
    f => f.grading_scale[0].message = 'Сообщение', f => f.blocks.reverse(),
    f => f.blocks[0].questions.push(newQuestion(true))]) {
    const changed = structuredClone(form)
    change(changed)
    assert.equal(hasFormChanges(changed, snapshot), true)
  }
  form.title = 'Другой'
  assert.equal(hasFormChanges(form, snapshot), true)
  form.title = 'Тест'
  assert.equal(hasFormChanges(form, snapshot), false)
  form.blocks[0].title = '  '
  assert.equal(hasFormChanges(form, snapshot), false)
  form.public_code = 'другой'
  assert.equal(hasFormChanges(form, snapshot), false)
  form.description = ''
  form.grading_scale[0].message = ''
  assert.equal(hasFormChanges(form, snapshot), false)
})
