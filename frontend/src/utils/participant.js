export function parseFormCode(value) {
  const text = value.trim()
  const marker = text.indexOf('/f/')
  if (marker < 0) return text
  const code = text.slice(marker + 3).split(/[?#/]/u)[0]
  try { return decodeURIComponent(code).trim() } catch { return code.trim() }
}

export function historyResult(attempt) {
  if (!attempt.is_finished) return ''
  if (!attempt.form.is_test) return 'пройден'
  return `${attempt.score}/${attempt.max_score}${attempt.grade === null ? '' : `, оценка ${attempt.grade}`}`
}
export function filterAttempts(attempts, type) {
  return attempts.filter(item => type === 'all' || item.form.is_test === (type === 'test'))
}
export function completionDate(value) {
  if (!value) return null
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)
}

export function previewForm(editor) {
  // Снимок не связан с реактивными объектами редактора: ответы его не меняют.
  const source = JSON.parse(JSON.stringify(editor))
  const questionIds = new Map(), optionIds = new Map()
  let nextQuestion = 1, nextOption = 1, nextRule = 1
  for (const block of source.blocks) {
    for (const question of block.questions) {
      questionIds.set(question.key, nextQuestion++)
      for (const option of question.options || []) optionIds.set(option.key, nextOption++)
    }
  }
  function condition(value) {
    if (!value) return null
    return { match_all: value.match_all, items: (value.items || []).map(item => ({
      question_id: questionIds.get(item.question) ?? 0, operator: item.operator,
      ...(item.option ? { option_id: optionIds.get(item.option) ?? 0 } : {}),
      ...(item.text_answer !== undefined ? { text_answer: item.text_answer } : {}),
    })) }
  }
  const blocks = source.blocks.map((block, index) => ({
    id: index + 1, title: block.title || null, condition: condition(block.condition),
    questions: block.questions.map(question => ({
      id: questionIds.get(question.key), text: question.text || '', type: question.type,
      is_answer_required: !!question.is_answer_required,
      options: (question.options || []).map(option => ({ id: optionIds.get(option.key), text: option.text || '' })),
      ...(question.image ? { image: question.image } : {}), condition: condition(question.condition),
      finish_rules: (question.finish_rules || []).map(rule => ({ id: nextRule++, condition: condition(rule.condition), message: rule.message })),
    })),
  }))
  return { id: source.id, title: source.title || '', is_test: !!source.is_test,
    take_by_blocks: !!source.take_by_blocks, allow_free_navigation: !!source.allow_free_navigation,
    completion_message: source.completion_message, blocks,
    question_order: blocks.flatMap(block => block.questions.map(question => question.id)) }
}
