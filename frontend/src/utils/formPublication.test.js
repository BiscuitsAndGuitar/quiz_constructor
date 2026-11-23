import test from 'node:test'
import assert from 'node:assert/strict'
import { participantLink, isReadOnly, copyParticipantLink } from './formPublication.js'
import { prepareFormForEditor } from './formEditor.js'

test('Ссылка ведёт на f/code на текущем сайте', () => {
  assert.equal(participantLink('http://localhost:5173', 'abc123'), 'http://localhost:5173/f/abc123')
  assert.equal(participantLink('https://example.com/', 'a/b'), 'https://example.com/f/a%2Fb')
})

test('Только опубликованная форма доступна только для чтения', () => {
  assert.equal(isReadOnly(null), false)
  assert.equal(isReadOnly({ is_published: false }), false)
  assert.equal(isReadOnly({ is_published: true }), true)
})

test('Просмотр не подставляет стандартную шкалу и баллы в опубликованную форму', () => {
  const form = { is_test: true, is_published: true, grading_scale: [], blocks: [{ questions: [{ points: null }] }] }
  assert.deepEqual(prepareFormForEditor(form), form)
})

test('Буфер обмена: успешная запись и возврат к ручному копированию', async () => {
  let copied
  assert.equal(await copyParticipantLink('https://example.com/f/a', { writeText: async text => { copied = text } }), true)
  assert.equal(copied, 'https://example.com/f/a')
  assert.equal(await copyParticipantLink('link', undefined), false)
  assert.equal(await copyParticipantLink('link', { writeText: async () => { throw new Error('denied') } }), false)
})
