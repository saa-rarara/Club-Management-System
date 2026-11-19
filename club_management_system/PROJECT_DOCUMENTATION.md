# SAU Club Management System — Development Documentation

**Status as of 20 November 2026:** all roadmap phases (authentication, student, faculty and administrator dashboards, workflow integration, UI polish) have been implemented. The automated test suite passes (112 of 112 checks) against a **SQLite stand-in** for MySQL. The final step, running the same flows on your real MySQL database, is still to be done. Section 11 has the checklist.

This document follows on from the earlier *Development Progress Report*. It records what was found in the code, what was changed and why, how each part works, how it was tested, and what is left.

---

## Contents

1. [What was found when the code was inspected](#1-what-was-found-when-the-code-was-inspected)
2. [How to run the project](#2-how-to-run-the-project)
3. [Project structure](#3-project-structure)
4. [How the pieces communicate](#4-how-the-pieces-communicate)
5. [Authentication and sessions](#5-authentication-and-sessions)
6. [Role-based access control](#6-role-based-access-control)
7. [Module-by-module description](#7-module-by-module-description)
8. [Complete route reference](#8-complete-route-reference)
9. [Security decisions](#9-security-decisions)
10. [Change log against the previous version](#10-change-log-against-the-previous-version)
11. [Testing](#11-testing)
12. [Known limitations and future work](#12-known-limitations-and-future-work)

---

## 1. What was found when the code was inspected

The latest ZIP (`club_management_system_2.zip`) was inspected in full before anything was changed: `app.py`, all five templates, `style.css`, `setup_admin.py`, `requirements.txt` and `SEproject.sql`.

### 1.1 Already working (confirmed in the earlier report)

- MySQL connection through the `MYSQL_PASSWORD` environment variable.
- Initial administrator account (`ADMIN_01`, admin_id 1) created with `setup_admin.py`.
- Login, logout, sessions, password hashing.
- Student management: listing, search and filters, account creation, password reset, status change.

### 1.2 Problems found

| # | Problem | Effect |
|---|---------|--------|
| 1 | **Eight templates referenced by `app.py` did not exist:** `student_clubs.html`, `student_memberships.html`, `application_form.html`, `student_applications.html`, `faculty_applications.html`, `admin_clubs.html`, `admin_faculty.html`, `admin_applications.html` | Every page apart from the three dashboards and Manage Students crashed with `TemplateNotFound` (HTTP 500). |
| 2 | No way to create **faculty** login accounts | Faculty could never log in, so the approval workflow could not be completed. |
| 3 | No page for assigning **presidents and advisors** (the POST routes existed, but no form called them) | Assignments could only be made by editing the database by hand. |
| 4 | `login.html` did not display flash messages | Users never saw "Invalid username or password" or "Your account is inactive". |
| 5 | `login.html` still contained a public **"Sign Up"** link | This contradicted the agreed policy that only administrators create accounts. |
| 6 | No CSRF protection on any POST form | Another website could submit forms on behalf of a logged-in administrator. |
| 7 | A deactivated user stayed logged in until their 2-hour session expired | Deactivation was not immediate. |
| 8 | `update_student_status` reported "Student record not found" when the new status equalled the old one | MySQL returns `rowcount = 0` for an UPDATE that changes nothing, which the code took to mean "not found". |
| 9 | `update_faculty_status` had no error handling | A database error produced a crash page. |
| 10 | `assign_advisor` did not check that the faculty member or club existed or was active | It could assign an inactive faculty member, or fail with a raw database error. |
| 11 | Student application dates were compared as strings and could be in the past | There was no server-side validation of the date format, and past events were accepted. |
| 12 | The 403 and 404 handlers returned plain text, and an unhandled MySQL error showed a stack trace | This was inconsistent with the rest of the UI. |
| 13 | The global CSS put `display:flex` on `body` and `width:100%` on every input and button | This broke the layout of every page except login. |

---

## 2. How to run the project

### 2.1 First-time setup (Windows PowerShell, the environment you are using)

```powershell
cd "club management system"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

On macOS the activation line is `source .venv/bin/activate`.

> **Do not re-import `SEproject.sql`.** It begins each table with `DROP TABLE`, which would delete the accounts you have already created. None of the changes in this version require any database change.

### 2.2 Set environment variables, then start Flask

```powershell
$env:MYSQL_PASSWORD   = "YOUR_MYSQL_ROOT_PASSWORD"
$env:FLASK_SECRET_KEY = "any-long-random-string"     # optional, recommended
python app.py
```

macOS / Linux:

```bash
export MYSQL_PASSWORD="YOUR_MYSQL_ROOT_PASSWORD"
export FLASK_SECRET_KEY="any-long-random-string"
python app.py
```

Then open <http://127.0.0.1:5000>.

Optional variables, with their defaults: `MYSQL_HOST=localhost`, `MYSQL_USER=root`, `MYSQL_DATABASE=sau_club_management`.

### 2.3 Administrator accounts

`ADMIN_01` already exists in your database. To give another administrator (admin_id 2–10) a login, run:

```powershell
python setup_admin.py
```

The script now lists all administrator records, shows which ones already have a login, and asks which `admin_id` to set up (the default is 1). It never creates new administrator records and never overwrites an existing login.

### 2.4 Typical first session

1. Log in as `ADMIN_01`.
2. **Faculty** → create logins for the advisors of the clubs you want to test. For example, faculty 8 (Bijoy Chand Chatterjee) advises Music Club, which Aanvi Sharma (student 1) belongs to.
3. **Students** → create or reuse `STUDENT_01`.
4. Log in as the student, then submit an application for Music Club.
5. Log in as the faculty advisor and approve it. The status stays **Pending** because only one approval exists.
6. Log in as the admin and approve it. The status becomes **Approved**.

---

## 3. Project structure

```
club_management_system/
│
├── app.py                         ← UPDATED (all routes)
├── setup_admin.py                 ← UPDATED (choose admin_id, env vars)
├── requirements.txt               (Flask, mysql-connector-python)
├── SEproject.sql                  (unchanged — do not re-import)
├── .gitignore                     ← UPDATED (audit.log, .DS_Store)
├── PROJECT_DOCUMENTATION.md       ← NEW (this file)
│
├── static/
│   └── style.css                  ← REWRITTEN (complete stylesheet)
│
├── templates/
│   ├── base.html                  ← NEW  shared layout + role navigation
│   ├── error.html                 ← NEW  400/403/404/500 page
│   ├── login.html                 ← UPDATED
│   │
│   ├── student_dashboard.html     ← UPDATED
│   ├── student_clubs.html         ← NEW
│   ├── student_memberships.html   ← NEW
│   ├── application_form.html      ← NEW
│   ├── student_applications.html  ← NEW
│   │
│   ├── faculty_dashboard.html     ← UPDATED
│   ├── faculty_applications.html  ← NEW
│   │
│   ├── admin_dashboard.html       ← UPDATED
│   ├── admin_students.html        ← UPDATED (CSRF, base layout)
│   ├── admin_faculty.html         ← NEW
│   ├── admin_clubs.html           ← NEW
│   ├── admin_assignments.html     ← NEW
│   ├── admin_applications.html    ← NEW
│   │
│   ├── _application_details.html  ← NEW partial (shared)
│   ├── _decision_form.html        ← NEW partial (shared)
│   └── _status_filter.html        ← NEW partial (shared)
│
└── dev_tests/                     ← NEW (optional, see section 11)
    ├── README.md
    ├── build_db.py
    ├── run_tests.py
    └── mysql/connector/__init__.py
```

`audit.log` is created automatically the first time the app runs.

### 3.1 How `app.py` is organised

| Section | Contents |
|---------|----------|
| 1 | Imports, Flask configuration, validation constants |
| 2 | `get_db_connection()` |
| 3 | Password hashing, `validate_password()`, `validate_new_credentials()`, `get_decisions_by_application()`, template date and money filters |
| 4 | Audit logging (`audit()`) |
| 5 | CSRF protection (`get_csrf_token()`, `csrf_protect()`) |
| 6 | Access control (`login_required`, `role_required`, `session_user_is_active()`) |
| 7 | `/`, `/login`, `/logout` |
| 8 | Student routes |
| 9 | Faculty routes |
| 10 | `update_application_status()`, the approval rule |
| 11 | Admin routes |
| 12 | Error handlers |
| 13 | `app.run()` |

---

## 4. How the pieces communicate

```
 Browser (HTML form / link)
        │  HTTP GET or POST  (form fields + session cookie)
        ▼
 Flask route in app.py
        │  1. before_request: CSRF check on POST
        │  2. @login_required: is there a session? is the user still Active?
        │  3. @role_required: does session["role"] match?
        │  4. validate request.form / request.args
        │  5. parameterised SQL through mysql-connector
        ▼
 MySQL (sau_club_management)
        │  rows returned as Python dictionaries
        ▼
 Flask: render_template("page.html", data=...)  or  flash(...) + redirect(...)
        │
        ▼
 Jinja2 template → HTML → Browser
```

### 4.1 Frontend → backend

- **Links and GET forms** (search and filters) put values in the URL, for example `/admin/students?search=aanvi&login_status=created`. Flask reads them with `request.args.get(...)`.
- **POST forms** (anything that changes data) send fields in the request body. Flask reads them with `request.form.get(...)`. The `name="..."` attribute of each input must match the key used in `app.py`.
- `url_for('route_function_name', id=...)` in templates generates the correct URL, so renaming a URL never breaks links.

### 4.2 Backend → MySQL

Every route follows the same pattern:

```python
connection = get_db_connection()
cursor = connection.cursor(dictionary=True)   # rows become dicts: row["club_name"]
try:
    cursor.execute("SELECT ... WHERE id = %s", (some_id,))   # parameterised
    rows = cursor.fetchall()
    ...
    connection.commit()          # only for INSERT/UPDATE/DELETE
except Error:
    connection.rollback()        # undo a half-finished change
finally:
    cursor.close()
    connection.close()           # always release the connection
```

`%s` is a placeholder. mysql-connector sends the value separately from the SQL text, so user input can never change the structure of the query (this prevents SQL injection). No query in the project builds SQL by pasting user input into the string.

### 4.3 Post/Redirect/Get

After every successful or failed POST, the route calls `flash(message, category)` and then `redirect(...)` to a GET page. This means refreshing the browser never resubmits a form, and the message is displayed once on the next page by `base.html`.

### 4.4 Template inheritance

Every page `extends "base.html"`. The base template provides:

- the top navigation bar, built from `session.role`, so each role sees only its own links;
- the signed-in user's name and a **Sign Out** POST button;
- flash messages, coloured by category (`success` green, `error` red);
- a `content` block that each page fills.

Three small partials (`_application_details.html`, `_decision_form.html`, `_status_filter.html`) are shared by the student, faculty and admin application pages, so the same HTML is not written three times.

---

## 5. Authentication and sessions

### 5.1 Login (`POST /login`)

1. Read `username` and `password` from the form, and reject the request if either is empty.
2. `SELECT * FROM User_Accounts WHERE username = %s`.
3. `check_password_hash(stored_hash, password)`. The same "Invalid username or password" message is shown for an unknown user and for a wrong password, so an attacker cannot discover which usernames exist.
4. Decide the role from whichever foreign key is set: `student_id` means student, `faculty_id` means faculty, `admin_id` means admin.
5. Check `account_status` in that role's own table (`Students`, `Faculty_Advisors` or `Admin_Representatives`). If it is not Active, the login is blocked with "Your account is inactive".
6. `session.clear()`, then store `account_id`, `user_id`, `role`, `username` and `display_name`.
7. Redirect to `/`, which forwards to the correct dashboard for the role.

> **Note on username case:** the table uses MySQL's case-insensitive collation (`utf8mb4_0900_ai_ci`), so `student_01` and `STUDENT_01` are the same username. The UNIQUE constraint therefore also blocks usernames that differ only in case.

### 5.2 Session

The Flask session is a cookie signed with `app.secret_key`. The user can read it but cannot alter it without the key. Settings:

| Setting | Value | Why |
|---------|-------|-----|
| `PERMANENT_SESSION_LIFETIME` | 2 hours | The user must log in again after two hours. |
| `SESSION_COOKIE_HTTPONLY` | True | JavaScript cannot read the cookie. |
| `SESSION_COOKIE_SAMESITE` | Lax | The cookie is not sent with cross-site POSTs. |

### 5.3 Logout

`POST /logout` clears the whole session. It is a POST rather than a link so that another site cannot log you out with an `<img src="/logout">` tag. It also carries a CSRF token.

### 5.4 Immediate effect of deactivation (new)

`login_required` now calls `session_user_is_active()` on every protected request. If an administrator deactivates a student or faculty member, that user's very next click signs them out with "Your account is inactive". Before this change they kept access until the session expired.

---

## 6. Role-based access control

Every protected route carries two decorators:

```python
@app.route("/admin/clubs")
@login_required            # 1st check: logged in AND still Active
@role_required("admin")    # 2nd check: session["role"] == "admin"
def manage_clubs():
```

A decorator is a function that wraps another function. `login_required` runs first and redirects to `/login` if there is no session. `role_required("admin")` then calls `abort(403)` if the role is wrong, which shows the shared "Access denied" page.

Hiding links in the navigation bar is only a convenience. The decorators are the real protection, so typing an admin URL as a student still returns 403. This was verified by the tests.

Some routes also check **ownership** inside the route:

- **Faculty decisions:** the faculty member must be the *current active advisor* of the club the application belongs to.
- **Student applications:** the student must be an *active member* of an *active* club.
- **Student pages:** every query is filtered by `session["user_id"]`, so a student only ever sees their own memberships and applications.

---

## 7. Module-by-module description

### 7.1 Student

| Page | What it does |
|------|--------------|
| **Dashboard** | Shows name, department, program; counts of active memberships, pending applications and clubs led as president; lists of the student's clubs and their five most recent applications. |
| **Clubs** | Card grid of active clubs with member counts. Shows **Join Club** for clubs the student has not joined, and a "You are a member" badge otherwise. |
| **Join (POST)** | Checks the club is active and the student is not already a member, then inserts a row into `Memberships` with today's date and status Active. |
| **My Memberships** | Table of every membership, with a shortcut to apply for an event in that club. |
| **New Application** | Form for title, description, start and end times, venue, purpose and optional funding. The funding fields are shown only when the checkbox is ticked. |
| **My Applications** | Each application with its status badge and expandable details, including every reviewer's decision and comment. |

**Server-side validation on submit:** all required fields are present; the title and venue are at most 150 characters (the column sizes); start and end are valid date-times; end is after start; start is in the future; if funding is requested, the amount is above 0 and below the `DECIMAL(12,2)` limit and a purpose is given; the student is an active member of the selected active club. When funding is not requested, the amount and purpose are stored as `NULL`, which the table's CHECK constraint requires.

### 7.2 Faculty

| Page | What it does |
|------|--------------|
| **Dashboard** | Clubs advised (with member count and current president), number of pending applications, and up to five pending applications still awaiting *this* faculty member's decision. |
| **Review Applications** | Applications for the clubs the faculty member currently advises, filterable by All, Pending, Approved or Rejected. Each card shows the event details, all reviewer decisions, and an Approve/Reject form with optional comments. Submitting again replaces the faculty member's earlier decision. |

### 7.3 Administrator

| Page | What it does |
|------|--------------|
| **Dashboard** | Six statistics (students, faculty, clubs, active memberships, login accounts, pending applications), shortcut cards to each area, and the five oldest pending applications. |
| **Students** | Unchanged in behaviour from the previous version: search, filters, create account, reset password, change status. CSRF tokens and a confirmation prompt before deactivation have been added. |
| **Faculty** *(new features)* | The same layout as Students: summary cards, search, filters, **create faculty login**, **reset faculty password**, change status, and a "Clubs Advised" column. |
| **Clubs** | Create a club; table of all clubs with status, member count, president and advisor; inline **Edit** (name and status); **Delete** with a confirmation prompt. Duplicate names (case-insensitive) are rejected. A club with members, applications or advisor history cannot be deleted because of foreign keys, and the page suggests marking it Inactive instead. |
| **Assignments** *(new page)* | One row per club showing the current president and advisor. The president drop-down lists only that club's active members. The advisor drop-down lists active faculty. |
| **Applications** | All applications, filterable by status, with the same details and decision form as the faculty view. |

**Assignment rules:** the club must be Active. A president must be an active member with an Active student record. An advisor must be an Active faculty member. Reassigning the current holder is rejected. A new assignment *ends* the previous one (`end_date = today`, `assignment_status = 'Inactive'`) rather than deleting it, so the history is kept. Both statements run in one transaction.

### 7.4 Application approval rule

This rule is unchanged from the original project and is applied in `update_application_status()`:

| Decisions recorded in `Approval_Decisions` | Resulting `application_status` |
|--------------------------------------------|--------------------------------|
| any decision = Rejected | **Rejected** |
| 2 or more decisions = Approved, none Rejected | **Approved** |
| otherwise | **Pending** |

Each reviewer has at most one row per application. This is enforced by the UNIQUE keys `(application_id, faculty_id)` and `(application_id, admin_id)`, and the `INSERT ... ON DUPLICATE KEY UPDATE` statement updates the existing row. A reviewer can therefore change their mind, and the status is recalculated each time. The decision insert and the status update run in one transaction.

---

## 8. Complete route reference

| Method | URL | Function | Role |
|--------|-----|----------|------|
| GET | `/` | `home` | any (redirects by role) |
| GET, POST | `/login` | `login` | public |
| POST | `/logout` | `logout` | logged in |
| GET | `/student/dashboard` | `student_dashboard` | student |
| GET | `/student/clubs` | `view_clubs` | student |
| POST | `/student/clubs/<club_id>/join` | `join_club` | student |
| GET | `/student/memberships` | `view_memberships` | student |
| GET, POST | `/student/applications/new` | `submit_application` | student |
| GET | `/student/applications` | `view_applications` | student |
| GET | `/faculty/dashboard` | `faculty_dashboard` | faculty |
| GET | `/faculty/applications` | `faculty_applications` | faculty |
| POST | `/faculty/applications/<id>/decision` | `faculty_decision` | faculty |
| GET | `/admin/dashboard` | `admin_dashboard` | admin |
| GET, POST | `/admin/clubs` | `manage_clubs` | admin |
| POST | `/admin/clubs/<club_id>/edit` | `edit_club` | admin |
| POST | `/admin/clubs/<club_id>/delete` | `delete_club` | admin |
| GET | `/admin/students` | `manage_students` | admin |
| POST | `/admin/students/<id>/create-account` | `create_student_account` | admin |
| POST | `/admin/students/<id>/reset-password` | `reset_student_password` | admin |
| POST | `/admin/students/<id>/status` | `update_student_status` | admin |
| GET | `/admin/faculty` | `manage_faculty` | admin |
| POST | `/admin/faculty/<id>/create-account` | `create_faculty_account` **(new)** | admin |
| POST | `/admin/faculty/<id>/reset-password` | `reset_faculty_password` **(new)** | admin |
| POST | `/admin/faculty/<id>/status` | `update_faculty_status` | admin |
| GET | `/admin/assignments` | `manage_assignments` **(new)** | admin |
| POST | `/admin/presidents/assign` | `assign_president` | admin |
| POST | `/admin/advisors/assign` | `assign_advisor` | admin |
| GET | `/admin/applications` | `admin_applications` | admin |
| POST | `/admin/applications/<id>/decision` | `admin_decision` | admin |

No existing route was renamed or removed.

---

## 9. Security decisions

| Measure | Where | Explanation |
|---------|-------|-------------|
| **Password hashing** | `hash_password()` | Werkzeug `pbkdf2:sha256` with a random salt. Only the hash is stored, never the password. |
| **Minimum 12-character password** | `validate_password()`, `setup_admin.py` | Length is the most effective single password rule. |
| **No public registration** | `login.html` | Only administrators create accounts. The "Sign Up" link was removed. |
| **Generic login error** | `login()` | Does not reveal whether a username exists. |
| **Parameterised SQL everywhere** | all queries | Prevents SQL injection. The only dynamic SQL is the `IN (%s, %s, ...)` list in `get_decisions_by_application()`, which contains placeholders only. |
| **CSRF tokens** *(new)* | `csrf_protect()` + hidden field in every POST form | A random token is stored in the session and must be returned with each POST. Without it the request is rejected with 400. This was implemented in about 20 lines rather than adding Flask-WTF, keeping the dependency list unchanged. |
| **Role decorators on every route** | `login_required`, `role_required` | Server-side enforcement that does not depend on hidden links. |
| **Ownership checks** | faculty decision, student application | Being the right role is not enough; the user must also be linked to the record. |
| **Immediate deactivation** *(new)* | `session_user_is_active()` | A deactivated user is signed out on their next request. |
| **Confirmation prompts** *(new)* | deactivate, delete club, reject | Prevents accidental clicks. A JavaScript `confirm()` is a convenience, not a security control. |
| **Audit log** *(new)* | `audit()` writes to `audit.log` | Records logins (including failed and blocked attempts), account creation, password resets, status changes, club create/edit/delete, assignments and decisions, with account id, role, IP address and time. A text file is used because the schema has no audit table and the rules say not to invent tables. |
| **Escaped output** | Jinja2 auto-escaping | Names and comments are HTML-escaped, so stored text cannot inject scripts. Names used in confirmation prompts go through `data-name` attributes for the same reason. |
| **Secrets from environment** | `MYSQL_PASSWORD`, `FLASK_SECRET_KEY` | No passwords in the source code. |
| **Friendly error pages** | `error.html` + handlers | Users see a clean message. The details are printed to the terminal only. |

---

## 10. Change log against the previous version

### `app.py`

**New**

- CSRF protection (`get_csrf_token`, `csrf_protect`).
- `session_user_is_active()`, called from `login_required`.
- `validate_password()` and `validate_new_credentials()` helpers. The student account routes now use them; their behaviour is unchanged except that **usernames containing spaces are now rejected**.
- An explicit duplicate-username check before insert, giving a clear message. The UNIQUE constraint remains as a safety net.
- Faculty account creation and password reset routes.
- `/admin/assignments` page route.
- `get_decisions_by_application()` helper, used by all three application pages.
- `datetime_display` and `money` Jinja filters.
- Audit logging.
- Error handlers for 400, 403, 404, MySQL errors and a missing `MYSQL_PASSWORD`.
- Optional `MYSQL_HOST`, `MYSQL_USER` and `MYSQL_DATABASE` environment variables.

**Fixed or extended (same route names and URLs)**

- `role_required` now calls `abort(403)` so the styled error page is shown.
- `login` stores `display_name` and `username` in the session, and logs attempts.
- `update_student_status`: checks the record exists *before* updating, fixing the false "not found" message when the status is unchanged.
- `update_faculty_status`: the same existence check, plus error handling.
- `assign_president`: checks the club is active, the student is active, and the student is not already president. Now redirects to the Assignments page.
- `assign_advisor`: checks the club is active, the faculty member exists and is active, and is not already the advisor. Now redirects to the Assignments page.
- `manage_clubs` / `edit_club`: name length and case-insensitive duplicate checks. The club list now includes member count, president and advisor.
- `delete_club`: handles "not found" and general database errors.
- `submit_application`: real date-time parsing, future-date check, length checks, funding upper bound, and a check that the club is active.
- `admin_decision`: checks the application exists.
- `faculty_decision` and `admin_decision`: the flash message now states the resulting status. `update_application_status()` returns the status it set.
- Student, faculty and admin dashboards: extra queries for richer information. The original variables are kept.
- `faculty_applications` and `admin_applications`: status filter.
- All flash messages now carry a category (`success` or `error`).

### Templates and CSS

- New `base.html` layout with role-specific navigation. Every page now extends it.
- Eight missing templates created; three shared partials and `error.html` added.
- All POST forms include `csrf_token`.
- `login.html`: flash messages shown, Sign Up link removed.
- `style.css` rewritten as one complete, organised stylesheet. The colours (`#ed7ba5` / `#df6592`) and the class names used by the Manage Students page are kept. The global `body { display:flex }` that broke page layouts has been removed.

### `setup_admin.py`

- Lists admin records and existing logins; lets you choose the `admin_id`.
- Uses `MYSQL_PASSWORD` if it is set, otherwise prompts for it.
- Validates username length and spaces.

### Database

- **No schema changes and no data changes.** No new tables or columns were invented.

---

## 11. Testing

### 11.1 What was actually tested

MySQL was not available in the development environment used for this update. To test the real application code anyway, a small **stand-in for `mysql.connector`** was written (in `dev_tests/`). It:

- recreates every table from `SEproject.sql` in SQLite, with the same primary keys, foreign keys, UNIQUE keys and CHECK constraints, and loads the same data (106 students, 22 faculty, 10 admins, 10 clubs, 106 memberships, 5 applications, 5 decisions);
- translates the handful of MySQL-specific pieces (`%s` → `?`, `NOW()`, `CAST(... AS CHAR)`, `ON DUPLICATE KEY UPDATE`);
- uses case-insensitive text comparison, matching your MySQL collation.

The unmodified `app.py` and templates were then exercised with Flask's test client. **Result: 112 of 112 checks passed.** The checks cover:

| Area | Checks |
|------|--------|
| Authentication | anonymous redirects; login page renders with no Sign Up link; POST without CSRF token returns 400; wrong password and unknown user rejected with the message displayed; admin, student and faculty logins land on the right dashboard; logout; protected pages redirect after logout |
| Access control | student → admin/faculty pages = 403; faculty → admin = 403; admin → student/faculty pages = 403 |
| Student accounts | short password, mismatched confirmation, username with a space, duplicate username, second account for the same student, nonexistent student and inactive student are all rejected; successful creation; password stored as a `pbkdf2:sha256` hash; summary counts |
| Faculty accounts | creation, duplicate rejection, password reset, "created" filter |
| Student workflow | all student pages load; join club; duplicate join rejected; application validation (end before start, past date, missing funding details, non-member club); successful submission with and without funding; dashboard counts |
| Faculty workflow | dashboard shows the advised club; only the advised clubs' applications are visible; invalid decision rejected; approval leaves the status **Pending**; a non-advisor cannot decide |
| Approval rule | faculty approval + admin approval → **Approved**; admin changes to Rejected → **Rejected**; back to Approved → **Approved**; one row per reviewer is kept; missing application handled; the student sees decisions and comments |
| Deactivation | student deactivated → signed out on the next request → login blocked → memberships and applications unchanged → reactivated → login works; same for faculty; same-status update no longer says "not found"; invalid status rejected |
| Password reset | short password rejected; reset without an account rejected; old password stops working; new password works |
| Clubs | create; case-insensitive duplicate rejected; empty name rejected; rename to an existing name rejected; edit persists; inactive club hidden from students; delete a club with no records; delete a club with records blocked; delete a missing club handled |
| Assignments | page lists current presidents; non-member president rejected; president assigned with the previous one ended; same president rejected; bad ID rejected; student dashboard shows the president role; advisor assigned; same advisor rejected; old advisor loses access and new advisor gains it; inactive faculty rejected |
| Errors | 404 page; missing `MYSQL_PASSWORD` gives a friendly page; audit log contains the expected events |

All main pages were also rendered in headless Chrome at desktop (1300 px) and mobile (390 px) widths and inspected visually.

To re-run the tests yourself (no MySQL needed):

```bash
python dev_tests/run_tests.py .
```

Run this from the project folder. It uses a temporary SQLite file and never touches your MySQL database. It does append test entries to `audit.log`, so delete that file afterwards if you want a clean log.

### 11.2 What has NOT been tested yet

The code has **not yet been run against your real MySQL server**. The SQLite stand-in is faithful for these queries, but it is not MySQL. Please run this checklist once on your machine:

| # | Step | Expected |
|---|------|----------|
| 1 | Start the app, log in as `ADMIN_01` | Admin dashboard, 6 statistic cards |
| 2 | Visit each admin menu item | Every page loads (no 500 error) |
| 3 | Faculty → create login for faculty 8 | "Faculty login account created" |
| 4 | Log out, log in as the faculty user | Faculty dashboard lists Music Club |
| 5 | Log in as `STUDENT_01`, visit every student menu item | All pages load |
| 6 | Join a new club | Success message, club shows "You are a member" |
| 7 | Submit an application for Music Club with funding | Appears as Pending |
| 8 | Faculty 8 approves it | Status still Pending |
| 9 | Admin approves it | Status Approved |
| 10 | Admin deactivates `STUDENT_01` while the student is logged in (in another browser) | Student's next click → login page, "inactive" message |
| 11 | Student tries to log in | Blocked |
| 12 | Admin reactivates, student logs in | Works |
| 13 | Admin → Assignments → assign a new president for any club | Success; the Clubs page shows the new name |
| 14 | Admin → Clubs → create "Test Club", then delete it | Both succeed |
| 15 | Admin → Clubs → delete "Anime club" | Blocked with the "related records" message |
| 16 | Open `audit.log` | Entries for all of the above |

If any step fails, copy the terminal output (the error is printed there) and we can debug that specific error.

---

## 12. Known limitations and future work

| Item | Notes |
|------|-------|
| **Table-name case on Linux** | `app.py` uses `Students`, `Clubs` and so on, while the dump created lowercase tables. This works on Windows and macOS, where MySQL table names are case-insensitive by default. On a **Linux** MySQL server (`lower_case_table_names=0`) the queries would fail. If the project is ever deployed on Linux, either set `lower_case_table_names=1` before initialising MySQL or change the table names in the queries to lowercase. |
| **Leaving a club** | There is no "leave club" feature, and `join_club` will not reactivate an Inactive membership. This was left as it was because the original code did not support it. |
| **Admin account management in the UI** | Administrator logins are created only through `setup_admin.py`, as agreed. There is no page to deactivate an admin. |
| **Self-service password change** | Users cannot change their own password; an administrator resets it. A "change my password" page would be a sensible next feature. |
| **Login rate limiting** | Failed logins are logged but not throttled. |
| **Production deployment** | `app.run(debug=True)` is for development only. For a real deployment: set `FLASK_SECRET_KEY`, turn debug off, serve over HTTPS and set `SESSION_COOKIE_SECURE = True`. |
| **Pagination** | The student table shows all 106 rows. This is fine at the current size; pagination would be needed for thousands of rows. |
