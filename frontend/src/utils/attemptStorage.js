const stateKey = id => `quiz_attempt_${id}`
const secretKey = id => `quiz_attempt_key_${id}`

export function createAttemptState(response, publicCode, receivedAt = Date.now()) {
  const { attempt, form } = response
  // Оба серверных времени в UTC; явный суффикс исключает влияние часового пояса браузера.
  const timestamp = value => Date.parse(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)
  const duration = attempt.deadline ? timestamp(attempt.deadline) - timestamp(attempt.started_at) : null
  return { id: attempt.id, form, publicCode, answers: {}, pageKey: null, position: 0, duration, receivedAt }
}
export function saveAttempt(storage, state) { storage.setItem(stateKey(state.id), JSON.stringify(state)) }
export function loadAttempt(storage, id) {
  try {
    const state = JSON.parse(storage.getItem(stateKey(id)))
    return state && String(state.id) === String(id) && Array.isArray(state.form?.blocks) &&
      Array.isArray(state.form?.question_order) && state.answers && Number.isFinite(state.receivedAt) &&
      (state.duration === null || Number.isFinite(state.duration)) ? state : null
  } catch { return null }
}
export function removeAttempt(storage, id) { storage.removeItem(stateKey(id)) }
export function saveAttemptKey(storage, id, key) { storage.setItem(secretKey(id), key) }
export function loadAttemptKey(storage, id) {
  try { return storage.getItem(secretKey(id)) || '' } catch { return '' }
}
