import { useEffect, useState } from 'react'
import api from '../api/client'

export default function Organizations() {
  const [orgs, setOrgs] = useState([])
  const [loading, setLoading] = useState(true)
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const { data } = await api.get('/organizations')
      setOrgs(data.data || [])
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
      await api.post('/organizations', { name, description: desc })
      setName('')
      setDesc('')
      load()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to create')
    }
  }

  if (loading) return <div className="loading">Loading…</div>

  return (
    <div>
      <h1 style={{ marginBottom: '1.5rem' }}>Organizations</h1>

      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1rem', marginBottom: '1rem' }}>Create Organization</h2>
        <form onSubmit={create} style={{ display: 'grid', gap: '0.75rem', maxWidth: 400 }}>
          <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
          <textarea placeholder="Description (optional)" value={desc} onChange={(e) => setDesc(e.target.value)} rows={2} />
          {error && <div className="error">{error}</div>}
          <button type="submit">Create</button>
        </form>
      </div>

      {orgs.length === 0 ? (
        <div className="empty">No organizations yet. Create one above.</div>
      ) : (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {orgs.map((o) => (
            <div key={o.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <strong>{o.name}</strong>
                  <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{o.slug}</div>
                </div>
                <span className="badge">{o.is_active ? 'Active' : 'Inactive'}</span>
              </div>
              {o.description && <p style={{ marginTop: '0.5rem', color: 'var(--text-muted)' }}>{o.description}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
