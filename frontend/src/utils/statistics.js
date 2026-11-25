export function formContext(form) {
  const questionBlocks = {}
  let hasRules = false
  for (const [index, block] of (form?.blocks ?? []).entries()) {
    for (const question of block.questions) {
      questionBlocks[Number(question.key.slice(1))] = index + 1
      if (question.finish_rules?.length) hasRules = true
    }
  }
  return { questionBlocks, hasRules: form ? !form.is_test && hasRules : true }
}

export function answerBlockTitle(answer, questionBlocks) {
  if (answer.block_title) return answer.block_title
  const number = questionBlocks[answer.question_id]
  return number ? `${number} (без названия)` : 'без названия'
}

function chart(labels, values, label, colors = '#426b96') {
  return { labels, datasets: [{ label, data: values, backgroundColor: colors, borderColor: '#426b96' }] }
}
export function gradesChart(rows = []) {
  return chart(rows.map(row => row.grade), rows.map(row => row.count), 'Прохождений')
}
export function daysChart(rows = []) {
  return chart(rows.map(row => row.date), rows.map(row => row.count), 'Завершено')
}
export function blocksChart(rows = []) {
  return chart(rows.map((row, index) => row.title || `Блок ${index + 1}`), rows.map(row => row.avg_percent), 'Средний результат, %')
}
export function optionLabel(option) {
  return `${option.is_correct ? '✓ ' : ''}${option.text} — ${option.count} (${option.percent}%)`
}
export function optionsChart(rows = []) {
  return chart(rows.map(optionLabel), rows.map(row => row.count), 'Ответов', rows.map(row => row.is_correct ? '#287449' : '#426b96'))
}
export function sortedQuestions(questions, difficult = false) {
  const rows = questions.filter(question => question.type !== 'info').map((question, index) => ({ ...question, number: index + 1 }))
  return difficult ? rows.sort((a, b) => a.correct_percent - b.correct_percent || a.number - b.number) : rows
}
export function shortText(text, limit = 100) {
  const letters = [...text]
  return letters.length > limit ? `${letters.slice(0, limit).join('')}…` : text
}
export function duration(seconds) {
  if (seconds == null) return '—'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor(seconds % 3600 / 60)
  return `${hours ? `${hours} ч ` : ''}${hours || minutes ? `${minutes} мин ` : ''}${seconds % 60} с`
}
export function localDate(value) {
  if (!value) return '—'
  // Сервер хранит UTC, но timestamp может прийти без обозначения часового пояса.
  return new Date(/Z$|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`).toLocaleString('ru-RU')
}
export function attemptRow(attempt, isTest) {
  return {
    name: attempt.user?.name ?? 'Аноним',
    date: localDate(attempt.started_at),
    status: !attempt.is_finished ? 'не завершена' : !isTest && attempt.finished_early ? 'досрочно' : 'завершена',
    result: isTest && attempt.is_finished ? `${attempt.score}/${attempt.max_score}${attempt.grade == null ? '' : `, оценка ${attempt.grade}`}` : '',
  }
}

export function attemptDetails(data, questionBlocks, isTest) {
  const row = attemptRow(data.attempt, isTest)
  return {
    title: `${row.name}, ${row.date}`,
    answers: data.answers.map(answer => ({ ...answer, blockTitle: answerBlockTitle(answer, questionBlocks) })),
  }
}
