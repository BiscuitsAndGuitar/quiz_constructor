import assert from 'node:assert/strict'
import test from 'node:test'
import { passwordError } from '../src/pages/password.js'

for (const password of ['abcdefgh', 'a'.repeat(72), 'я'.repeat(36), '😀'.repeat(18)]) {
  test(`Допустимый пароль: ${[...password].length} символов, ${new TextEncoder().encode(password).length} UTF-8`, () => {
    assert.equal(passwordError(password), '')
  })
}

for (const password of ['abcdefg', '😀'.repeat(7)]) {
  test(`Короткий пароль: ${JSON.stringify(password)}`, () => {
    assert.equal(passwordError(password), 'Пароль должен быть не короче 8 символов')
  })
}

for (const password of ['a'.repeat(73), 'я'.repeat(37), '😀'.repeat(19), '😀'.repeat(18) + 'a']) {
  test(`Превышен предел UTF-8: ${new TextEncoder().encode(password).length}`, () => {
    assert.equal(passwordError(password), 'Пароль слишком длинный. Допустимо примерно до 36 русских букв или 72 латинских символов')
  })
}
