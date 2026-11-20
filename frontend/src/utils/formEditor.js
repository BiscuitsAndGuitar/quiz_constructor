export function newQuestion(isTest = false) {
  const question = { key: crypto.randomUUID(), text: '', type: 'single', is_answer_required: false, options: [] }
  if (isTest) Object.assign(question, { points: 1, allow_partial_scoring: false })
  return question
}

export function newOption(isTest = false) {
  const option = { key: crypto.randomUUID(), text: '' }
  if (isTest) option.is_correct = false
  return option
}

export function changeQuestionType(question, type) {
  if (question.type === type) return
  question.type = type
  if (type === 'text') question.options = []
  for (const option of question.options) {
    if ('is_correct' in option) option.is_correct = false
  }
  delete question.correct_text_answers
  if ('points' in question) {
    question.allow_partial_scoring = false
    if (type === 'text') question.correct_text_answers = []
  }
}

export function defaultGradingScale() {
  return [0, 50, 70, 85].map((min_percent, index) => ({ min_percent, grade: String(index + 2), message: null }))
}

export function sortGradingScale(scale) {
  return [...scale].sort((a, b) => a.min_percent - b.min_percent)
}

export function totalPoints(form) {
  return form.blocks.reduce((total, block) => total + block.questions.reduce((sum, question) =>
    sum + (Number.isInteger(question.points) ? question.points : 0), 0), 0)
}

export function prepareFormForEditor(form) {
  const result = structuredClone(form)
  if (result.is_test) {
    if (!result.grading_scale?.length) result.grading_scale = defaultGradingScale()
    for (const block of result.blocks) {
      for (const question of block.questions) question.points ??= 1
    }
  }
  return result
}

export function formSavePayload(form) {
  // Все полученные настройки сохраняются, включая пока скрытые в интерфейсе.
  const { id, is_test, is_published, public_code, ...editable } = form
  const payload = structuredClone(editable)
  if (payload.completion_message === '') payload.completion_message = null
  if (!payload.requires_login || payload.max_attempts === '') payload.max_attempts = null
  if (is_test) {
    if (payload.grading_scale) payload.grading_scale = sortGradingScale(payload.grading_scale)
    for (const block of payload.blocks) {
      for (const question of block.questions) {
        delete question.is_answer_required
        if (question.type !== 'text') delete question.correct_text_answers
        if (question.type !== 'multiple') question.allow_partial_scoring = false
      }
    }
  } else {
    for (const key of ['grading_scale', 'time_limit_minutes', 'shuffle_questions', 'show_correct_answers', 'show_results_by_block']) delete payload[key]
    for (const block of payload.blocks) {
      for (const question of block.questions) {
        for (const key of ['points', 'allow_partial_scoring', 'correct_text_answers']) delete question[key]
        for (const option of question.options) delete option.is_correct
      }
    }
  }
  return payload
}
