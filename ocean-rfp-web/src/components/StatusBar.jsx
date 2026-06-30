import { AGENCIES } from '../data/projects.js'
import logo from '../assets/geosr-logo.png'

export default function StatusBar({ agency, onAgency }) {
  return (
    <header className="statusbar">
      <div className="statusbar-inner">
        <div className="sb-l">
          <img src={logo} alt="GeoSR · GeoSystem Research Corporation" className="brand-logo" />
        </div>
        <div className="sb-r">
          <div className="agencies">
            {AGENCIES.map((a, i) => (
              <span key={a.label}>
                {i > 0 && <span className="sep">·</span>}
                <button
                  className={`agency-btn${agency && agency.label === a.label ? ' on' : ''}`}
                  onClick={() => onAgency(a)}
                  title={`${a.label} 사업만 보기`}
                >
                  {a.label}
                </button>
              </span>
            ))}
          </div>
          <span className="online">SYSTEM ONLINE</span>
        </div>
      </div>
    </header>
  )
}
