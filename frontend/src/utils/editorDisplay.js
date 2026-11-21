export function toggleCollapsed(collapsed, key) {
  const next = new Set(collapsed)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  return next
}

export function collapseAll(blocks) {
  return new Set(blocks.flatMap(block => [block.key, ...block.questions.map(question => question.key)]))
}

export function messageLines(detail) {
  if (Array.isArray(detail)) return detail.flatMap(messageLines)
  if (typeof detail === 'string') return detail.split('\n').filter(line => line.trim())
  if (detail && typeof detail.msg === 'string') return messageLines(detail.msg)
  return ['Не удалось выполнить запрос']
}

export function expandForErrors(collapsed, detail) {
  // Сервер иногда нумерует вопросы внутри блока, иногда по всей форме.
  // Не угадываем место: при упоминании блока/вопроса раскрываем все карточки.
  const lines = messageLines(detail)
  const next = lines.some(line => /(?:вопрос|блок)\S*\s+\d+/iu.test(line)) ? new Set() : new Set(collapsed)
  for (const line of lines) {
    if (/шкал|оценк|границ|min_percent|grading_scale|grade/iu.test(line)) next.delete(gradingSection)
    if (/настрой|доступ|попыт|врем|минут|завершени|описани|requires_login|max_attempts|time_limit|completion_message|description|take_by_blocks|navigation|shuffle|show_/iu.test(line)) next.delete(settingsSection)
    // Общее сообщение о поле message не различает оценку, правило и настройки.
    if (/сообщени/iu.test(line)) { next.delete(settingsSection); next.delete(gradingSection) }
  }
  return next
}

export function remapCollapsed(collapsed, before, after) {
  const next = new Set()
  for (const section of [settingsSection, gradingSection]) {
    if (collapsed.has(section)) next.add(section)
  }
  // PUT заменяет ключи, но сохраняет порядок отправленных блоков и вопросов.
  before.forEach((block, index) => {
    const saved = after[index]
    if (!saved) return
    if (collapsed.has(block.key)) next.add(saved.key)
    block.questions.forEach((question, questionIndex) => {
      if (collapsed.has(question.key) && saved.questions[questionIndex]) next.add(saved.questions[questionIndex].key)
    })
  })
  return next
}

export function questionSummary(question) {
  const text = question.text.trim().replace(/\s+/g, ' ') || 'Без текста'
  return text.length > 90 ? `${text.slice(0, 90)}…` : text
}

export const questionTypeNames = { single: 'Один ответ', multiple: 'Несколько ответов', text: 'Текстовый ответ' }
// Символы не пересекаются с временными ключами блоков и вопросов.
export const settingsSection = Symbol('settings')
export const gradingSection = Symbol('grading')

export function collapseAllSections(form) {
  const next = collapseAll(form.blocks)
  next.add(settingsSection)
  if (form.is_test) next.add(gradingSection)
  return next
}

export function settingsSummary(form) {
  const parts = [`Доступ: ${form.requires_login ? 'только авторизованным' : 'всем'}`,
    `Проходить по блокам: ${form.take_by_blocks ? 'да' : 'нет'}`]
  if (form.is_test && form.time_limit_minutes != null && form.time_limit_minutes !== '') {
    parts.push(`Ограничение времени: ${form.time_limit_minutes} мин`)
  }
  return parts.join(' · ')
}

