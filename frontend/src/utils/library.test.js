import test from 'node:test'
import assert from 'node:assert/strict'
import { insertLibraryBlock, libraryParams, libraryPayload, normalizeTags } from './library.js'
import { formSavePayload, formSnapshot, hasFormChanges, questionNumbers } from './formEditor.js'
import { referenceErrors } from './conditions.js'

function example() {
  return { key: 'b1', title: 'Блок', condition: null, questions: [
    { key: 'q1', type: 'single', text: 'Выберите', options: [{ key: 'o1', text: 'Да' }], image: { id: 7, url: '/uploads/image.png' } },
    { key: 'q2', type: 'text', text: 'Почему?', options: [], condition: { match_all: true, items: [{ question: 'q1', operator: 'chosen', option: 'o1' }] } },
    { key: 'q3', type: 'info', text: 'Пояснение', options: [] },
  ] }
}

test('Вставка: уникальные ключи, условия, info и картинка, без изменения источника', () => {
  const source = example(), original = structuredClone(source)
  const form = { is_test: false, blocks: [example()] }
  const snapshot = formSnapshot(form)
  const generated = ['b1', 'q1', 'o1', 'new-block', 'new-q1', 'new-o1', 'new-q2', 'new-info'][Symbol.iterator]()
  const inserted = insertLibraryBlock(source, form.blocks, () => generated.next().value)
  assert.equal(inserted.key, 'new-block')
  assert.deepEqual(inserted.questions.map(q => q.key), ['new-q1', 'new-q2', 'new-info'])
  assert.deepEqual(inserted.questions[1].condition.items[0], { question: 'new-q1', operator: 'chosen', option: 'new-o1' })
  assert.deepEqual(inserted.questions[0].image, source.questions[0].image)
  assert.equal(inserted.questions[2].type, 'info')
  assert.deepEqual(source, original)
  form.blocks.push(inserted)
  assert.equal(hasFormChanges(form, snapshot), true)
  assert.deepEqual(questionNumbers(form.blocks), [[1, 2, null], [3, 4, null]])
  assert.deepEqual(referenceErrors(form.blocks), [])
  const saved = formSavePayload(form)
  assert.equal(saved.blocks[1].questions[0].image_id, 7)
  assert.equal(saved.blocks[1].questions[1].condition.items[0].question, 'new-q1')
  inserted.questions[0].image.url = '/changed'
  assert.equal(source.questions[0].image.url, '/uploads/image.png')
})

test('Повторная вставка и блок без условий получают независимые ключи', () => {
  const block = { key: 'b1', title: null, questions: [{ key: 'q1', type: 'info', text: 'Текст', options: [], image: null }] }
  const first = insertLibraryBlock(block, [])
  const second = insertLibraryBlock(block, [first])
  assert.equal(new Set([first.key, first.questions[0].key, second.key, second.questions[0].key]).size, 4)
  assert.equal(second.questions[0].image, null)
  const invalid = example()
  invalid.questions[1].condition.items[0].question = 'absent'
  assert.throws(() => insertLibraryBlock(invalid, []), /отсутствующий вопрос/)
})

test('Теги: регистр, пробелы, пустые, дубли и границы длины и количества', () => {
  assert.deepEqual(normalizeTags(['  ГеОметрия ', '', 'геометрия', 'два\t слова', 'два  слова']), ['геометрия', 'два слова'])
  assert.deepEqual(normalizeTags(['😀'.repeat(30)]), ['😀'.repeat(30)])
  assert.throws(() => normalizeTags(['а'.repeat(31)]), /Тег должен быть не длиннее 30 символов/)
  const ten = Array.from({ length: 10 }, (_, index) => String(index))
  assert.deepEqual(normalizeTags([...ten, ...ten, '']), ten)
  assert.throws(() => normalizeTags([...ten, 'ещё']), /Можно указать не больше 10 тегов/)
})

test('POST библиотеки: текущие данные, image_id и is_test, без полей интерфейса', () => {
  for (const isTest of [false, true]) {
    const block = example()
    block.collapsed = true
    block.questions[0].uploading = true
    block.questions[0].options[0].editing = true
    block.questions[0].points = 2
    block.questions[0].options[0].is_correct = true
    block.questions[0].finish_rules = [{ key: 'r1', condition: { match_all: true, items: [{ question: 'q1', operator: 'answered' }] }, message: 'Конец' }]
    const body = libraryPayload(block, isTest, { title: ' Новое ', description: ' ', tags: [' ТЕГ ', 'тег'], is_public: true })
    assert.equal(body.title, 'Новое')
    assert.equal(body.description, null)
    assert.equal(body.is_test, isTest)
    assert.deepEqual(body.tags, ['тег'])
    assert.equal(body.block.questions[0].image_id, 7)
    assert.equal(body.block.questions[0].image, undefined)
    assert.equal(body.block.collapsed, undefined)
    assert.equal(body.block.questions[0].uploading, undefined)
    assert.equal(body.block.questions[0].options[0].editing, undefined)
    assert.equal('points' in body.block.questions[0], isTest)
    assert.equal('is_correct' in body.block.questions[0].options[0], isTest)
    assert.equal('condition' in body.block.questions[1], !isTest)
    assert.equal('finish_rules' in body.block.questions[0], !isTest)
    assert.equal(body.block.questions[2].options, undefined)
    assert.equal(block.questions[0].image.id, 7)
  }
})

test('Параметры списка: пустые фильтры отсутствуют, тег нормализован, тип и offset сохранены', () => {
  assert.deepEqual(libraryParams({ query: ' ', tag: '', scope: 'all', type: 'all' }), { limit: 20, offset: 0 })
  assert.deepEqual(libraryParams({ query: ' Поиск ', tag: ' ДВА  СЛОВА ', scope: 'public', type: 'test' }, 40),
    { limit: 20, offset: 40, query: 'Поиск', tag: 'два слова', scope: 'public', is_test: true })
  assert.equal(libraryParams({ type: 'test' }, 0, false).is_test, false)
  assert.equal(libraryParams({ type: 'survey' }).is_test, false)
  assert.equal(libraryParams({ scope: 'mine' }).scope, 'mine')
})
