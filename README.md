# BikeCare — Smart Bike Service Management Platform (Security-Hardened)

BikeCare is an enterprise-grade, full-stack multi-tenant two-wheeler service center management application. It covers end-to-end garage operations across four distinct user roles (**Customer**, **Employee / Service Advisor**, **Mechanic**, and **Owner**), featuring digital estimates with customer sign-off, strict payment-enforced vehicle handover, AI-assisted symptom diagnosis, and multi-tenant garage isolation.

---

## 1. Project Overview & Security Architecture

### Key Security Enhancements
- **Password Policy**: Minimum 10 characters, mixed case, numbers, blacklist against top 1,000 common passwords, and username restriction.
- **Brute-Force & Lockout**: 5 failed login attempts per email or 20 per IP in 15 minutes triggers an automated 15-minute HTTP 429 lockout.
- **Session & Token Hardening**: Short-lived JWT access tokens (15 minutes) kept exclusively in JavaScript memory. 7-day refresh tokens stored SHA-256 hashed in HttpOnly, SameSite=Lax cookies with automatic token rotation and family-based theft revocation. Immediate token invalidation via `token_version`.
- **Forced Password Changes**: Owner-created staff accounts must change their temporary password on first login.
- **Two-Factor Authentication**: Optional TOTP MFA using `pyotp` with Fernet-encrypted secrets and 8 single-use recovery codes.
- **Object-Level Authorization (IDOR Defense)**: Access checks return HTTP 404 (never 403) to prevent leaking the existence of foreign jobs, bikes, or providers.
- **Mass-Assignment Defense**: `model_config = ConfigDict(extra='forbid')` enforced on all Pydantic request models.
- **Injection Safety**: Parameterized queries via SQLAlchemy ORM, wildcard escaping for search strings, and HTML escaping / strict CSP meta tags on the frontend.
- **Business Logic Concurrency**: Database row-locking (`with_for_update`) on estimate decisions. Immutable invoices with audited void and reissue workflows.
- **Audit Logging**: Immutable, tamper-evident `audit_logs` table tracking logins, lockouts, approvals, invoices, and file actions with automatic sensitive credential redaction.

---

## 2. Technology Stack

| Layer | Technologies |
|---|---|
| **Backend API** | Python 3.10, FastAPI, Uvicorn, Starlette, SlowAPI (Rate Limiting) |
| **Data & ORM** | SQLAlchemy 2.0, Alembic, PostgreSQL (`psycopg2-binary`) / SQLite fallback |
| **Security & Auth** | PyJWT, Bcrypt (cost 12), PyOTP, Cryptography (Fernet), Pydantic v2 |
| **File Processing** | Pillow (EXIF metadata stripping and image re-encoding), Supabase Storage |
| **Static & Security Scanners** | Bandit, Pip-Audit, Gitleaks configuration |
| **Frontend** | Vanilla HTML5, CSS3, JavaScript ES6+ Fetch (in-memory token client) |
| **Testing** | Pytest, HTTPX, SQLite in-memory test database with Neon safety check |

---

## 3. Windows PowerShell Setup & Installation

### Step 3.1: Navigate to the Backend Directory
```powershell
cd "c:\Users\DELL\Desktop\gaurage project\BikeCare\backend"
```

### Step 3.2: Create and Activate Virtual Environment
```powershell
# Create virtual environment
python -m venv venv

# If PowerShell script execution is restricted, temporarily set ExecutionPolicy:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

### Step 3.3: Install Dependencies
```powershell
python -m pip install --upgrade pip setuptools
pip install -r requirements.txt
```

### Step 3.4: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Ensure `SECRET_KEY` is at least 32 characters long. In production, ensure `DATABASE_URL` contains `sslmode=require` and `CORS_ORIGINS` uses `https://`.

---

## 4. Database Setup & Alembic Migrations

### Apply Migrations
```powershell
.\venv\Scripts\alembic.exe upgrade head
```

### Create a New Migration (Windows PowerShell)
```powershell
.\venv\Scripts\alembic.exe revision --autogenerate -m "migration_description"
```

### Least-Privilege Database User Setup (PostgreSQL)
For production hosting, create a dedicated application user that cannot execute DDL commands (ALTER, DROP) or access administrative tables:
```sql
-- 1. Create limited application user
CREATE USER bikecare_app WITH PASSWORD 'secure_app_password';

-- 2. Grant connection and schema usage
GRANT CONNECT ON DATABASE bikecare_db TO bikecare_app;
GRANT USAGE ON SCHEMA public TO bikecare_app;

-- 3. Grant DML only (SELECT, INSERT, UPDATE, DELETE) on existing & future tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bikecare_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO bikecare_app;

-- 4. Grant sequence usage for auto-increment IDs
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bikecare_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO bikecare_app;
```

---

## 5. First-Time Setup & Demo Data

```powershell
# Create Initial Owner
python -m app.create_owner --name "Vikram Singh" --email "owner@bikecare.com" --password "Owner@1234" --garage "Apex Moto Care"

# Seed Demo Data (Multi-role, vehicles, estimates, invoices)
python -m app.seed_demo
```

---

## 6. Running the Application

### Terminal 1 — Start the Backend (Port 8000)
```powershell
cd "c:\Users\DELL\Desktop\gaurage project\BikeCare\backend"
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2 — Secure Development Frontend Server (Port 5500)
```powershell
cd "c:\Users\DELL\Desktop\gaurage project\BikeCare\frontend"
python serve.py
```
`serve.py` automatically serves the frontend on `http://localhost:5500` with strict Content Security Policy (CSP), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, and `Referrer-Policy` headers.

---

## 7. Security Scans & Test Suite

### Running Pytest Test Suite (31 Passed)
```powershell
cd "c:\Users\DELL\Desktop\gaurage project\BikeCare\backend"
.\venv\Scripts\pytest -v
```

### Running Static Security Analysis (Bandit)
```powershell
.\venv\Scripts\bandit.exe -r app
```
*(Result: 0 High, 0 Medium issues).*

### Running Known Vulnerability Dependency Scan (Pip-Audit)
```powershell
.\venv\Scripts\pip-audit.exe
```
*(Result: No known vulnerabilities found).*

### Secret Scanning Before Commits
A Gitleaks baseline configuration is provided in `.gitleaks.toml`. Run gitleaks or detect-secrets:
```powershell
gitleaks detect --source . -v
```

---

## 8. Role Matrix & Demo Credentials

| Role | Demo Email | Demo Password | Responsibilities |
|---|---|---|---|
| **Owner** | `owner@bikecare.com` | `Owner@1234` | Financial KPIs, staff management, audit log dashboard, invoice voids, settings. |
| **Employee** | `employee@bikecare.com` | `Staff@1234` | Reception queue, intake inspection, estimate creation, payments, delivery. |
| **Mechanic** | `mechanic@bikecare.com` | `Staff@1234` | Repair bays, diagnosis logging, spare parts recording, work sessions. |
| **Customer** | `customer@bikecare.com` | `Customer@1234` | Register motorcycles, book requests, approve/reject estimates, view invoices. |
