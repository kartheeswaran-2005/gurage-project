# FIX_NOTES.md - Root Cause Analysis & Verification

## 1. Problem Summary
When loading the employee page `http://127.0.0.1:8000/employee/requests.html` (title 'Workshop Service Queue', sidebar item 'Service Requests'), users observed the message:
`"Failed to load data. Please retry."` with an empty table and `"Showing 0 of 0"`.

---

## 2. Root Cause & Evidence

### Cause A: Timing & Session Restoration Race Condition in Frontend
- **Evidence:** Network trace revealed a `401 Unauthorized` request to `/api/requests` right upon page initialization.
- **Root Cause:** In the frontend (`frontend/js/api.js`), the access token was stored in memory (`inMemoryAccessToken`). When navigating between pages or reloading, the token in memory was initially `null`. Previously, pages immediately initiated table queries via `fetch` before waiting for the auth guard / silent refresh check to complete (`Auth.restoreSession()`).
- **Fix:**
  - Implemented an exported `sessionReady` promise in [api.js](file:///c:/Users/DELL/Desktop/gaurage%20project/BikeCare/frontend/js/api.js) and session cache in `sessionStorage`.
  - Updated [auth-guard.js](file:///c:/Users/DELL/Desktop/gaurage%20project/BikeCare/frontend/js/auth-guard.js) and individual page controllers across all roles (`employee`, `mechanic`, `owner`, `customer`) to await `API.sessionReady` before triggering initial data requests.
  - On receiving any unexpected `401`, `api.js` automatically executes one silent refresh via `/api/auth/refresh` and transparently retries the failed request once before failing.

### Cause B: `MultipleResultsFound` 500 Server Error in `serialize_request`
- **Evidence:** Backend server log showed:
  ```text
  File "C:\Users\DELL\Desktop\gaurage project\BikeCare\backend\app\api\requests.py", line 67, in serialize_request
    active_assignment = db.execute(
        select(JobAssignment).where(
            JobAssignment.service_request_id == req.id,
            JobAssignment.unassigned_at.is_(None)
        )
    ).scalar_one_or_none()
  sqlalchemy.exc.MultipleResultsFound: Multiple rows were found when one or none was required
  ```
- **Root Cause:** When multiple active job assignments existed or had unassigned_at is null for a single service request in the database, `scalar_one_or_none()` raised `MultipleResultsFound`, crashing the request list serialization with HTTP 500.
- **Fix:** In [requests.py](file:///c:/Users/DELL/Desktop/gaurage%20project/BikeCare/backend/app/api/requests.py), changed the query to `.order_by(desc(JobAssignment.id)).scalars().first()`, safely fetching the latest active assignment without throwing.

### Cause C: Query Filter Date Parameter Formatting (HTTP 422)
- **Evidence:** Querying requests with `date_from` or `date_to` caused `422 Unprocessable Entity` when spaces were decoded from unencoded `+` timezone offsets in URL query strings (e.g. `2026-10-17T07:08:07.675655 00:00`), or when empty filter strings were passed (`date_from=&status=`).
- **Root Cause:** Pydantic `datetime` parsing failed when spaces replaced `+` in timezone offsets. Also, empty string filters (`""`) caused validation failures.
- **Fix:**
  - Added robust date parser `_parse_filter_date` in [requests.py](file:///c:/Users/DELL/Desktop/gaurage%20project/BikeCare/backend/app/api/requests.py) that accommodates ISO formats, space-encoded timezone offsets, date-only formats, and empty strings.
  - Sanitized `mechanic_id`, `status`, and `q` to treat empty strings as omitted filters.
  - Escaped `%` and `_` SQL wildcards in search query `q`.

---

## 3. Clear Error & Empty States
Updated [table.js](file:///c:/Users/DELL/Desktop/gaurage%20project/BikeCare/frontend/js/table.js) and [api.js](file:///c:/Users/DELL/Desktop/gaurage%20project/BikeCare/frontend/js/api.js):
- **401:** *"Your session expired. Please log in again."* (redirects gracefully to login page).
- **403:** *"You do not have permission to view this."*
- **404:** *"This data could not be found."*
- **422:** *"Some filter values are not valid."*
- **429:** *"Too many requests. Please wait a minute and try again."*
- **500 / Network Failure:** *"Something went wrong on the server. Please try again."* plus the unique Request ID (`X-Request-ID`), alongside a working **Retry** button.
- **Empty State:** When total items is 0, rendered a friendly empty state (*"No records found" / "No service requests found"*) distinct from error states.

---

## 4. Health Check Endpoint
Enhanced `GET /api/health` in [main.py](file:///c:/Users/DELL/Desktop/gaurage%20project/BikeCare/backend/app/main.py):
- Connects to the database and verifies connectivity with `SELECT 1`.
- Reads and returns the current Alembic migration revision (`c82df9108b31`).
- Logs the masked database connection string and connection status on startup.

---

## 5. Test Results

### Pytest Backend Test Suite
- Executed `pytest`:
  - **74 passed, 0 failed** across all 11 test modules:
    - `test_requests_list.py`: 26 passed (zero rows, many rows, each filter alone, all combined, empty strings, invalid 422 inputs, provider isolation, and no-provider employees).
    - `test_auth.py`: 6 passed
    - `test_estimates.py`: 2 passed
    - `test_files_and_assistant.py`: 2 passed
    - `test_first_login_flow.py`: 17 passed
    - `test_invoices_closing.py`: 1 passed
    - `test_permissions_isolation.py`: 4 passed
    - `test_reports_analytics.py`: 1 passed
    - `test_requests_workflow.py`: 3 passed
    - `test_security_hardening.py`: 12 passed

### Real Browser Verification
- Logged into `http://127.0.0.1:8000/login.html` as employee (`employee@bikecare.com`).
- Visited `http://127.0.0.1:8000/employee/requests.html`.
- Verified workshop queue loaded 4 requests without errors (`BC-2026-000007`, `BC-2026-000004`, `BC-2026-000003`, `BC-2026-000002`).
- Search, status filters, mechanic filters, and pagination controls verified functional.
