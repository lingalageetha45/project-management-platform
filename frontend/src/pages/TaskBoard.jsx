import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api/client'

const COLUMNS = [
  { key: 'backlog', label: 'Backlog' },
  { key: 'todo', label: 'Todo' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'review', label: 'Review' },
  { key: 'done', label: 'Done' },
]

export default function TaskBoard() {
  const { id } = useParams()
  const [tasks, setTasks] = useState([])
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const { data } = await api.get(`/tasks?project_id=${id}&page_size=100`)
      setTasks(data.data?.items || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  const createTask = async (e) => {
    e.preventDefault()
    if (!title.trim()) return
    setError('')
    try {
      await api.post('/tasks', { title, project_id: Number(id), status: 'backlog' })
      setTitle('')
      load()
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to create task')
    }
  }

  const moveTask = async (taskId, newStatus) => {
    try {
      await api.patch(`/tasks/${taskId}/status`, { status: newStatus })
      load()
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Invalid transition')
    }
  }

  if (loading) return <div className="loading">Loading board…</div>

  return (
    <div>
      <div style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Link to={`/projects/${id}`}>← Project</Link>
        <h1 style={{ fontSize: '1.25rem' }}>Task Board</h1>
      </div>

      <form onSubmit={createTask} style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', maxWidth: 480 }}>
        <input
          placeholder="New task title…"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <button type="submit">Add</button>
      </form>
      {error && <div className="error" style={{ marginBottom: '1rem' }}>{error}</div>}

      <div className="kanban">
        {COLUMNS.map((col) => (
          <div key={col.key} className="kanban-column">
            <h3>{col.label} ({tasks.filter((t) => t.status === col.key).length})</h3>
            {tasks
              .filter((t) => t.status === col.key)
              .map((t) => (
                <div key={t.id} className="task-card">
                  <div className="title">{t.title}</div>
                  <div className="meta">
                    <span className={`badge badge-${t.priority}`}>{t.priority}</span>
                  </div>
                  <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                    {COLUMNS.filter((c) => c.key !== t.status).map((c) => (
                      <button
                        key={c.key}
                        className="btn-ghost"
                        style={{ fontSize: '0.7rem', padding: '0.2rem 0.4rem' }}
                        onClick={() => moveTask(t.id, c.key)}
                      >
                        → {c.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
          </div>
        ))}
      </div>
    </div>
  )
}
