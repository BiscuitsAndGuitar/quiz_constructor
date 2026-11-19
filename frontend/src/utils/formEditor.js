export function newQuestion() {
  return { key: crypto.randomUUID(), text: '', type: 'single', is_answer_required: false, options: [] }
}

export function newOption() {
  return { key: crypto.randomUUID(), text: '' }
}

export function changeQuestionType(question, type) {
  question.type = type
  if (type === 'text') question.options = []
}

export function formSavePayload(form) {
  // Все полученные настройки сохраняются, включая пока скрытые в интерфейсе.
  const { id, is_test, is_published, public_code, ...editable } = form
  return structuredClone(editable)
}
