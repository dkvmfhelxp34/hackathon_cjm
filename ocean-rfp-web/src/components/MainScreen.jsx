import { useState } from 'react'
import KpiDeck from './KpiDeck.jsx'
import ProjectList from './ProjectList.jsx'
import LlmPanel from './LlmPanel.jsx'
import { filterByAgency } from '../data/projects.js'

// 검색 매칭: 프로젝트명 / 발주처 / 태그 / 용어
function matches(p, q) {
  if (!q.trim()) return true
  const s = q.trim().toLowerCase()
  return (
    p.name.toLowerCase().includes(s) ||
    p.agency.toLowerCase().includes(s) ||
    p.tags.some((t) => t.toLowerCase().includes(s)) ||
    p.terms.some((t) => t.term.toLowerCase().includes(s))
  )
}

const pad = (n) => String(n).padStart(2, '0')

export default function MainScreen({ onOpen, agency, onClearAgency, now }) {
  const [query, setQuery] = useState('')
  const list = filterByAgency(agency).filter((p) => matches(p, query))

  const hh = pad(now.getHours())
  const mm = pad(now.getMinutes())
  const date = `${now.getFullYear()}.${pad(now.getMonth() + 1)}.${pad(now.getDate())}`
  const h = now.getHours()
  const label = h < 6 ? 'DAWN' : h < 12 ? 'MORNING' : h < 18 ? 'AFTERNOON' : 'EVENING'

  return (
    <main>
      <div className="head">
        <div>
          <div className="eyebrow">예보사업부 · Forecasting Division</div>
          <h1>예보사업부 RFP <em>통합 대시보드</em></h1>
          <p>
            분석된 제안요청서의 사업요약·핵심 용어·원문을 한 화면에서 탐색합니다. 발주처
            필터와 검색으로 원하는 사업을 빠르게 찾을 수 있습니다.
          </p>
        </div>
        <div className="clock">
          <div className="t mono">{hh}:{mm}</div>
          <div className="d mono">{label} · {date}</div>
        </div>
      </div>

      <KpiDeck list={list} />

      <div className="layout">
        <ProjectList
          list={list}
          onOpen={onOpen}
          agency={agency}
          onClearAgency={onClearAgency}
          query={query}
          setQuery={setQuery}
        />
        <LlmPanel />
      </div>
    </main>
  )
}
