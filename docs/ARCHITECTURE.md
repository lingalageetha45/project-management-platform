# Architecture Overview

## Clean Architecture Layers

```
┌─────────────────────────────────────────┐
│              Frontend (React)           │
│  Pages · Components · Zustand · Axios   │
└──────────────────┬──────────────────────┘
                   │ HTTPS / JWT
┌──────────────────▼──────────────────────┐
│           FastAPI Routes                │
│  /api/auth  /api/organizations  ...     │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│         Dependencies (deps.py)          │
│  get_current_user · get_project_with_   │
│  access · require_org_role              │
│  → Multi-tenant + RBAC enforcement      │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│              Services                   │
│  AuthService · OrganizationService      │
│  ProjectService · TaskService           │
│  NotificationService · AuditService     │
│  → Business rules, transitions,         │
│    dependency checks, side-effects      │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│         SQLAlchemy Models               │
│  User · Organization · Project · Task   │
│  Comment · Attachment · Notification    │
│  AuditLog · RefreshToken                │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│              PostgreSQL                 │
└─────────────────────────────────────────┘
```

## Security Guarantees

1. **Authentication** – JWT access tokens (short-lived) + refresh tokens (rotated & stored).
2. **Inactive users** cannot obtain tokens.
3. **Organization isolation** – every resource lookup joins / filters by organization membership.
4. **Resource-level checks** – `get_project_with_access` / `get_task_with_access` prevent IDOR.
5. **Role checks** – `require_org_role([...])` for admin-only operations.
6. **Business rules** – status transitions, circular dependency prevention, viewer assignment blocked.

## Error Format

```json
{
  "success": false,
  "error": {
    "code": "TASK_ORGANIZATION_ACCESS_DENIED",
    "message": "You do not have access to this task."
  }
}
```

Status codes: 400, 401, 403, 404, 409, 422, 500.
