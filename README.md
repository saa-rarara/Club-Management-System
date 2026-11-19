# SAU Club Management System

A web application for managing student clubs at **South Asian University (SAU)**. It covers club memberships, event and funding applications, a two-step approval workflow, and administrator-controlled accounts for students, faculty advisors and administrators.

Built with **Python, Flask and MySQL** as a university Software Engineering project.

---

## Features

### Student
- Browse active clubs and join them
- View memberships, and clubs where you are president
- Submit event applications, with optional funding requests
- Track application status and read reviewer comments

### Faculty advisor
- See the clubs you advise, with member counts and presidents
- Review applications for your clubs: approve or reject, with comments
- Filter applications by Pending, Approved or Rejected

### Administrator
- Create login accounts for existing students and faculty (there is no public sign-up)
- Reset passwords and activate or deactivate users
- Create, edit, deactivate and delete clubs
- Assign club presidents and faculty advisors, keeping the assignment history
- Review all applications

### Approval rule
| Decisions on an application | Status |
|---|---|
| Any reviewer rejects | **Rejected** |
| Two or more approve (advisor + admin), none reject | **Approved** |
| Otherwise | **Pending** |

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ (tested on 3.13), Flask 3.1 |
| Database | MySQL 8.0 or 8.4 |
| DB driver | mysql-connector-python |
| Frontend | HTML, CSS, Jinja2 templates |
| Authentication | Flask sessions |
| Password hashing | Werkzeug (`pbkdf2:sha256`) |

---

## Project structure

```
club_management_system/
├── app.py                     # Flask app: all routes, auth, DB access
├── setup_admin.py             # One-time script to create an admin login
├── SEproject.sql              # Database schema + seed data
├── requirements.txt           # Flask, mysql-connector-python
├── README.md
├── PROJECT_DOCUMENTATION.md   # Detailed implementation + testing record
├── static/
│   └── style.css              # Pink-and-white theme
├── templates/
│   ├── base.html              # Shared layout + role-based navigation
│   ├── login.html, error.html
│   ├── student_*.html, application_form.html
│   ├── faculty_*.html
│   ├── admin_*.html
│   └── _*.html                # Shared partials
└── dev_tests/                 # Optional automated tests (no MySQL needed)
```

---

## Prerequisites

- **Python 3.11 or newer**, from python.org or Anaconda
- **MySQL Community Server 8.0 or newer**, with a known root password
- A modern browser

---

## Installation

### 1. Get the code
Unzip the project and open a terminal in the folder that contains `app.py`.

### 2. Create a Python environment and install the dependencies

**Anaconda (macOS / Windows):**
```bash
conda create -n sauclubs python=3.12 -y
conda activate sauclubs
pip install -r requirements.txt
```

**venv, macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**venv, Windows PowerShell:**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Create the database

> Do this **only once**. `SEproject.sql` drops and recreates every table, so re-importing it deletes all accounts you have created.

**macOS / Linux:**
```bash
mysql -u root -p -e "CREATE DATABASE sau_club_management;"
mysql -u root -p sau_club_management < SEproject.sql
```

**Windows PowerShell** (`<` does not work in PowerShell):
```powershell
mysql -u root -p -e "CREATE DATABASE sau_club_management;"
Get-Content SEproject.sql | mysql -u root -p sau_club_management
```

You can also use MySQL Workbench: **Server → Data Import → Import from Self-Contained File**, with `sau_club_management` as the target schema.

Check the import worked: `SELECT COUNT(*) FROM students;` should return **106**.

### 4. Configure environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `MYSQL_PASSWORD` | **Yes** | — | MySQL password |
| `MYSQL_HOST` | No | `localhost` | MySQL host |
| `MYSQL_USER` | No | `root` | MySQL user |
| `MYSQL_DATABASE` | No | `sau_club_management` | Database name |
| `FLASK_SECRET_KEY` | Recommended | development key | Signs session cookies |

**macOS / Linux:**
```bash
export MYSQL_PASSWORD='your-mysql-password'
export FLASK_SECRET_KEY='any-long-random-text'
```

**Windows PowerShell:**
```powershell
$env:MYSQL_PASSWORD = 'your-mysql-password'
$env:FLASK_SECRET_KEY = 'any-long-random-text'
```

**Anaconda (set once, kept in the environment):**
```bash
conda env config vars set MYSQL_PASSWORD='your-mysql-password'
conda deactivate && conda activate sauclubs
```

Use **single quotes** so that characters such as `$` in the password are not changed by the shell.

### 5. Create the first administrator login
The imported `User_Accounts` table is empty, so nobody can log in until you run:
```bash
python setup_admin.py
```
Choose an admin ID (the default is 1), a username such as `ADMIN_01`, and a password of at least **12 characters**. You can run the script again later to give other administrators a login.

---

## Running the application

**macOS:** use port 5001, because AirPlay Receiver occupies port 5000.
```bash
flask --app app run --debug --port 5001
```
Then open **http://127.0.0.1:5001**.

**Windows / Linux:**
```bash
python app.py
```
Then open **http://127.0.0.1:5000**.

Stop the server with **Ctrl + C**.

---

## Getting started

1. Log in as the administrator.
2. **Faculty →** create a login for a club's advisor. For example, faculty 8 advises Music Club.
3. **Students →** create a login for a member of that club. For example, student 1 belongs to Music Club.
4. As the student: **New Application →** submit an event. Its status is **Pending**.
5. As the faculty advisor: **Review Applications →** approve it. The status stays **Pending** (one approval).
6. As the admin: **Applications →** approve it. The status becomes **Approved**.

---

## Testing

An optional automated suite runs all three roles end to end. It uses a SQLite stand-in for MySQL, so it **never touches your real database**:
```bash
python dev_tests/run_tests.py .
```
Expected output: `112/112 checks passed`. The run adds entries to `audit.log`; delete that file afterwards if you want a clean log.

A manual checklist for testing against MySQL is in `PROJECT_DOCUMENTATION.md`, section 11.2.

---

## Security

- Passwords are stored only as salted `pbkdf2:sha256` hashes, with a 12-character minimum
- Every query is parameterised, preventing SQL injection
- Every form carries a CSRF token
- Role and ownership checks run on the server for every route
- A deactivated user is signed out on their next request
- Session cookies are HttpOnly and SameSite=Lax, and expire after 2 hours
- Logins, account changes and decisions are written to `audit.log`
- Secrets come from environment variables, never from source code

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Page says "Database not configured" | Set `MYSQL_PASSWORD` in the same terminal, then restart the app |
| `1045 Access denied for user 'root'` | The MySQL password is wrong |
| `2003` / `2002 Can't connect to MySQL server` | Start MySQL (System Settings → MySQL on macOS; Services → MySQL80 on Windows) |
| `1049 Unknown database` | Create and import the database (step 3) |
| `No module named 'flask'` or `'mysql'` | Activate the environment; in VS Code, run **Python: Select Interpreter** |
| "Invalid username or password" for the admin | Run `python setup_admin.py` |
| macOS: "403 Forbidden" / "Address already in use" | Use `--port 5001`, or turn off AirPlay Receiver |
| "Request could not be processed" (400) | The form expired; refresh the page and submit again |
| Linux: `Table '...Students' doesn't exist` | Set `lower_case_table_names=1` in MySQL, because the code uses mixed-case table names |

---

## Documentation

- **`PROJECT_DOCUMENTATION.md`:** architecture, every route, security decisions, change log and test results
- **Software Requirements Specification (SRS):** functional and non-functional requirements, data model, use cases and traceability

---

## Known limitations

- Users cannot change their own password; an administrator resets it
- There is no "leave club" feature and no email notifications
- `debug=True` is for development only. Before deploying, turn debug off, set `FLASK_SECRET_KEY`, and serve over HTTPS.

---

*South Asian University, Software Engineering Project, November 2026*

## Team Members
1. Aditya Adhikari
2. Achyut Krishna Sharma
3. Arnav Mishra
4. Saara Ahmed
5. Suyash Singh Gusain
6. Tarini Parashar 
