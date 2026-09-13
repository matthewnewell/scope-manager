import { NavLink } from 'react-router-dom'
import './Nav.css'

export default function Nav() {
  return (
    <nav className="sm-nav">
      <NavLink to="/about" className="sm-nav__brand">
        Scope Manager
      </NavLink>
      <div className="sm-nav__links">
        <NavLink
          to="/"
          end
          className={({ isActive }) => `sm-nav__link ${isActive ? 'sm-nav__link--active' : ''}`}
        >
          Scope
        </NavLink>
      </div>
    </nav>
  )
}
