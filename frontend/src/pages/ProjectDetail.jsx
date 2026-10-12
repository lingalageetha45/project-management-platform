import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api/client'

export default function ProjectDetail() {
  const { id } = useParams()
  const [project, setProject] = useState(null)
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [p, t] = await Promise.all([
          api.get(`/projects/${id}`),
          api.get(`/tasks?project_id=${id}&page_size=50`),
        ])
        setProject(p.data.data)
        setTasks(t.data.data?.items || [])
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  if (loading) return <div className="loading">Loading…</div>
  if (!project) return <div className="empty">Project not found</div>

  return (
    <div>
      <div style={{ marginBottom: '1rem' }}>
        <Link to="/projects">← Projects</Link>
      </div>
      <h1>{project.name}</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>{project.description || 'No description'}</p>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
        <span className="badge">{project.status}</span>
        <Link to={`/projects/${id}/board`} className="btn">Open Task Board</Link>
      </div>

      <h2 style={{ fontSize: '1.1rem', marginBottom: '0.75rem' }}>Tasks ({tasks.length})</h2>
      {tasks.length === 0 ? (
        <div className="empty">No tasks yet. Open the board to create some.</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Status</th>
              <th>Priority</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <td>{t.title}</td>
                <td><span className={`badge badge-${t.status}`}>{t.status}</span></td>
                <td><span className={`badge badge-${t.priority}`}>{t.priority}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
