export function passwordError(password) {
  // Считаем символы Unicode, как len() в Python, а не пары UTF-16.
  if ([...password].length < 8) return 'Пароль должен быть не короче 8 символов'
  if (new TextEncoder().encode(password).length > 72) {
    return 'Пароль слишком длинный. Допустимо примерно до 36 русских букв или 72 латинских символов'
  }
  return ''
}
