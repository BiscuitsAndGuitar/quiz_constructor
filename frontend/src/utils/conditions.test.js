import test from 'node:test'
import assert from 'node:assert/strict'
import { availableQuestions, deletionReferences, operatorsFor, referenceErrors, typeChangeErrors } from './conditions.js'
import { formSavePayload, formSnapshot, moveBlock, moveQuestion } from './formEditor.js'

const condition = (question, operator = 'answered', value = {}) => ({ match_all: true, items: [{ question, operator, ...value }] })
function blocks() {
  return [
    { key: 'b1', questions: [{ key: 'q1', type: 'single', options: [{ key: 'o1', text: 'Да' }] },
      { key: 'q2', type: 'text', options: [], condition: condition('q1') }] },
    { key: 'b2', condition: condition('q1'), questions: [{ key: 'q3', type: 'multiple', options: [],
      finish_rules: [{ key: 'r1', condition: condition('q3') }, { key: 'r2', condition: condition('q2') }] }] },
  ]
}

test('Выбор вопросов учитывает границы блока, текущий вопрос правила и исключает info', () => {
  const data = blocks()
  assert.deepEqual(availableQuestions(data, 0), [])
  assert.deepEqual(availableQuestions(data, 0, 0), [])
  assert.deepEqual(availableQuestions(data, 0, 1).map(item => item.question.key), ['q1'])
  assert.deepEqual(availableQuestions(data, 1).map(item => item.question.key), ['q1', 'q2'])
  assert.deepEqual(availableQuestions(data, 1, 0, true).map(item => item.question.key), ['q1', 'q2', 'q3'])
  data[0].questions[0].type = 'info'
  assert.deepEqual(availableQuestions(data, 1).map(item => item.question.key), ['q2'])
  assert.deepEqual(operatorsFor('info'), [])
})

test('Проверка порядка: вопрос, блок, правило на себя и на более поздний вопрос', () => {
  const data = blocks()
  assert.deepEqual(referenceErrors(data), [])
  assert.match(referenceErrors(moveQuestion(data, 0, 0, 1)).join(), /Условие вопроса 1.*вопрос 2/)
  assert.match(referenceErrors(moveBlock(data, 0, 1)).join(), /Условие блока 1/)
  data[1].questions[0].finish_rules[0].condition = condition('q1')
  assert.deepEqual(referenceErrors(data), [])
  data[0].questions[0].finish_rules = [{ key: 'later', condition: condition('q3') }]
  assert.match(referenceErrors(data).join(), /не позже/)
  data[0].condition = condition('q1')
  assert.match(referenceErrors(data).join(), /Условие блока 1/)
})

test('Перенос через границу проверяет ссылки блоков и не пропускает пустые блоки', () => {
  const data = blocks()
  const moved = moveQuestion(data, 0, 1, 1)
  assert.deepEqual(referenceErrors(moved), [])
  const invalid = moveQuestion(moved, 0, 0, 1)
  assert.match(referenceErrors(invalid).join(), /Условие блока 2/)
  const empty = [{ key: 'e1', questions: [] }, { key: 'e2', questions: [] }, data[0]]
  assert.deepEqual(referenceErrors(moveQuestion(empty, 2, 0, -1)), [])
  assert.equal(moveQuestion(empty, 2, 0, -1)[1].questions[0].key, 'q1')
})

test('Удаление показывает все внешние ссылки, но разрешает удалить внутренние вместе с владельцем', () => {
  const data = blocks()
  assert.deepEqual(deletionReferences(data, ['q1']), ['Условие вопроса 2', 'Условие блока 2'])
  assert.deepEqual(deletionReferences(data, ['q1', 'q2'], null, 0), ['Условие блока 2', 'Правило 2 вопроса 3'])
  assert.deepEqual(deletionReferences(data, ['q3']), [])
  assert.deepEqual(deletionReferences(data, ['q3'], null, 1), [])
  data[0].questions[1].condition = condition('q1', 'chosen', { option: 'o1' })
  data[0].questions[0].finish_rules = [{ key: 'self', condition: condition('q1', 'not_chosen', { option: 'o1' }) }]
  assert.deepEqual(deletionReferences(data, [], 'o1'), ['Правило 1 вопроса 1', 'Условие вопроса 2'])
  assert.deepEqual(deletionReferences(data, [], 'unused'), [])
})

test('Смена типа блокируется только когда ссылки становятся некорректными; оригинал не меняется', () => {
  const data = blocks()
  assert.deepEqual(typeChangeErrors(data, 'q1', 'text'), []) // answered подходит обоим типам
  data[0].questions[1].condition = condition('q1', 'chosen', { option: 'o1' })
  assert.match(typeChangeErrors(data, 'q1', 'text').join(), /оператор не подходит/)
  assert.deepEqual(typeChangeErrors(data, 'q1', 'multiple'), [])
  assert.equal(data[0].questions[0].type, 'single')
  data[1].questions[0].condition = condition('q2', 'contains', { text_answer: 'да' })
  assert.match(typeChangeErrors(data, 'q2', 'single').join(), /оператор не подходит/)
})

test('Прямые проверки info запрещают ссылки и собственные правила', () => {
  const data = blocks()
  data[0].questions[0].type = 'info'
  assert.match(referenceErrors(data).join(), /Текст без вопроса/)
  data[1].questions[0].type = 'info'
  assert.match(referenceErrors(data).join(), /не может быть правил/)
})

test('Ссылки на удалённые вопросы и варианты обнаруживаются', () => {
  const data = blocks()
  data[0].questions[1].condition = condition('q1', 'chosen', { option: 'missing' })
  assert.match(referenceErrors(data).join(), /удалённый вариант/)
  data[0].questions[1].condition = condition('missing')
  assert.match(referenceErrors(data).join(), /missing/)
})

test('Тело опроса сохраняет условия и порядок правил; тест не отправляет их; снимок замечает изменения', () => {
  const form = { is_test: false, blocks: blocks(), title: 'Опрос', take_by_blocks: true }
  assert.deepEqual(formSavePayload(form).blocks, form.blocks.map(block => ({ ...block, title: null })))
  const before = formSnapshot(form)
  form.blocks[1].questions[0].finish_rules.reverse()
  assert.notEqual(formSnapshot(form), before)
  form.blocks[1].questions[0].finish_rules.reverse()
  assert.equal(formSnapshot(form), before)
  form.is_test = true
  const payload = formSavePayload(form)
  for (const block of payload.blocks) {
    assert.equal('condition' in block, false)
    for (const question of block.questions) {
      assert.equal('condition' in question, false)
      assert.equal('finish_rules' in question, false)
    }
  }
})
