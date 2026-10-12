# ProjectFlow – Multi-Tenant Project & Workflow Management Platform

Production-oriented full-stack application demonstrating:

- **Multi-tenant isolation** (organization-scoped resources)
- **Role-based + resource-based authorization**
- **JWT authentication** (access + refresh tokens with rotation)
- **Clean architecture** (Routes → Dependencies → Services → Models)
- **Task workflow with valid transitions & dependencies**
- **Notifications, Audit logs, Pagination/Filtering**
- **React frontend** with protected routes, Kanban board, dashboards
- **Docker Compose** ready deployment

## Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Frontend  | React 18, Vite, React Router, Zustand, Axios |
| Backend   | FastAPI, SQLAlchemy 2, Pydantic v2, Alembic |
| Database  | PostgreSQL 16                       |
| Auth      | JWT (python-jose) + bcrypt          |
| Optional  | Redis, Celery (scaffolded)          |

## Quick Start (Docker)

```bash
cd project-management-platform

# Copy env
cp backend/.env.example backend/.env

# Start everything
docker compose up --build -d

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
```

**Default Super Admin**
- Email: `superadmin@projectflow.local`
- Password: `SuperAdmin@123`

## Local Development (without Docker)

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start PostgreSQL locally and update DATABASE_URL in .env
# Then:
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

## Architecture

```
Routes (FastAPI)
   ↓
Dependencies (auth, multi-tenant checks)
   ↓
Services (business logic, validation, notifications)
   ↓
Models / SQLAlchemy
   ↓
PostgreSQL
```

### Multi-Tenant Isolation

Every sensitive endpoint verifies that the requested resource belongs to an organization the authenticated user is a member of.  
Changing IDs in URLs/payloads cannot leak data across tenants.

### Roles

- `super_admin` – full system access
- `organization_admin` – manage org members & settings
- `project_manager` – manage projects & assign tasks
- `team_member` – work on assigned tasks
- `viewer` – read-only (cannot be assigned tasks)

### Task Workflow

Valid transitions are enforced server-side:

```
Backlog → Todo → In Progress → Review → Done
                ↘ Blocked
Any → Cancelled (with reopen rules)
```

Dependencies: a task cannot move to In Progress / Review / Done while any dependency is incomplete. Circular dependencies are rejected.

## API Overview

| Area            | Endpoints                                      |
|-----------------|------------------------------------------------|
| Auth            | `/api/auth/register|login|refresh|logout|me|change-password` |
| Organizations   | CRUD + members + roles                         |
| Projects        | CRUD + members                                 |
| Tasks           | CRUD + status + assign + dependencies + filters|
| Notifications   | list / mark-read / mark-all-read               |

Full interactive docs: `http://localhost:8000/docs`

## Testing

```bash
cd backend
pytest app/tests -v
```

(Starter tests included for auth & multi-tenant isolation.)

## Project Structure

```
project-management-platform/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # route handlers
│   │   ├── core/               # config, security, exceptions
│   │   ├── db/                 # session, base
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic
│   │   ├── services/           # business logic
│   │   └── main.py
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── store/
│   │   └── styles/
│   └── Dockerfile
├── docs/                       # ER diagram, architecture
├── docker-compose.yml
└── README.md
```

## Deliverables Checklist

- [x] Multi-tenant isolation
- [x] JWT auth (register/login/refresh/logout/me/change-password)
- [x] Role + resource authorization
- [x] Organizations + members + roles
- [x] Projects CRUD + status transitions
- [x] Tasks CRUD + workflow + assignment + dependencies
- [x] Notifications
- [x] Audit logging
- [x] Pagination / filtering / search
- [x] Consistent error responses
- [x] React frontend (Login, Register, Dashboard, Orgs, Projects, Task Board, Notifications, Profile)
- [x] Protected routes + role-aware UI skeleton
- [x] Docker Compose
- [x] Alembic ready
- [x] README + setup instructions
- [x] ER diagram (see `docs/`)
- [ ] Full Celery workers / WebSocket fan-out (scaffolded – extendable)
- [ ] Complete test matrix (starter present)
- [ ] File upload endpoints (model ready – endpoint can be added in 30 min)
- [ ] Comments endpoints (model ready)

## Extending

- **File uploads**: implement `/api/attachments` using the existing `Attachment` model + MIME validation.
- **Comments + mentions**: use `Comment` model + parse `@username` → NotificationService.
- **WebSockets**: add `fastapi.WebSocket` endpoint and push from NotificationService.
- **Celery**: move overdue checks / email to a worker using the Redis service already in docker-compose.

## License

MIT – built as an engineering assignment demonstration.
