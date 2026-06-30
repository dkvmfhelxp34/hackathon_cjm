import { sumBudgetEok } from '../data/projects.js'

// 필터링된 목록(list)에 연동되어 실시간 집계
export default function KpiDeck({ list }) {
  const agencies = new Set(list.map((p) => p.agency)).size
  const terms = list.reduce((n, p) => n + p.terms.length, 0)
  const items = [
    { lab: 'Analyzed', v: list.length, unit: ' 사업', hi: true },
    { lab: 'Total Budget', v: sumBudgetEok(list) },
    { lab: 'Agencies', v: agencies, unit: ' 기관' },
    { lab: 'Key Terms', v: terms, unit: ' 용어' },
  ]
  return (
    <div className="deck">
      {items.map((it) => (
        <div key={it.lab} className={`glass kpi${it.hi ? ' hi' : ''}`}>
          <div className="lab">{it.lab}</div>
          <div className="v">
            {it.v}
            {it.unit && <small>{it.unit}</small>}
          </div>
        </div>
      ))}
    </div>
  )
}
