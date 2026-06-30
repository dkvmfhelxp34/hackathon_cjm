import { useState } from 'react'
import { projects, agencyColor, AGENCIES } from '../data/projects.js'
import { SearchIcon } from './icons.jsx'

export default function ProjectList({ list, onOpen, agencies = [], onAgency, onClearAgency, onSearch }) {
  const isOn = (a) => agencies.some((x) => x.label === a.label)
  // 입력값(text)과 실제 적용 검색어 분리 — 제출 시에만 필터 적용
  const [text, setText] = useState('')
  const submit = (e) => {
    if (e) e.preventDefault()
    onSearch(text.trim())
  }
  const clear = () => {
    setText('')
    onSearch('')
  }

  return (
    <div className="glass">
      <div className="panelhead">
        <h2>
          <span className="k">› </span>프로젝트 목록
          <span className="cnt">{list.length}건</span>
        </h2>
        <form className="search" onSubmit={submit}>
          <button type="submit" className="search-go" title="검색">
            <SearchIcon />
          </button>
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="프로젝트 / 발주처 / 용어 (검색 실행)"
          />
          {text && (
            <button type="button" className="search-clear" onClick={clear} title="검색어 지우기">✕</button>
          )}
        </form>
      </div>

      <div className="filterbar">
        <span className="filterbar-label">발주처</span>
        {AGENCIES.map((a) => (
          <button
            key={a.label}
            className={`agency-btn${isOn(a) ? ' on' : ''}`}
            onClick={() => onAgency(a)}
            title={`${a.label} 사업 필터 (다중 선택 가능)`}
            style={isOn(a) ? { background: a.color, borderColor: a.color, color: '#fff' } : { color: a.color }}
          >
            <span className="agency-dot" style={{ background: a.color }} />
            {a.label}
          </button>
        ))}
        {agencies.length > 0 && (
          <button className="clearfilter" onClick={onClearAgency} title="기관 필터 해제">✕ 해제</button>
        )}
      </div>

      {list.length === 0 ? (
        <div className="empty">검색 결과가 없습니다.</div>
      ) : (
        list.map((p) => {
          const n = projects.findIndex((x) => x.id === p.id) + 1
          const c = agencyColor(p.agency)
          return (
            <button
              key={p.id}
              className="row"
              onClick={() => onOpen(p.id)}
              style={{ boxShadow: `inset 4px 0 0 ${c}` }}
            >
              <span className="idx mono" style={{ color: c }}>{String(n).padStart(2, '0')}</span>
              <span>
                <span className="pname">{p.name}</span>
                <span className="tagrow">
                  {p.tags.map((t) => (
                    <span key={t} className="tg">{t}</span>
                  ))}
                </span>
              </span>
              <span className="bud">{p.budgetShort}</span>
              <span className="ag">
                <span className="ag-dot" style={{ background: c }} />
                {p.agency}
              </span>
              <span className="go">→</span>
            </button>
          )
        })
      )}
    </div>
  )
}
