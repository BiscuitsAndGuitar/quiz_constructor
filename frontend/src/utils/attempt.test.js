import test from 'node:test'
import assert from 'node:assert/strict'
import { conditionMatches, visibleContent, attemptPages, pageIndex, missingRequired, finishAnswers, remainingMilliseconds, safeRedirect } from './attempt.js'
import { createAttemptState, saveAttempt, loadAttempt, removeAttempt, saveAttemptKey, loadAttemptKey } from './attemptStorage.js'
import { limitTextAnswer } from './attempt.js'

test('Текстовый ответ: границы 1000/1001, длинная вставка и защита finish', () => {
  assert.equal(limitTextAnswer('я'.repeat(1000)), 'я'.repeat(1000))
  assert.equal(limitTextAnswer('я'.repeat(1001)), 'я'.repeat(1000))
  assert.equal(limitTextAnswer('a'.repeat(10000)).length, 1000)
  assert.equal(limitTextAnswer('a'.repeat(999) + '😀'), 'a'.repeat(999))
  assert.equal(limitTextAnswer('😀'.repeat(501)), '😀'.repeat(500))
  assert.deepEqual(finishAnswers([{ id: 1, type: 'text' }], { 1: { text: 'я'.repeat(1001) } }),
    [{ question_id: 1, text: 'я'.repeat(1000) }])
})

const condition = (question_id, operator, value = {}) => ({ match_all: true, items: [{ question_id, operator, ...value }] })
const question = (id, extra = {}) => ({ id, type: 'text', is_answer_required: false, ...extra })
function form(extra = {}) {
  return { is_test: false, take_by_blocks: false, question_order: [1, 2, 3, 4], blocks: [
    { id: 1, questions: [question(1), question(2)] }, { id: 2, questions: [question(3), question(4)] },
  ], ...extra }
}
const ids = content => content.blocks.flatMap(b => b.questions.map(q => q.id))

for (const [operator, value, present, absent] of [
  ['chosen', { option_id: 10 }, true, false], ['not_chosen', { option_id: 10 }, false, true],
  ['equals', { text_answer: ' Да   Конечно ' }, true, false], ['contains', { text_answer: 'ДА  кон' }, true, false],
  ['answered', {}, true, false], ['not_answered', {}, false, true],
]) test(`Условие ${operator}: ответ и отсутствие ответа`, () => {
  assert.equal(conditionMatches(condition(1, operator, value), { 1: { text: ' да  КОНЕЧНО ', option_ids: [10] } }), present)
  assert.equal(conditionMatches(condition(1, operator, value), {}), absent)
})
test('Условия: все или любое; пустой ответ', () => {
  const data = { match_all: true, items: [...condition(1, 'answered').items, ...condition(2, 'answered').items] }
  assert.equal(conditionMatches(data, { 1: { text: 'x' } }), false)
  data.match_all = false
  assert.equal(conditionMatches(data, { 1: { text: 'x' } }), true)
  assert.equal(conditionMatches(condition(1, 'answered'), { 1: { text: ' \n ' } }), false)
})
test('Видимость сверху вниз: скрытый ответ отсутствует, скрытый блок и info', () => {
  const data = form()
  data.blocks[0].questions[0].condition = condition(99, 'answered')
  data.blocks[0].questions[1].condition = condition(1, 'not_answered')
  data.blocks[1].condition = condition(1, 'answered')
  assert.deepEqual(ids(visibleContent(data, { 1: { text: 'скрыто' } })), [2])
  data.blocks[0].questions[0] = question(1, { type: 'info', condition: condition(99, 'not_answered') })
  assert.deepEqual(ids(visibleContent(data, { 1: { text: 'не ответ' } })), [1, 2])
  data.is_test = true
  assert.deepEqual(ids(visibleContent(data, {})), [1, 2, 3, 4])
})
for (const byBlocks of [false, true]) test(`Первое правило, ссылка на себя, режим блоков ${byBlocks}`, () => {
  const data = form({ take_by_blocks: byBlocks })
  data.blocks[0].questions[0].finish_rules = [
    { id: 1, condition: condition(1, 'not_answered') },
    { id: 2, condition: condition(1, 'answered') },
    { id: 3, condition: condition(1, 'answered') },
  ]
  const answers = { 1: { text: 'да' }, 3: { text: 'лишний' } }
  assert.deepEqual(ids(visibleContent(data, answers)), [1, 2, 3, 4])
  const result = visibleContent(data, answers, true)
  assert.equal(result.rule.id, 2)
  assert.deepEqual(ids(result), byBlocks ? [1, 2] : [1])
  assert.equal(visibleContent(data, answers, true, [3]).rule, null)
})
test('Правила скрытого вопроса и info не действуют; последнее правило действует', () => {
  const data = form()
  const rule = { id: 10, condition: condition(1, 'not_answered') }
  data.blocks[0].questions[0] = question(1, { condition: condition(99, 'answered'), finish_rules: [rule] })
  data.blocks[0].questions[1] = question(2, { type: 'info', finish_rules: [rule] })
  assert.equal(visibleContent(data, {}, true).rule, null)
  data.blocks[1].questions[1].finish_rules = [rule]
  assert.equal(visibleContent(data, {}, true).rule.id, 10)
})
test('Страницы: порядок сервера, info над вопросом, нумерация и переходы', () => {
  const data = form({ question_order: [4, 1, 3, 2] })
  data.blocks[1].questions[1].type = 'info'
  data.blocks[0].questions[1].type = 'info'
  const pages = attemptPages(data, data.blocks)
  assert.deepEqual(pages.map(p => p.questions.map(q => q.id)), [[4, 1], [2, 3]])
  assert.deepEqual([...pages[0].numbered], [[1, 1], [3, 2]])
  assert.equal(pageIndex(pages, pages[1].key), 1)
  assert.equal(pageIndex(pages, pages[0].key), 0)
  assert.equal(pageIndex(pages, 'hidden', 8), 1)
  assert.equal(pageIndex([], 'hidden'), 0)
})
test('Страницы блоков пропускают скрытые; только info остаётся без номера', () => {
  const data = form({ take_by_blocks: true })
  data.blocks[0].condition = condition(99, 'answered')
  assert.deepEqual(attemptPages(data, visibleContent(data, {}).blocks).map(p => p.key), ['b2'])
  data.take_by_blocks = false
  data.blocks[1].questions.forEach(q => { q.type = 'info' })
  const pages = attemptPages(data, visibleContent(data, {}).blocks)
  assert.equal(pages.length, 1)
  assert.equal(pages[0].numbered.size, 0)
})
test('Обязательные только у опросов, только видимые; тело finish без пустых и info', () => {
  const data = form()
  data.blocks[0].questions[0].is_answer_required = true
  data.blocks[0].questions[1].type = 'single'
  data.blocks[1].questions[0].type = 'info'
  const questions = data.blocks.flatMap(b => b.questions)
  const answers = { 1: { text: '   ' }, 2: { option_ids: [8], text: 'не отправлять' }, 3: { text: 'info' }, 4: { text: ' да ' }, 99: { text: 'чужой' } }
  assert.deepEqual(missingRequired(data, questions, answers), [1])
  assert.deepEqual(missingRequired({ ...data, is_test: true }, questions, answers), [])
  assert.deepEqual(missingRequired(data, questions.slice(1), answers), [])
  assert.deepEqual(finishAnswers(questions, answers), [{ question_id: 2, option_ids: [8] }, { question_id: 4, text: ' да ' }])
})
test('Таймер зависит от длительности, а не от даты серверных часов', () => {
  assert.equal(remainingMilliseconds(60000, 1000, 11000), 50000)
  assert.equal(remainingMilliseconds(60000, 1000, 90000), 0)
  assert.equal(remainingMilliseconds(null, 1000, 90000), null)
  const state = createAttemptState({ attempt: { id: 1, started_at: '2000-01-01T00:00:00', deadline: '2000-01-01T00:01:00' }, form: form() }, 'CODE', 1000)
  assert.equal(state.duration, 60000)
  assert.equal(remainingMilliseconds(state.duration, state.receivedAt, 11000), 50000)
})
test('Хранилище: восстановление формы, ответов, позиции, времени и отдельного ключа', () => {
  const values = new Map()
  const storage = { setItem: (k, v) => values.set(k, v), getItem: k => values.get(k) ?? null, removeItem: k => values.delete(k) }
  const state = createAttemptState({ attempt: { id: 7, deadline: null }, form: form() }, 'CODE', 1000)
  state.answers = { 1: { text: 'Да' } }; state.pageKey = 'q2'; state.position = 1
  saveAttempt(storage, state)
  saveAttemptKey(storage, 7, 'secret')
  assert.deepEqual(loadAttempt(storage, 7), state)
  assert.equal(loadAttempt(storage, 8), null)
  removeAttempt(storage, 7)
  assert.equal(loadAttempt(storage, 7), null)
  assert.equal(loadAttemptKey(storage, 7), 'secret')
  storage.setItem('quiz_attempt_7', '{broken')
  assert.equal(loadAttempt(storage, 7), null)
  assert.equal(loadAttempt({ getItem() { throw Error() } }, 7), null)
})
test('Безопасный возврат: только внутренний путь', () => {
  assert.equal(safeRedirect('/f/ABC?x=1'), '/f/ABC?x=1')
  for (const value of ['//evil.com', 'https://evil.com', '/\\evil.com', '/\nevil', null, ['/f/a']]) assert.equal(safeRedirect(value), null)
})
