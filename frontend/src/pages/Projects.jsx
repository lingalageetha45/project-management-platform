import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'

export default function Projects() {
  const [projects, setProjects] = useState([])
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ name: '', description: '', organization_id: '' })
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const [p, o] = await Promise.all([api.get('/projects'), api.get('/organizations')])
      setProjects(p.data.data || [])
      setOrgs(o.data.data || [])
      if (o.data.data?.length && !form.organization_id) {
        setForm((f) => ({ ...f, organization_id: o.data.data[0].id }))
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const create = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/projects', {
        name: form.name,
        description: form.description,
        organization_id: Number(form.organization_id),
      })
      setForm({ name: '', description: '', organization_id: form.organization_id })
      load()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed')
    }
  }

  if (loading) return <div className="loading">Loading…</div>

  return (
    <div>
      <h1 style={{ marginBottom: '1.5rem' }}>Projects</h1>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1rem', marginBottom: '1rem' }}>Create Project</h2>
        <form onSubmit={create} style={{ display: 'grid', gap: '0.75rem', maxWidth: 420 }}>
          <input
            placeholder="Project name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          <select
            value={form.organization_id}
            onChange={(e) => setForm({ ...form, organization_id: e.target.value })}
            required
          >
            <option value="">Select organization</option>
            {orgs.map((o) => (
              <option key={o.id} value={o.id}>{o.name}</option>
            ))}
          </select>
          <textarea
            placeholder="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={2}
          />
          {error && <div className="error">{error}</div>}
          <button type="submit">Create Project</button>
        </form>
      </div>

      {projects.length === 0 ? (
        <div className="empty">No projects yet.</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Org ID</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.id}>
                <td><strong>{p.name}</strong></td>
                <td><span className="badge">{p.status}</span></td>
                <td>{p.organization_id}</td>
                <td>
                  <Link to={`/projects/${p.id}`}>Details</Link>
                  {' · '}
                  <Link to={`/projects/${p.id}/board`}>Board</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
