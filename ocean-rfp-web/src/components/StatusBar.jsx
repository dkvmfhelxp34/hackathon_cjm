import logo from '../assets/geosr-logo.png'

const pad = (n) => String(n).padStart(2, '0')

const WD = ['일', '월', '화', '수', '목', '금', '토']

export default function StatusBar({ now }) {
  const h = now.getHours()
  const hh = pad(h)
  const mm = pad(now.getMinutes())
  const ss = pad(now.getSeconds())
  const ampm = h < 12 ? '오전' : '오후'
  const wd = WD[now.getDay()]
  const date = `${now.getFullYear()}.${pad(now.getMonth() + 1)}.${pad(now.getDate())}`

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
            <div className="clock-time">
              <span className="clock-live" />
              <span className="hm mono">{hh}<span className="colon">:</span>{mm}</span>
              <span className="ss mono">{ss}</span>
            </div>
            <div className="clock-meta mono">{ampm} · {date} ({wd})</div>
          </div>
          <span className="online">SYSTEM ONLINE</span>
        </div>
      </div>
    </header>
  )
}
