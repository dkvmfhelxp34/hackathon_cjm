import logo from '../assets/geosr-logo.png'

const pad = (n) => String(n).padStart(2, '0')

export default function StatusBar({ now }) {
  const hh = pad(now.getHours())
  const mm = pad(now.getMinutes())
  const date = `${now.getFullYear()}.${pad(now.getMonth() + 1)}.${pad(now.getDate())}`
  const h = now.getHours()
  const label = h < 6 ? 'DAWN' : h < 12 ? 'MORNING' : h < 18 ? 'AFTERNOON' : 'EVENING'

  return (
    <header className="statusbar">
      <div className="statusbar-inner masthead">
        <div className="mast-left">
          <img src={logo} alt="GeoSR · GeoSystem Research Corporation" className="brand-logo" />
          <div className="mast-div" />
          <div className="mast-text">
            <div className="eyebrow">예보사업부 · FORECASTING DIVISION</div>
            <div className="mast-title">예보사업부 RFP <em>통합 대시보드</em></div>
          </div>
        </div>
        <div className="mast-right">
          <div className="clock">
            <div className="t mono">{hh}:{mm}</div>
            <div className="d mono">{label} · {date}</div>
          </div>
          <span className="online">SYSTEM ONLINE</span>
        </div>
      </div>
    </header>
  )
}
