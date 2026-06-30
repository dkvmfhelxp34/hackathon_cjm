import { AGENCIES } from '../data/projects.js'
import logo from '../assets/geosr-logo.png'

export default function StatusBar({ agency, onAgency }) {
  return (
    <div className="statusbar">
      <div className="sb-l">
        <div className="logo">
          <img src={logo} alt="GeoSR" className="brand-logo" />
        </div>
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
  )
}
