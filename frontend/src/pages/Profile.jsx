import useAuthStore from '../store/authStore'

export default function Profile() {
  const user = useAuthStore((s) => s.user)

  return (
    <div>
      <h1 style={{ marginBottom: '1.5rem' }}>Profile</h1>
      <div className="card" style={{ maxWidth: 420 }}>
        <div className="form-group">
          <label>Full name</label>
          <input value={user?.full_name || ''} readOnly />
        </div>
        <div className="form-group">
          <label>Email</label>
          <input value={user?.email || ''} readOnly />
        </div>
        <div className="form-group">
          <label>Role</label>
          <input value={user?.is_superuser ? 'Super Admin' : 'User'} readOnly />
        </div>
      </div>
    </div>
  )
}
