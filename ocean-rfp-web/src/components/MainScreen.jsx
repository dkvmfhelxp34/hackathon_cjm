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

export default function MainScreen({ onOpen, agencies, onAgency, onClearAgency }) {
  const [query, setQuery] = useState('')
  const list = filterByAgency(agencies).filter((p) => matches(p, query))

  return (
    <main>
      <p className="lead">
        분석된 제안요청서의 사업요약·핵심 용어·원문을 한 화면에서 탐색합니다. 발주처 필터와
        검색으로 원하는 사업을 빠르게 찾을 수 있습니다.
      </p>

      <KpiDeck list={list} />

      <div className="layout">
        <ProjectList
          list={list}
          onOpen={onOpen}
          agencies={agencies}
          onAgency={onAgency}
          onClearAgency={onClearAgency}
          query={query}
          setQuery={setQuery}
        />
        <LlmPanel count={list.length} />
      </div>
    </main>
  )
}
