export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand ${compact ? 'brand--compact' : ''}`} aria-label="至简">
      <span className="brand__name">至简</span>
      <span className="brand__seal" aria-hidden="true">简</span>
      {!compact && <span className="brand__tagline">本地优先 · 安心处理</span>}
    </div>
  )
}
