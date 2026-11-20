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
  // После перемещения внутри массивов могут оставаться Vue-прокси; тело API — обычный JSON.
  const payload = JSON.parse(JSON.stringify(editable))
  for (const block of payload.blocks) block.title = block.title?.trim() || null
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

export function newBlock() {
  return { key: crypto.randomUUID(), title: null, questions: [] }
}

export function addBlock(blocks, block) {
  return [...blocks, block]
}

export function removeBlock(blocks, index) {
  if (blocks.length <= 1 || index < 0 || index >= blocks.length) return blocks
  return blocks.filter((_, position) => position !== index)
}

export function moveBlock(blocks, index, direction) {
  const target = index + direction
  if (![1, -1].includes(direction) || !blocks[index] || target < 0 || target >= blocks.length) return blocks
  const result = [...blocks]
  ;[result[index], result[target]] = [result[target], result[index]]
  return result
}

export function canMoveQuestion(blocks, blockIndex, questionIndex, direction) {
  const block = blocks[blockIndex]
  if (!block?.questions[questionIndex]) return false
  if (direction === -1) return questionIndex > 0 || blockIndex > 0
  if (direction === 1) return questionIndex < block.questions.length - 1 || blockIndex < blocks.length - 1
  return false
}

export function moveQuestion(blocks, blockIndex, questionIndex, direction) {
  if (!canMoveQuestion(blocks, blockIndex, questionIndex, direction)) return blocks
  const result = blocks.map(block => ({ ...block, questions: [...block.questions] }))
  const questions = result[blockIndex].questions
  const target = questionIndex + direction
  const [question] = questions.splice(questionIndex, 1)
  if (target < 0) result[blockIndex - 1].questions.push(question)
  else if (target > questions.length) result[blockIndex + 1].questions.unshift(question)
  else questions.splice(target, 0, question)
  return result
}

export function questionNumbers(blocks) {
  let number = 0
  return blocks.map(block => block.questions.map(() => ++number))
}

export function formSnapshot(form) {
  // JSON-снимок читает также вложенные Vue-поля; служебные флаги хранятся вне формы.
  const state = formSavePayload(JSON.parse(JSON.stringify(form)))
  // Пустое поле в браузере — строка, хотя сервер может прислать null.
  state.description ??= ''
  for (const row of state.grading_scale || []) row.message ??= ''
  return JSON.stringify(state)
}

export function hasFormChanges(form, snapshot) {
  return formSnapshot(form) !== snapshot
}
