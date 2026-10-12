import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import useAuthStore from '../store/authStore'

export default function Dashboard() {
  const user = useAuthStore((s) => s.user)
  const [stats, setStats] = useState({ projects: 0, tasks: 0, orgs: 0 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [orgs, projects, tasks] = await Promise.all([
          api.get('/organizations'),
          api.get('/projects'),
          api.get('/tasks?page_size=100'),
        ])
        setStats({
          orgs: orgs.data.data?.length || 0,
          projects: projects.data.data?.length || 0,
          tasks: tasks.data.data?.total || 0,
        })
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return <div className="loading">Loading dashboard…</div>

  return (
    <div>
      <h1 style={{ marginBottom: '0.25rem' }}>Dashboard</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
        Welcome back, {user?.full_name}
      </p>

      <div className="grid-stats">
        <div className="stat-card">
          <div className="value">{stats.orgs}</div>
          <div className="label">Organizations</div>
        </div>
        <div className="stat-card">
          <div className="value">{stats.projects}</div>
          <div className="label">Projects</div>
        </div>
        <div className="stat-card">
          <div className="value">{stats.tasks}</div>
          <div className="label">Tasks</div>
        </div>
      </div>

      <div className="card">
        <h2 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>Quick actions</h2>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <Link to="/organizations" className="btn">Manage Organizations</Link>
          <Link to="/projects" className="btn">View Projects</Link>
          <Link to="/notifications" className="btn btn-ghost">Notifications</Link>
        </div>
      </div>
    </div>
  )
}
