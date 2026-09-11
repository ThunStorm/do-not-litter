export function videoTimestampUrl(canonicalUrl: string, startMs: number | null) {
  if (startMs == null) return canonicalUrl
  try {
    const target = new URL(canonicalUrl)
    target.searchParams.set('t', String(Math.max(0, Math.floor(startMs / 1000))))
    return target.toString()
  } catch {
    return canonicalUrl
  }
}
