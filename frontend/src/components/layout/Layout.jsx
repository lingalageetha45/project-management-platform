import { NavLink, Outlet } from 'react-router-dom'
import useAuthStore from '../../store/authStore'

export default function Layout() {
  const { user, logout } = useAuthStore()

  return (
    <div className="layout">
      <aside className="sidebar">
        <div style={{ marginBottom: '1.5rem', padding: '0 0.5rem' }}>
          <strong style={{ fontSize: '1.15rem' }}>ProjectFlow</strong>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{user?.full_name}</div>
        </div>
        <NavLink to="/" end>Dashboard</NavLink>
        <NavLink to="/organizations">Organizations</NavLink>
        <NavLink to="/projects">Projects</NavLink>
        <NavLink to="/notifications">Notifications</NavLink>
        <NavLink to="/profile">Profile</NavLink>
        <div style={{ marginTop: 'auto', paddingTop: '1rem' }}>
          <button className="btn-ghost" style={{ width: '100%' }} onClick={logout}>
            Logout
          </button>
        </div>
      </aside>
      <main className="main">
        <div className="container">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
