export const operatorNames = {
  chosen: 'Выбран вариант', not_chosen: 'Не выбран вариант', equals: 'Ответ равен',
  contains: 'Ответ содержит', answered: 'Есть ответ', not_answered: 'Нет ответа',
}

export function operatorsFor(type) {
  if (type === 'info') return []
  if (type === 'text') return ['equals', 'contains', 'answered', 'not_answered']
  if (['single', 'multiple'].includes(type)) return ['chosen', 'not_chosen', 'answered', 'not_answered']
  return []
}

export function indexedQuestions(blocks) {
  let number = 0
  return blocks.flatMap((block, blockIndex) => block.questions.map((question, questionIndex) => ({
    question, blockIndex, questionIndex, number: ++number,
  })))
}

export function availableQuestions(blocks, blockIndex, questionIndex = -1, includeSelf = false) {
  return indexedQuestions(blocks).filter(item => item.question.type !== 'info' && (
    item.blockIndex < blockIndex || (item.blockIndex === blockIndex && (
      item.questionIndex < questionIndex || (includeSelf && item.questionIndex === questionIndex)))))
}

export function conditionOwners(blocks) {
  const result = []
  let number = 0
  blocks.forEach((block, blockIndex) => {
    result.push({ condition: block.condition, blockIndex, questionIndex: -1,
      label: `Условие блока ${blockIndex + 1}` })
    block.questions.forEach((question, questionIndex) => {
      number++
      result.push({ condition: question.condition, blockIndex, questionIndex, questionKey: question.key,
        label: `Условие вопроса ${number}` })
      ;(question.finish_rules || []).forEach((rule, ruleIndex) => result.push({
        condition: rule.condition, blockIndex, questionIndex, questionKey: question.key, includeSelf: true,
        label: `Правило ${ruleIndex + 1} вопроса ${number}`,
      }))
    })
  })
  return result
}

export function referenceErrors(blocks) {
  const errors = []
  const questions = indexedQuestions(blocks)
  for (const owner of conditionOwners(blocks)) {
    const allowed = availableQuestions(blocks, owner.blockIndex, owner.questionIndex, owner.includeSelf)
    if (owner.includeSelf && blocks[owner.blockIndex].questions[owner.questionIndex].type === 'info') {
      errors.push(`${owner.label}: у «Текста без вопроса» не может быть правил завершения`)
    }
    for (const item of owner.condition?.items || []) {
      const source = questions.find(entry => entry.question.key === item.question)
      // Незавершённая строка редактора не блокирует действия; сервер проверит её при сохранении.
      if (!item.question) continue
      const label = source ? `вопрос ${source.number}` : `вопрос «${item.question}»`
      if (!allowed.some(entry => entry.question.key === item.question)) {
        errors.push(`${owner.label} ссылается на ${label}: он должен быть ${owner.includeSelf ? 'не позже вопроса правила' : 'раньше'} и не типа «Текст без вопроса»`)
      } else if (!operatorsFor(source.question.type).includes(item.operator)) {
        errors.push(`${owner.label} ссылается на ${label}: оператор не подходит к типу вопроса`)
      } else if (['chosen', 'not_chosen'].includes(item.operator) && item.option &&
        !source.question.options.some(option => option.key === item.option)) {
        errors.push(`${owner.label} ссылается на удалённый вариант (${label})`)
      }
    }
  }
  return [...new Set(errors)]
}

export function deletionReferences(blocks, questionKeys, optionKey = null, removedBlockIndex = null) {
  const places = []
  for (const owner of conditionOwners(blocks)) {
    // Собственные условия удаляемого вопроса или блока исчезают вместе с владельцем.
    if (removedBlockIndex !== null && owner.blockIndex === removedBlockIndex) continue
    if (optionKey === null && questionKeys.includes(owner.questionKey)) continue
    if ((owner.condition?.items || []).some(item => optionKey !== null
      ? item.option === optionKey : questionKeys.includes(item.question))) places.push(owner.label)
  }
  return [...new Set(places)]
}

export function typeChangeErrors(blocks, questionKey, type) {
  const copy = JSON.parse(JSON.stringify(blocks))
  const question = copy.flatMap(block => block.questions).find(item => item.key === questionKey)
  question.type = type
  if (type === 'text' || type === 'info') question.options = []
  return referenceErrors(copy)
}
