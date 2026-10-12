# MediManage

MediManage is a Django-based foundation for managing clinic and hospital patient information.

## Run & Operate

- `python manage.py` — Django management entry point (dependencies are listed in `requirements.txt`)
- `python manage.py runserver 0.0.0.0:8000` — run the Django development server
- `python manage.py check` — validate Django configuration
- `python manage.py test` — run the Django test suite

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- Python, Django, SQLite for development, PostgreSQL for production

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `manage.py` — Django command-line entry point
- `medimanage/` — Django project package
- `apps/` — feature-specific Django apps, added in later phases
- `templates/` — server-rendered templates
- `templates/authentication/` — login, password change, and password reset templates
- `static/` — source static assets
- `media/` — uploaded media files
- `requirements.txt` — Python dependencies

Phases 1–7 are currently complete: project setup, Django configuration, modular
app structure, authentication, RBAC, the core database model layer, and staff
patient-profile management and patient account activation. Appointment management,
clinical interfaces, and reporting remain intentionally staged.

## Architecture decisions

- The Django project is kept at the repository root to match the PRD's requested structure.
- Feature apps are grouped under `apps/` so each later module can remain isolated.
- Local secrets belong in `.env`, which is ignored; `.env.example` documents the expected names.
- Django's built-in authentication views provide the initial sign-in, logout,
  password change, and password reset flows.
- First-login password enforcement uses a session gate so temporary credentials
  cannot be used to access the rest of the application.
- RBAC uses Django Groups with the canonical names `ADMIN`, `RECEPTIONIST`,
  `DOCTOR`, and `PATIENT`.
- Role checks are enforced server-side through reusable decorators/mixins and
  administrator middleware; dashboards and the Patient model come later.
- Patient ownership is temporarily enforced against the linked Django user ID
  until the Patient model is introduced.
- Core clinic entities use separate Django apps and initial migrations:
  patient profiles, staff/doctor profiles, appointments, medical records,
  consultations, prescriptions, notifications, and audit logs.
- Audit log records are read-only through the Django admin interface.
- Patient registration is staff-controlled: administrators and receptionists
  can create, search, edit, deactivate, and archive profiles.
- Patient profile mutations create audit log entries, while doctors have
  read-only profile access and patients can view only their linked profile.

## Product

The current milestone includes working sign-in, password management,
server-side role access checks, a migrated SQLite data foundation, a
staff-controlled patient profile workflow, and patient account activation.
Appointments and dashboards will be implemented in subsequent phases.

## User preferences

The user requested that the PRD be implemented one phase at a time, beginning with Phase 1.

## Gotchas

- Do not add authentication, dashboards, models, or other later-phase features until their phase is requested.
- Install Python packages from `requirements.txt` before running Django management commands.
- The role redirect currently lands on the setup page with a role marker until
  the role-specific dashboards are implemented.
- Run `python manage.py ensure_roles` when initializing a new development database.
- Run `python manage.py makemigrations` and `python manage.py migrate` after model changes.
- Patient account activation is staff-controlled: administrators and
  receptionists can create a restricted patient login, and the patient
  receives a temporary password by email and must change it on first login.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
