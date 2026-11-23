export function participantLink(origin, publicCode) {
  return `${origin.replace(/\/$/, '')}/f/${encodeURIComponent(publicCode)}`
}

export function isReadOnly(form) {
  return form?.is_published === true
}

export async function copyParticipantLink(link, clipboard) {
  try {
    if (!clipboard?.writeText) return false
    await clipboard.writeText(link)
    return true
  } catch {
    return false
  }
}
