# Sentinova ThreatLens

> A full-stack cybersecurity and Security Operations Center (SOC) platform for threat intelligence, detection, investigation, incident response, and security monitoring.

## Overview

Sentinova ThreatLens brings common SOC workflows into one platform, including threat intelligence, indicators, alerts, incidents, threat hunting, correlation, reporting, audit logging, and real-time security updates.

## Architecture

```text
                    Sentinova ThreatLens
                            |
             +--------------+--------------+
             |                             |
          Frontend                       Backend
          Next.js                        FastAPI
             |                             |
             +-------------+---------------+
                           |
          +----------------+----------------+
          |                |                |
      PostgreSQL         Redis          OpenSearch
                           |
                   Background Jobs
                    / Scheduler
```

## Core Features

- SOC dashboard and security monitoring
- Threat intelligence and IOC management
- Alert management
- Incident response workflows
- Threat hunting
- IOC normalization and enrichment
- Threat scoring and correlation
- MITRE ATT&CK-oriented analysis
- Real-time WebSocket updates
- JWT authentication
- Role-Based Access Control (RBAC)
- MFA support
- Audit logging
- Security reports
- Integrations and feeds
- System health monitoring

## Roles

The platform includes role-based access for roles such as:

- SOC Analyst
- Threat Hunter
- Incident Responder
- Security Engineer
- Administrator
- Executive

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| Cache / Queue | Redis |
| Search / Analytics | OpenSearch |
| Real-time | WebSockets |
| Authentication | JWT |
| Authorization | RBAC |
| Infrastructure | Docker / Docker Compose |

## Project Structure

```text
Sentinova-ThreatLens/
├── backend/
│   ├── app/
│   ├── tests/
│   ├── requirements.txt
│   └── ...
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Demo Login

The project includes a dedicated demo login interface for demonstrations.

Available demo roles include:

```text
SOC Analyst
Threat Hunter
Incident Responder
Security Engineer
Administrator
Executive
```

The demo login uses the project's seeded demo accounts and authenticates through the backend. It is not a frontend-only fake login.

**Do not use demo credentials for production.**

## Running Locally

### Prerequisites

Install:

- Git
- Docker
- Docker Compose
- Node.js and npm
- Python 3.11+ recommended

Check installations:

```bash
git --version
docker --version
docker compose version
node --version
npm --version
python --version
```

### Start the full environment

From the project root:

```bash
docker compose up -d
```

Check services:

```bash
docker compose ps
```

View API logs:

```bash
docker compose logs api --tail=100
```

Stop the environment:

```bash
docker compose down
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:3000
```

### Backend

For a direct backend setup:

```bash
cd backend
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

The API is normally available on:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

### Health check

```bash
curl http://localhost:8000/health
```

## Testing

Backend:

```bash
cd backend
pytest -q
```

Frontend production build:

```bash
cd frontend
npm run build
```

## Environment Variables

Never commit real secrets.

Typical configuration includes:

```text
DATABASE_URL
REDIS_URL
OPENSEARCH_URL
JWT_SECRET
CORS_ORIGINS
API_URL
NEXT_PUBLIC_API_URL
```

Keep real values in local or deployment environment variables.

Do not commit:

```text
.env
backend/.env
frontend/.env
API keys
database passwords
JWT secrets
private keys
cloud credentials
```

## Deployment

The application can be deployed using containerized services or a platform such as Render.

Depending on the required functionality, production may use:

```text
Frontend
Backend API
PostgreSQL
Redis
OpenSearch
Background Worker
Scheduler
```

Before deployment:

1. Configure production environment variables.
2. Use strong production secrets.
3. Configure CORS for trusted origins.
4. Enable HTTPS.
5. Configure the public frontend/backend URLs.
6. Protect PostgreSQL, Redis, and OpenSearch from public access.
7. Review RBAC permissions.
8. Verify WebSocket connectivity.
9. Disable or restrict demo functionality for production.

## Security

This is a cybersecurity project and should only be used in systems and environments where you have authorization.

Recommended production practices:

- Never expose database or Redis ports publicly.
- Never commit credentials.
- Use HTTPS.
- Use strong JWT secrets.
- Restrict administrative permissions.
- Configure CORS explicitly.
- Rotate exposed credentials immediately.
- Review API permissions before public deployment.
- Use separate credentials for development and production.

## Purpose

Sentinova ThreatLens demonstrates practical cybersecurity and software engineering skills across:

- SOC operations
- Threat intelligence
- Threat hunting
- Incident response
- IOC enrichment
- Security monitoring
- Authentication and authorization
- REST APIs
- Real-time systems
- Database and search infrastructure
- Docker-based deployment

## Project Status

**Status:** Internship / portfolio cybersecurity project

The project is intended for authorized security testing, educational use, controlled demonstrations, and portfolio presentation.

## Author

**Adiba Parveen**

GitHub:

https://github.com/AdibaParveen

## Disclaimer

This project is intended for authorized security testing, education, and controlled environments.

Do not use it to access, scan, monitor, or interfere with systems without explicit authorization.
