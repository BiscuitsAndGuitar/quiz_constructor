import test from 'node:test'
import assert from 'node:assert/strict'
import { imageFileError, imageUploadError, imageUrl, maxImageSize } from './images.js'
import { newQuestion, changeQuestionType, questionNumbers, formSavePayload, formSnapshot, hasFormChanges, prepareFormForEditor } from './formEditor.js'
import { previewForm } from './participant.js'
import { attemptPages, finishAnswers, missingRequired } from './attempt.js'

test('Точные тексты ошибок картинки одинаковы для проверки в браузере и ответа сервера', () => {
  const type = 'Допустимы только картинки форматов JPEG, PNG, GIF и WebP'
  const size = 'Файл слишком большой. Максимальный размер картинки: 5 МБ'
  assert.equal(imageFileError({ type: 'text/plain', size: 1 }), type)
  assert.equal(imageUploadError({ status: 422, message: 'Старый текст' }), type)
  assert.equal(imageFileError({ type: 'image/png', size: maxImageSize + 1 }), size)
  assert.equal(imageUploadError({ status: 413, message: 'Старый текст' }), size)
  assert.equal(imageUploadError({ status: 401, message: 'Войдите' }), 'Войдите')
  assert.equal(imageUploadError(new Error('Нет сети')), 'Нет сети')
})

test('Картинки: допустимые типы и точный предел размера', () => {
  for (const type of ['image/jpeg', 'image/png', 'image/gif', 'image/webp']) {
    assert.equal(imageFileError({ type, size: maxImageSize }), '')
    assert.match(imageFileError({ type, size: maxImageSize + 1 }), /5 МБ/)
  }
  for (const type of ['text/plain', 'image/svg+xml', '']) assert.match(imageFileError({ type, size: 1 }), /JPEG/)
  assert.equal(imageUrl('/uploads/a.png', 'http://localhost:8000/'), 'http://localhost:8000/uploads/a.png')
})

test('Редактор: info не нумеруется, сохраняет картинку и условие, не отправляет лишние поля', () => {
  for (const isTest of [false, true]) {
    const question = newQuestion(isTest)
    question.image = { id: 5, url: '/uploads/a.png' }
    question.text = 'Пояснение'
    question.condition = { match_all: true, items: [] }
    question.options.push({ key: 'o', text: 'Ответ', is_correct: true })
    changeQuestionType(question, 'info', isTest)
    const form = { is_test: isTest, blocks: [{ questions: [question, newQuestion(isTest)] }] }
    assert.deepEqual(questionNumbers(form.blocks), [[null, 1]])
    const payload = formSavePayload(form).blocks[0].questions[0]
    assert.equal(payload.image_id, 5)
    for (const key of ['image', 'options', 'points', 'allow_partial_scoring', 'correct_text_answers', 'is_answer_required', 'finish_rules']) assert.equal(key in payload, false)
    assert.equal('condition' in payload, !isTest)
    assert.equal(prepareFormForEditor(form).blocks[0].questions[0].points, undefined)
    const snapshot = formSnapshot(form)
    question.image = null
    assert.equal(hasFormChanges(form, snapshot), true)
    assert.equal(formSavePayload(form).blocks[0].questions[0].image_id, null)
    changeQuestionType(question, 'text', isTest)
    assert.equal(question.text, 'Пояснение')
    if (isTest) { assert.equal(question.points, 1); assert.deepEqual(question.correct_text_answers, []) }
  }
})

test('Info и картинка в предпросмотре четырёх режимов: пояснения над вопросом, без ответа и номера', () => {
  for (const take_by_blocks of [false, true]) for (const allow_free_navigation of [false, true]) {
    const form = previewForm({ is_test: false, take_by_blocks, allow_free_navigation, blocks: [{ questions: [
      { key: 'i1', type: 'info', text: 'До', image: { id: 1, url: '/uploads/a.png' } },
      { key: 'q', type: 'text', text: 'Вопрос' }, { key: 'i2', type: 'info', text: 'После' },
    ] }] })
    const pages = attemptPages(form, form.blocks)
    assert.equal(pages.length, 1)
    assert.equal(pages[0].numbered.size, 1)
    assert.deepEqual(pages[0].questions.map(q => q.text), take_by_blocks ? ['До', 'Вопрос', 'После'] : ['До', 'После', 'Вопрос'])
    assert.deepEqual(pages[0].questions[0].image, { id: 1, url: '/uploads/a.png' })
    assert.deepEqual(finishAnswers(pages[0].questions, { 1: { text: 'Не ответ' } }), [])
    assert.deepEqual(missingRequired(form, [{ id: 1, type: 'info', is_answer_required: true }], {}), [])
  }
})
