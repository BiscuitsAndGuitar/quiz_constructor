export const normalizeText = value => (value || '').toLowerCase().trim().replace(/\s+/gu, ' ')
export const hasAnswer = answer => !!(answer?.option_ids?.length || normalizeText(answer?.text))

export function limitTextAnswer(value = '') {
  // Как maxlength: не более 1000 единиц UTF-16, без оборванной пары символа эмодзи.
  return value.slice(0, 1000).replace(/[\uD800-\uDBFF]$/u, '')
}

export function conditionMatches(condition, answers) {
  if (!condition) return true
  const results = condition.items.map(item => {
    const answer = answers[item.question_id]
    const chosen = !!answer?.option_ids?.includes(item.option_id)
    const text = normalizeText(answer?.text)
    const expected = normalizeText(item.text_answer)
    return { chosen, not_chosen: !chosen, equals: !!text && text === expected,
      contains: !!text && text.includes(expected), answered: hasAnswer(answer),
      not_answered: !hasAnswer(answer) }[item.operator]
  })
  return condition.match_all ? results.every(Boolean) : results.some(Boolean)
}

// При редактировании ответа правила завершения не применяем: они проверяются кнопкой.
export function visibleContent(form, answers, checkFinish = false, ruleQuestionIds = null) {
  const blocks = []
  const known = {}
  let rule = null
  let ruleQuestionId = null
  for (const block of form.blocks) {
    if (!form.is_test && !conditionMatches(block.condition, known)) continue
    const questions = []
    for (const question of block.questions) {
      if (!form.is_test && !conditionMatches(question.condition, known)) continue
      questions.push(question)
      if (question.type === 'info') continue
      known[question.id] = answers[question.id]
      if (checkFinish && !form.is_test && !rule && (!ruleQuestionIds || ruleQuestionIds.includes(question.id))) {
        rule = (question.finish_rules || []).find(item => conditionMatches(item.condition, known)) || null
        if (rule) ruleQuestionId = question.id
      }
      if (rule && !form.take_by_blocks) break
    }
    if (questions.length) blocks.push({ ...block, questions })
    if (rule) break
  }
  return { blocks, rule, ruleQuestionId }
}

export function attemptPages(form, blocks) {
  const numbered = new Map()
  const questions = new Map(blocks.flatMap(block => block.questions.map(q => [q.id, q])))
  const ordered = form.take_by_blocks ? blocks.flatMap(b => b.questions) :
    form.question_order.map(id => questions.get(id)).filter(Boolean)
  for (const q of ordered) if (q.type !== 'info') numbered.set(q.id, numbered.size + 1)
  if (form.take_by_blocks) return blocks.map(b => ({ key: `b${b.id}`, title: b.title,
    questions: b.questions, numbered }))
  const pages = []
  let info = []
  for (const question of ordered) {
    if (question.type === 'info') info.push(question)
    else {
      pages.push({ key: `q${question.id}`, questions: [...info, question], numbered })
      info = []
    }
  }
  // Последнее пояснение показываем над предыдущим вопросом, отдельный номер не нужен.
  if (info.length && pages.length) pages.at(-1).questions.splice(pages.at(-1).questions.length - 1, 0, ...info)
  else if (info.length) pages.push({ key: 'info', questions: info, numbered })
  return pages
}

export function pageIndex(pages, key, fallback = 0) {
  const found = pages.findIndex(page => page.key === key)
  return found >= 0 ? found : Math.max(0, Math.min(fallback, pages.length - 1))
}
export function missingRequired(form, questions, answers) {
  return form.is_test ? [] : questions.filter(q => q.type !== 'info' && q.is_answer_required && !hasAnswer(answers[q.id])).map(q => q.id)
}
export function finishAnswers(questions, answers) {
  return questions.filter(q => q.type !== 'info' && hasAnswer(answers[q.id])).map(q =>
    q.type === 'text' ? { question_id: q.id, text: limitTextAnswer(answers[q.id].text) } :
      { question_id: q.id, option_ids: [...answers[q.id].option_ids] })
}
export function remainingMilliseconds(duration, receivedAt, now) {
  return duration === null ? null : Math.max(0, duration - Math.max(0, now - receivedAt))
}
export function safeRedirect(value) {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//') &&
    !/[\\\u0000-\u0020]/u.test(value) ? value : null
}
