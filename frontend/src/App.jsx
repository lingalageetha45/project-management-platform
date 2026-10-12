import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/authStore'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import TaskBoard from './pages/TaskBoard'
import Organizations from './pages/Organizations'
import Notifications from './pages/Notifications'
import Profile from './pages/Profile'
import Layout from './components/layout/Layout'
import ProtectedRoute from './components/auth/ProtectedRoute'

export default function App() {
  const { fetchMe, loading } = useAuthStore()

  useEffect(() => {
    fetchMe()
  }, [fetchMe])

  if (loading) {
    return <div className="loading">Loading ProjectFlow…</div>
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/organizations" element={<Organizations />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/projects/:id/board" element={<TaskBoard />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
