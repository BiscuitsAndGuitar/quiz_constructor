import test from 'node:test'
import assert from 'node:assert/strict'
import { formContext, answerBlockTitle, attemptDetails, gradesChart, daysChart, blocksChart, optionLabel, optionsChart, sortedQuestions, shortText, duration, localDate, attemptRow } from './statistics.js'

test('Диаграммы сохраняют порядок, нули, дни UTC и подписи блоков', () => {
  const grades = gradesChart([{ grade: '2', count: 0 }, { grade: '5', count: 3 }])
  assert.deepEqual(grades.labels, ['2', '5'])
  assert.deepEqual(grades.datasets[0].data, [0, 3])
  const days = daysChart([{ date: '2026-11-01', count: 2 }, { date: '2026-11-02', count: 0 }])
  assert.deepEqual(days.labels, ['2026-11-01', '2026-11-02'])
  assert.deepEqual(days.datasets[0].data, [2, 0])
  const blocks = blocksChart([{ title: 'Тема', avg_percent: 70 }, { title: null, avg_percent: 0 }])
  assert.deepEqual(blocks.labels, ['Тема', 'Блок 2'])
  assert.deepEqual(blocks.datasets[0].data, [70, 0])
  assert.deepEqual(gradesChart().labels, [])
})

test('Варианты: число, процент и знак правильного ответа, не только цвет', () => {
  const option = { text: 'Ответ', count: 3, percent: 60, is_correct: true }
  assert.equal(optionLabel(option), '✓ Ответ — 3 (60%)')
  assert.equal(optionLabel({ ...option, is_correct: false }), 'Ответ — 3 (60%)')
  const data = optionsChart([option, { ...option, is_correct: false }])
  assert.deepEqual(data.datasets[0].data, [3, 3])
  assert.notEqual(...data.datasets[0].backgroundColor)
})

test('Сложные вопросы: стабильный порядок, исходные номера, без изменения входа', () => {
  const questions = [{ question_id: 1, correct_percent: 80 }, { question_id: 2, correct_percent: 20 }, { question_id: 3, correct_percent: 20 }, { question_id: 4, type: 'info' }]
  assert.deepEqual(sortedQuestions(questions, true).map(row => row.number), [2, 3, 1])
  assert.deepEqual(sortedQuestions(questions).map(row => row.question_id), [1, 2, 3])
  assert.equal(questions[0].number, undefined)
})

test('Сокращение текста сохраняет Unicode и полное исходное значение', () => {
  assert.equal(shortText('а'.repeat(100)), 'а'.repeat(100))
  assert.equal(shortText('😀'.repeat(101)), `${'😀'.repeat(100)}…`)
})

test('Время: секунды, минуты, часы и отсутствие данных', () => {
  for (const [value, expected] of [[0, '0 с'], [59, '59 с'], [60, '1 мин 0 с'], [96, '1 мин 36 с'], [3600, '1 ч 0 мин 0 с'], [3661, '1 ч 1 мин 1 с'], [null, '—']]) assert.equal(duration(value), expected)
  assert.equal(localDate('2026-11-03T03:00:00'), new Date('2026-11-03T03:00:00Z').toLocaleString('ru-RU'))
  assert.equal(localDate('2026-11-03T06:00:00+03:00'), localDate('2026-11-03T03:00:00Z'))
})

test('Прохождения: оценка, отсутствие оценки, опрос, досрочно, незавершённая и аноним', () => {
  const attempt = { user: { name: 'Анна' }, is_finished: true, score: 5, max_score: 10, grade: '3', started_at: '2026-11-03T03:00:00' }
  assert.equal(attemptRow(attempt, true).result, '5/10, оценка 3')
  assert.equal(attemptRow({ ...attempt, grade: null }, true).result, '5/10')
  assert.equal(attemptRow(attempt, false).result, '')
  assert.equal(attemptRow(attempt, false).status, 'завершена')
  assert.equal(attemptRow({ ...attempt, finished_early: true }, false).status, 'досрочно')
  const unfinished = attemptRow({ ...attempt, user: null, is_finished: false }, true)
  assert.equal(unfinished.name, 'Аноним')
  assert.equal(unfinished.result, '')
  assert.equal(unfinished.status, 'не завершена')
})

test('Номера блоков берутся из всей формы, включая пустые и скрытые блоки', () => {
  const form = { is_test: false, blocks: [{ questions: [] }, { questions: [{ key: 'q25', finish_rules: [] }] }, { questions: [{ key: 'q40', finish_rules: [{ key: 'r1' }] }] }] }
  const context = formContext(form)
  assert.deepEqual(context.questionBlocks, { 25: 2, 40: 3 })
  assert.equal(answerBlockTitle({ question_id: 40, block_title: null }, context.questionBlocks), '3 (без названия)')
  assert.equal(answerBlockTitle({ question_id: 25, block_title: '' }, context.questionBlocks), '2 (без названия)')
  assert.equal(answerBlockTitle({ question_id: 25, block_title: 'Название' }, context.questionBlocks), 'Название')
  assert.equal(context.hasRules, true)
  assert.equal(formContext({ ...form, is_test: true }).hasRules, false)
  assert.equal(formContext({ is_test: false, blocks: [{ questions: [{ key: 'q1', finish_rules: [] }] }] }).hasRules, false)
})

test('Недоступная форма: запасная подпись и пояснение о правилах', () => {
  const context = formContext(null)
  assert.equal(context.hasRules, true)
  assert.equal(answerBlockTitle({ question_id: 99, block_title: null }, context.questionBlocks), 'без названия')
  assert.equal(answerBlockTitle({ question_id: 99, block_title: 'Тема' }, context.questionBlocks), 'Тема')
})

test('Ответы: полные тексты и обновление номеров после поздней загрузки формы', () => {
  const data = { attempt: { user: null, started_at: '2026-11-03T03:00:00', is_finished: true }, answers: [{ question_id: 40, block_title: null, text_answer: 'я\n'.repeat(1000), selected_options: [] }] }
  assert.equal(attemptDetails(data, {}, false).answers[0].blockTitle, 'без названия')
  const details = attemptDetails(data, { 40: 3 }, false)
  assert.equal(details.answers[0].blockTitle, '3 (без названия)')
  assert.equal(details.answers[0].text_answer, data.answers[0].text_answer)
  assert.ok(details.title.startsWith('Аноним, '))
  assert.equal(data.answers[0].blockTitle, undefined)
})
