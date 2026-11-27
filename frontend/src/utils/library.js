import { formSavePayload } from './formEditor.js'

export function normalizeTags(tags) {
  const cleaned = [...new Set(tags.map(tag => tag.trim().replace(/\s+/gu, ' ').toLowerCase()).filter(Boolean))]
  if (cleaned.some(tag => [...tag].length > 30)) throw new Error('Тег должен быть не длиннее 30 символов')
  if (cleaned.length > 10) throw new Error('Можно указать не больше 10 тегов')
  return cleaned
}

export function libraryParams(filters, offset = 0, fixedType = null) {
  const params = { limit: 20, offset }
  if (filters.query?.trim()) params.query = filters.query.trim()
  if (filters.tag?.trim()) params.tag = normalizeTags([filters.tag])[0]
  if (filters.scope && filters.scope !== 'all') params.scope = filters.scope
  if (fixedType !== null) params.is_test = fixedType
  else if (filters.type && filters.type !== 'all') params.is_test = filters.type === 'test'
  return params
}

function pick(value, keys) {
  return Object.fromEntries(keys.filter(key => value[key] !== undefined).map(key => [key, value[key]]))
}

export function libraryPayload(block, isTest, metadata) {
  // Передаём только поля контракта: состояние сворачивания и прочие поля UI не нужны.
  const clean = pick(block, ['key', 'title', 'condition'])
  clean.questions = block.questions.map(question => ({
    ...pick(question, ['key', 'text', 'type', 'image', 'points', 'allow_partial_scoring', 'correct_text_answers', 'is_answer_required', 'condition', 'finish_rules']),
    options: (question.options || []).map(option => pick(option, ['key', 'text', 'is_correct'])),
  }))
  const prepared = formSavePayload({ is_test: isTest, blocks: [clean] }).blocks[0]
  return { title: metadata.title.trim(), description: metadata.description?.trim() || null,
    is_public: !!metadata.is_public, tags: normalizeTags(metadata.tags), is_test: isTest, block: prepared }
}

export function insertLibraryBlock(block, existingBlocks, makeKey = () => crypto.randomUUID()) {
  const result = JSON.parse(JSON.stringify(block))
  const used = new Set()
  function collect(item) {
    used.add(item.key)
    for (const question of item.questions) {
      used.add(question.key)
      for (const option of question.options || []) used.add(option.key)
      for (const rule of question.finish_rules || []) used.add(rule.key)
    }
  }
  existingBlocks.forEach(collect)
  collect(block)
  function fresh() {
    let key
    do { key = makeKey() } while (used.has(key))
    used.add(key)
    return key
  }
  const keys = new Map()
  result.key = fresh()
  for (const question of result.questions) {
    keys.set(question.key, fresh())
    question.key = keys.get(question.key)
    for (const option of question.options || []) {
      keys.set(option.key, fresh())
      option.key = keys.get(option.key)
    }
    for (const rule of question.finish_rules || []) rule.key = fresh()
  }
  function remap(condition) {
    for (const item of condition?.items || []) {
      if (!keys.has(item.question) || (item.option && !keys.has(item.option))) throw new Error('В блоке найдена ссылка на отсутствующий вопрос или вариант')
      item.question = keys.get(item.question)
      if (item.option) item.option = keys.get(item.option)
    }
  }
  remap(result.condition)
  for (const question of result.questions) {
    remap(question.condition)
    for (const rule of question.finish_rules || []) remap(rule.condition)
  }
  return result
}
