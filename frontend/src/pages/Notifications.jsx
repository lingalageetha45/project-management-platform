import { useEffect, useState } from 'react'
import api from '../api/client'

export default function Notifications() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const { data } = await api.get('/notifications')
      setItems(data.data?.items || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const markAll = async () => {
    await api.patch('/notifications/read-all')
    load()
  }

  if (loading) return <div className="loading">Loading…</div>

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1>Notifications</h1>
        <button className="btn-ghost" onClick={markAll}>Mark all read</button>
      </div>
      {items.length === 0 ? (
        <div className="empty">No notifications</div>
      ) : (
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          {items.map((n) => (
            <div key={n.id} className="card" style={{ opacity: n.is_read ? 0.7 : 1 }}>
              <strong>{n.title}</strong>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{n.message}</p>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                {n.created_at} · {n.type}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
