import test from 'node:test'
import assert from 'node:assert/strict'
import { parseFormCode, historyResult, filterAttempts, completionDate, previewForm } from './participant.js'
import { attemptPages, visibleContent, missingRequired } from './attempt.js'

test('Код: обычный, ссылка, параметры, фрагмент, завершающий путь и пробелы', () => {
  for (const input of ['CODE', ' CODE ', 'https://example.org/f/CODE', 'https://example.org/f/CODE?x=1#end', '/f/CODE#end', '/f/CODE/extra', '/f/%43ODE']) {
    assert.equal(parseFormCode(input), 'CODE')
  }
  for (const input of ['', ' \n ', 'https://example.org/f/?x=1', '/f/']) assert.equal(parseFormCode(input), '')
})
test('Результат истории: оценка, отсутствие оценки, опрос, незавершённая', () => {
  const attempt = { is_finished: true, form: { is_test: true }, score: 5, max_score: 6, grade: '4' }
  assert.equal(historyResult(attempt), '5/6, оценка 4')
  assert.equal(historyResult({ ...attempt, grade: null }), '5/6')
  assert.equal(historyResult({ ...attempt, form: { is_test: false } }), 'пройден')
  assert.equal(historyResult({ ...attempt, is_finished: false }), '')
})
test('Фильтр истории не меняет порядок; серверная дата считается UTC', () => {
  const items = [{ form: { is_test: true } }, { form: { is_test: false } }, { form: { is_test: true } }]
  assert.deepEqual(filterAttempts(items, 'all'), items)
  assert.deepEqual(filterAttempts(items, 'survey'), [items[1]])
  assert.deepEqual(filterAttempts(items, 'test'), [items[0], items[2]])
  assert.equal(completionDate('2026-11-24T12:30:00').toISOString(), '2026-11-24T12:30:00.000Z')
  assert.equal(completionDate('2026-11-24T12:30:00Z').toISOString(), '2026-11-24T12:30:00.000Z')
  assert.equal(completionDate(null), null)
})

function editor() {
  return { title: 'Черновик', is_test: false, take_by_blocks: false, allow_free_navigation: true,
    completion_message: 'Спасибо', blocks: [
      { key: 'empty', title: null, questions: [] },
      { key: 'b', title: null, questions: [
        { key: 'new-q', type: 'single', text: '', is_answer_required: true, options: [{ key: 'new-o', text: 'Да' }],
          finish_rules: [{ key: 'r', message: 'Готово', condition: { match_all: true, items: [{ question: 'new-q', operator: 'chosen', option: 'new-o' }] } }] },
        { key: 'info', type: 'info', text: 'Подсказка', image: { id: 42, url: '/uploads/test.png' },
          condition: { match_all: true, items: [{ question: 'new-q', operator: 'answered' }] } },
        { key: 'text', type: 'text', text: 'Текст', options: [] },
      ] },
      { key: 'last', title: 'Последний', condition: { match_all: false, items: [{ question: 'text', operator: 'contains', text_answer: 'да' }] },
        questions: [{ key: 'last-q', type: 'text', text: 'Последний вопрос' }] },
    ] }
}
test('Предпросмотр: числовые номера, ссылки условий и правил, пустой блок и info', () => {
  const source = editor(), snapshot = JSON.stringify(source)
  const form = previewForm(source)
  assert.deepEqual(form.question_order, [1, 2, 3, 4])
  assert.equal(form.blocks[1].title, null)
  assert.equal(form.blocks[1].questions[0].text, '')
  assert.deepEqual(form.blocks[1].questions[0].options, [{ id: 1, text: 'Да' }])
  const rule = form.blocks[1].questions[0].finish_rules[0]
  assert.equal(typeof rule.id, 'number')
  assert.deepEqual(rule.condition.items, [{ question_id: 1, operator: 'chosen', option_id: 1 }])
  assert.deepEqual(form.blocks[2].condition.items, [{ question_id: 3, operator: 'contains', text_answer: 'да' }])
  assert.equal(form.blocks[1].questions[1].type, 'info')
  assert.deepEqual(form.blocks[1].questions[1].image, { id: 42, url: '/uploads/test.png' })
  assert.equal(visibleContent(form, { 1: { option_ids: [1] } }, true).rule.message, 'Готово')
  assert.deepEqual(missingRequired(form, form.blocks[1].questions, {}), [1])
  for (const byBlocks of [true, false]) {
    form.take_by_blocks = byBlocks
    const pages = attemptPages(form, visibleContent(form, {}).blocks)
    assert.equal(pages.length, byBlocks ? 1 : 2)
  }
  form.blocks[1].questions[1].image.url = '/changed'
  assert.equal(JSON.stringify(source), snapshot)
})
test('Предпросмотр теста сохраняет порядок редактора, не переносит баллы и правильность', () => {
  const source = editor()
  source.is_test = true
  source.shuffle_questions = true
  source.shuffle_answer_options = true
  source.blocks[1].questions[0].points = 10
  source.blocks[1].questions[0].options[0].is_correct = true
  const form = previewForm(source)
  assert.deepEqual(form.question_order, [1, 2, 3, 4])
  assert.equal('points' in form.blocks[1].questions[0], false)
  assert.equal('is_correct' in form.blocks[1].questions[0].options[0], false)
  assert.equal(visibleContent(form, {}, true).rule, null)
  assert.deepEqual(attemptPages(previewForm({ blocks: [] }), []), [])
})
