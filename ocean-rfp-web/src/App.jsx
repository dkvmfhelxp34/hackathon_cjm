import { useState, useEffect } from 'react'
import StatusBar from './components/StatusBar.jsx'
import MainScreen from './components/MainScreen.jsx'
import SummaryScreen from './components/SummaryScreen.jsx'
import OriginalScreen from './components/OriginalScreen.jsx'
import { AGENCIES } from './data/projects.js'

export default function App() {
  // 표출 전용 상태 기반 라우팅: main → summary → original
  // 초기 화면은 URL 쿼리(?screen=summary&id=coast)로도 지정 가능 (딥링크/공유)
  const [view, setView] = useState(() => {
    const q = new URLSearchParams(window.location.search)
    const screen = q.get('screen')
    const id = q.get('id')
    if ((screen === 'summary' || screen === 'original') && id) return { screen, id }
    return { screen: 'main', id: null }
  })

  // 상단바 기관 클릭 → 목록 화면에서 해당 기관 사업만 필터 (재클릭 시 해제)
  const [agency, setAgency] = useState(() => {
    const a = new URLSearchParams(window.location.search).get('agency')
    return a ? AGENCIES.find((x) => x.label === a) || null : null
  })
  const selectAgency = (a) => {
    setAgency((prev) => (prev && prev.label === a.label ? null : a))
    setView({ screen: 'main', id: null })
  }

  const goMain = () => setView({ screen: 'main', id: null })
  const openSummary = (id) => setView({ screen: 'summary', id })
  const openOriginal = (id) => setView({ screen: 'original', id })

  // 실시간 시계
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [view])

  return (
    <>
      <div className="bg-glow" />
      <div className="bg-grid" />
      <div className="app">
        <StatusBar agency={agency} onAgency={selectAgency} />
        {view.screen === 'main' && (
          <MainScreen
            onOpen={openSummary}
            agency={agency}
            onClearAgency={() => setAgency(null)}
            now={now}
          />
        )}
        {view.screen === 'summary' && (
          <SummaryScreen id={view.id} onBack={goMain} onOriginal={openOriginal} />
        )}
        {view.screen === 'original' && (
          <OriginalScreen id={view.id} onBack={goMain} onSummary={openSummary} />
        )}
      </div>
    </>
  )
}
