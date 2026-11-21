import test from 'node:test'
import assert from 'node:assert/strict'
import { collapseAll, expandForErrors, messageLines, questionSummary, remapCollapsed, toggleCollapsed } from './editorDisplay.js'
import { formSavePayload, formSnapshot, moveQuestion } from './formEditor.js'
import { collapseAllSections, settingsSection, gradingSection, settingsSummary } from './editorDisplay.js'

test('Свернуть всё охватывает разделы, блоки и вопросы; шкала есть только у теста', () => {
  const form = { blocks: blocks(), is_test: true }
  const before = formSnapshot(form)
  const payload = formSavePayload(form)
  const state = collapseAllSections(form)
  assert.equal(state.size, 6)
  assert.ok(state.has(settingsSection) && state.has(gradingSection) && state.has('q1'))
  assert.equal(toggleCollapsed(state, settingsSection).has(settingsSection), false)
  assert.equal(state.has(settingsSection), true)
  assert.equal(collapseAllSections({ ...form, is_test: false }).has(gradingSection), false)
  assert.equal(new Set().has(settingsSection), false)
  assert.equal(formSnapshot(form), before)
  assert.deepEqual(formSavePayload(form), payload)
})

test('Состояние разделов сохраняется после замены ключей сервером', () => {
  const state = collapseAllSections({ blocks: blocks(), is_test: true })
  const next = remapCollapsed(state, blocks(), [{ key: 'new', questions: [{ key: 'new-q' }] }])
  assert.ok(next.has(settingsSection) && next.has(gradingSection) && next.has('new-q'))
})

test('Ошибки настроек и шкалы раскрывают соответствующие разделы', () => {
  const state = collapseAllSections({ blocks: blocks(), is_test: true })
  for (const message of ['Максимум попыток должен быть целым числом', 'Ограничение времени должно быть от 1 до 1440', 'Неверный доступ']) {
    const next = expandForErrors(state, message)
    assert.equal(next.has(settingsSection), false)
    assert.equal(next.has(gradingSection), true)
    assert.equal(next.has('q1'), true)
  }
  for (const message of ['В шкале оценок должна быть строка с границей 0%', 'Граница шкалы должна быть целым числом']) {
    const next = expandForErrors(state, message)
    assert.equal(next.has(gradingSection), false)
    assert.equal(next.has(settingsSection), true)
  }
  const both = expandForErrors(state, ['Максимум попыток: ошибка', 'Шкала: ошибка'])
  assert.equal(both.has(settingsSection), false)
  assert.equal(both.has(gradingSection), false)
  assert.deepEqual(expandForErrors(state, 'Нет связи с сервером'), state)
})

test('Сводка настроек показывает доступ, режим и только заданное время теста', () => {
  assert.equal(settingsSummary({}), 'Доступ: всем · Проходить по блокам: нет')
  assert.equal(settingsSummary({ is_test: true, requires_login: true, take_by_blocks: true, time_limit_minutes: 30 }),
    'Доступ: только авторизованным · Проходить по блокам: да · Ограничение времени: 30 мин')
  assert.doesNotMatch(settingsSummary({ is_test: true, time_limit_minutes: null }), /времени/)
})

function blocks() {
  return [{ key: 'b1', questions: [{ key: 'q1', text: 'Первый', type: 'text', options: [] }] },
    { key: 'b2', questions: [{ key: 'q2', text: 'Второй', type: 'text', options: [] }] }]
}

test('Начальное состояние раскрыто, переключение независимо и не меняет исходный Set', () => {
  const initial = new Set()
  const one = toggleCollapsed(initial, 'q1')
  assert.equal(initial.size, 0)
  assert.deepEqual([...one], ['q1'])
  assert.deepEqual([...toggleCollapsed(one, 'q1')], [])
  assert.deepEqual([...toggleCollapsed(one, 'b1')], ['q1', 'b1'])
})

test('Свернуть всё включает блоки и вопросы, новые элементы остаются раскрытыми', () => {
  const data = blocks()
  const collapsed = collapseAll(data)
  assert.deepEqual([...collapsed], ['b1', 'q1', 'b2', 'q2'])
  data.push({ key: 'b3', questions: [{ key: 'q3' }] })
  assert.equal(collapsed.has('b3'), false)
  assert.equal(collapsed.has('q3'), false)
  assert.equal(new Set().size, 0)
  assert.deepEqual([...collapseAll([])], [])
})

test('Сворачивание не меняет запрос, снимок и состояние после перемещения', () => {
  const form = { is_test: false, blocks: blocks() }
  const before = formSnapshot(form)
  const payload = formSavePayload(form)
  const collapsed = collapseAll(form.blocks)
  toggleCollapsed(collapsed, 'b1')
  assert.equal(formSnapshot(form), before)
  assert.deepEqual(formSavePayload(form), payload)
  const moved = moveQuestion(form.blocks, 0, 0, 1)
  assert.equal(collapsed.has(moved[1].questions[0].key), true)
})

test('После PUT состояние переносится на новые ключи, удалённые ключи исчезают', () => {
  const before = blocks()
  const after = [{ key: 'b11', questions: [{ key: 'q11' }] }, { key: 'b22', questions: [{ key: 'q22' }] }]
  assert.deepEqual([...remapCollapsed(new Set(['b1', 'q2', 'deleted']), before, after)], ['b11', 'q22'])
})

test('Ошибка с номером вопроса или блока раскрывает карточки; общая ошибка сохраняет состояние', () => {
  const collapsed = collapseAll(blocks())
  for (const detail of ['Вопрос 2: укажите баллы', 'Условие блока 2: ошибка', ['Ошибка', 'Правило 1 вопроса 2: ошибка']]) {
    assert.equal(expandForErrors(collapsed, detail).size, 0)
  }
  assert.deepEqual(expandForErrors(collapsed, 'Нет связи с сервером'), collapsed)
  assert.equal(collapsed.size, 4)
})

test('Сообщение принимает строки, списки и сообщения ошибок валидации', () => {
  assert.deepEqual(messageLines('Первая\nВторая'), ['Первая', 'Вторая'])
  assert.deepEqual(messageLines(['Ошибка 1', { msg: 'Ошибка 2' }]), ['Ошибка 1', 'Ошибка 2'])
  assert.deepEqual(messageLines(null), ['Не удалось выполнить запрос'])
})

test('Краткий текст вопроса обрезается и не содержит переносов', () => {
  assert.equal(questionSummary({ text: '  Первый\n вопрос  ' }), 'Первый вопрос')
  assert.equal(questionSummary({ text: '' }), 'Без текста')
  assert.equal(questionSummary({ text: 'я'.repeat(100) }), 'я'.repeat(90) + '…')
})
