# Optional automated tests. Uses a SQLite stand-in for MySQL; never touches your real database.
# Usage (from the project folder):  python dev_tests/run_tests.py .
import os, re, sys, shutil, subprocess
HARNESS = os.path.dirname(os.path.abspath(__file__))
APP_DIR = sys.argv[1]
import tempfile
DB = os.path.join(tempfile.gettempdir(), "sau_club_test.db")
if os.path.exists(DB): os.remove(DB)
subprocess.run([sys.executable, os.path.join(HARNESS,"build_db.py"), os.path.join(APP_DIR,"SEproject.sql"), DB], check=True, capture_output=True)
os.environ["FAKE_DB_PATH"] = DB
os.environ["MYSQL_PASSWORD"] = "test"
sys.path.insert(0, HARNESS); sys.path.insert(1, APP_DIR)
import sqlite3
from werkzeug.security import generate_password_hash
import app as appmod
app = appmod.app
app.config["TESTING"] = True

results = []
def check(name, cond, extra=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if (extra and not cond) else ""))

def db(q, p=()):
    c = sqlite3.connect(DB); r = c.execute(q, p).fetchall(); c.commit(); c.close(); return r

# Simulate setup_admin.py: initial admin account
db("INSERT INTO user_accounts (admin_id, username, password_hash) VALUES (1,'ADMIN_01',?)", (generate_password_hash("AdminPassword123", method="pbkdf2:sha256"),))

def token(client, url="/login"):
    html = client.get(url).get_data(as_text=True)
    m = re.search(r'name="csrf_token" value="([0-9a-f]+)"', html)
    return m.group(1) if m else None

def login(client, u, p):
    t = token(client, "/login")
    return client.post("/login", data={"username": u, "password": p, "csrf_token": t}, follow_redirects=True)

def post(client, url, data, page="/"):
    t = token(client, page)
    d = dict(data); d["csrf_token"] = t
    return client.post(url, data=d, follow_redirects=True)

def text(r): return r.get_data(as_text=True)

# ---------- Authentication ----------
c = app.test_client()
r = c.get("/"); check("anon / redirects to login", r.status_code == 302 and "/login" in r.headers["Location"])
r = c.get("/login"); check("login page renders", r.status_code == 200 and "Sign In" in text(r))
check("no public Sign Up link", "Sign Up" not in text(r))
r = c.get("/admin/dashboard"); check("protected page redirects anon", r.status_code == 302)
r = c.post("/login", data={"username":"ADMIN_01","password":"AdminPassword123"}); check("POST without CSRF token -> 400", r.status_code == 400)
r = login(c, "ADMIN_01", "wrongpassword"); check("wrong password rejected + message shown", "Invalid username or password" in text(r))
r = login(c, "nobody", "whatever12345"); check("unknown user rejected", "Invalid username or password" in text(r))
r = login(c, "ADMIN_01", "AdminPassword123"); check("admin login -> admin dashboard", r.status_code == 200 and "Admin Dashboard" in text(r))
check("admin dashboard shows 106 students", ">106<" in text(r))
check("nav shows admin name", "Navneet Jha" in text(r))
for url in ["/admin/students","/admin/faculty","/admin/clubs","/admin/assignments","/admin/applications","/admin/applications?status=Pending","/admin/applications?status=bogus",
            "/admin/students?search=Aanvi","/admin/students?login_status=not_created&student_status=Active","/admin/students?search=1&login_status=created","/admin/faculty?search=Sandeep&faculty_status=Active"]:
    r = c.get(url); check(f"admin GET {url} -> 200", r.status_code == 200, r.status_code)
r = c.get("/student/dashboard"); check("admin blocked from student dashboard (403)", r.status_code == 403)
r = c.get("/faculty/applications"); check("admin blocked from faculty pages (403)", r.status_code == 403)
r = c.get("/student/clubs"); check("403 page uses template", "Access denied" in text(r))

# ---------- Student account creation ----------
P = "/admin/students"
r = post(c, "/admin/students/1/create-account", {"username":"STUDENT_01","password":"short","confirm_password":"short"}, P); check("short password rejected", "at least 12" in text(r))
r = post(c, "/admin/students/1/create-account", {"username":"STUDENT_01","password":"StudentPass123","confirm_password":"StudentPass124"}, P); check("mismatched confirm rejected", "do not match" in text(r))
r = post(c, "/admin/students/1/create-account", {"username":"STUDENT 01","password":"StudentPass123","confirm_password":"StudentPass123"}, P); check("username with space rejected", "cannot contain spaces" in text(r))
r = post(c, "/admin/students/1/create-account", {"username":"ADMIN_01","password":"StudentPass123","confirm_password":"StudentPass123"}, P); check("duplicate username rejected", "already in use" in text(r))
r = post(c, "/admin/students/1/create-account", {"username":"STUDENT_01","password":"StudentPass123","confirm_password":"StudentPass123"}, P); check("student account created", "created successfully" in text(r))
row = db("select password_hash from user_accounts where student_id=1")
check("password stored as hash", row and row[0][0].startswith("pbkdf2:sha256") and "StudentPass123" not in row[0][0])
r = post(c, "/admin/students/1/create-account", {"username":"STUDENT_01b","password":"StudentPass123","confirm_password":"StudentPass123"}, P); check("second account for same student rejected", "already has a login account" in text(r))
r = post(c, "/admin/students/9999/create-account", {"username":"X_1","password":"StudentPass123","confirm_password":"StudentPass123"}, P); check("nonexistent student rejected", "not found" in text(r))
r = c.get("/admin/students"); check("summary 1 created / 105 not", ">105<" in text(r) and ">1<" in text(r))
db("UPDATE students SET account_status='Inactive' WHERE student_id=50")
r = post(c, "/admin/students/50/create-account", {"username":"S50","password":"StudentPass123","confirm_password":"StudentPass123"}, P); check("inactive student cannot get account", "inactive student" in text(r))
db("UPDATE students SET account_status='Active' WHERE student_id=50")
post(c, "/admin/students/2/create-account", {"username":"STUDENT_02","password":"StudentPass123","confirm_password":"StudentPass123"}, P)

# ---------- Faculty accounts ----------
F = "/admin/faculty"
r = post(c, "/admin/faculty/8/create-account", {"username":"FACULTY_08","password":"FacultyPass123","confirm_password":"FacultyPass123"}, F); check("faculty account created", "Faculty login account created" in text(r))
r = post(c, "/admin/faculty/8/create-account", {"username":"FACULTY_08b","password":"FacultyPass123","confirm_password":"FacultyPass123"}, F); check("duplicate faculty account rejected", "already has a login account" in text(r))
post(c, "/admin/faculty/12/create-account", {"username":"FACULTY_12","password":"FacultyPass123","confirm_password":"FacultyPass123"}, F)
r = post(c, "/admin/faculty/12/reset-password", {"password":"FacultyNewPass1","confirm_password":"FacultyNewPass1"}, F); check("faculty password reset", "reset successfully" in text(r))
r = c.get("/admin/faculty?login_status=created"); check("faculty filter 'created' shows 2", text(r).count("account-created") == 2)

r = post(c, "/logout", {}, "/admin/dashboard"); check("logout works", "signed out" in text(r))
r = c.get("/admin/dashboard"); check("after logout protected page redirects", r.status_code == 302)

# ---------- Student workflow ----------
s = app.test_client()
r = login(s, "student_01", "StudentPass123"); check("student login (case-insensitive username like MySQL) -> student dashboard", "Welcome, Aanvi Sharma" in text(r))
for url in ["/student/clubs","/student/memberships","/student/applications/new","/student/applications","/student/applications/new?club_id=3"]:
    r = s.get(url); check(f"student GET {url} -> 200", r.status_code == 200, r.status_code)
r = s.get("/admin/students"); check("student blocked from admin (403)", r.status_code == 403)
r = s.get("/faculty/dashboard"); check("student blocked from faculty (403)", r.status_code == 403)
r = post(s, "/student/clubs/5/join", {}, "/student/clubs"); check("student joins club", "successfully joined" in text(r))
r = post(s, "/student/clubs/5/join", {}, "/student/clubs"); check("duplicate join rejected", "already a member" in text(r))
A = "/student/applications/new"
base = {"club_id":"3","title":"Spring Jam","description":"Live music","proposed_start":"2030-03-01T10:00","proposed_end":"2030-03-01T15:00","requested_venue":"OAT","event_purpose":"Fun"}
r = post(s, A, dict(base, proposed_end="2030-03-01T09:00"), A); check("end before start rejected", "end must be after" in text(r))
r = post(s, A, dict(base, proposed_start="2020-03-01T10:00", proposed_end="2020-03-01T12:00"), A); check("past start rejected", "must be in the future" in text(r))
r = post(s, A, dict(base, funding_required="yes"), A); check("funding without amount rejected", "funding amount and purpose" in text(r))
r = post(s, A, dict(base, club_id="9"), A); check("application for non-member club rejected", "active club member" in text(r))
r = post(s, A, dict(base, funding_required="yes", requested_amount="5000", funding_purpose="Sound"), A); check("application submitted", "submitted successfully" in text(r))
new_app = db("select application_id, application_status, requested_amount from applications order by application_id desc limit 1")[0]
check("new application Pending in DB", new_app[1] == "Pending" and new_app[2] == 5000.0)
APP_ID = new_app[0]
r = post(s, A, base, A); check("application without funding submitted", "submitted successfully" in text(r))
r = s.get("/student/dashboard"); check("dashboard shows 2 memberships & pending count", ">2<" in text(r) and "Spring Jam" in text(r))

# ---------- Faculty workflow ----------
f = app.test_client()
r = login(f, "FACULTY_08", "FacultyPass123"); check("faculty login -> faculty dashboard", "Welcome, Bijoy Chand Chatterjee" in text(r) and "Music Club" in text(r))
r = f.get("/faculty/applications"); check("faculty sees club 3 applications", r.status_code == 200 and "Spring Jam" in text(r) and "Battle of Bands" in text(r))
r = f.get("/admin/dashboard"); check("faculty blocked from admin (403)", r.status_code == 403)
r = post(f, f"/faculty/applications/{APP_ID}/decision", {"decision":"Maybe"}, "/faculty/applications"); check("invalid decision rejected", "Invalid decision" in text(r))
r = post(f, f"/faculty/applications/{APP_ID}/decision", {"decision":"Approved","comments":"Looks good"}, "/faculty/applications"); check("faculty approves -> still Pending (1 approval)", "now Pending" in text(r))
f12 = app.test_client(); login(f12, "FACULTY_12", "FacultyNewPass1")
r = post(f12, f"/faculty/applications/{APP_ID}/decision", {"decision":"Approved"}, "/faculty/applications"); check("non-advisor faculty cannot decide", "not authorised" in text(r))
r = f12.get("/faculty/applications"); check("faculty 12 does not see club 3 apps", "Spring Jam" not in text(r))

# ---------- Admin decision ----------
login(c, "ADMIN_01", "AdminPassword123")
r = post(c, f"/admin/applications/{APP_ID}/decision", {"decision":"Approved","comments":"OK"}, "/admin/applications"); check("admin approval -> Approved (2 approvals)", "now Approved" in text(r))
r = post(c, f"/admin/applications/{APP_ID}/decision", {"decision":"Rejected","comments":"Budget"}, "/admin/applications"); check("admin changes to Rejected -> Rejected", "now Rejected" in text(r))
check("decision upsert kept one admin row", db("select count(*) from approval_decisions where application_id=? and admin_id=1",(APP_ID,))[0][0] == 1)
r = post(c, f"/admin/applications/{APP_ID}/decision", {"decision":"Approved"}, "/admin/applications"); check("admin back to Approved -> Approved", "now Approved" in text(r))
r = post(c, "/admin/applications/99999/decision", {"decision":"Approved"}, "/admin/applications"); check("decision on missing application handled", "not found" in text(r))
r = s.get("/student/applications"); check("student sees Approved + reviewer comment", "Approved" in text(r) and "Looks good" in text(r) and "Bijoy" in text(r))

# ---------- Deactivation / reactivation ----------
r = post(c, "/admin/students/1/status", {"account_status":"Inactive"}, "/admin/students"); check("student deactivated", "status updated" in text(r))
r = post(c, "/admin/students/1/status", {"account_status":"Inactive"}, "/admin/students"); check("same-status update not reported as 'not found'", "status updated" in text(r))
r = s.get("/student/dashboard", follow_redirects=True); check("logged-in student signed out after deactivation", "Login" in text(r) and "inactive" in text(r))
r = login(s, "STUDENT_01", "StudentPass123"); check("inactive student login blocked", "inactive" in text(r) and "Welcome" not in text(r))
check("memberships/applications unchanged after deactivation", db("select count(*) from memberships where student_id=1")[0][0] == 2 and db("select count(*) from applications where student_id=1")[0][0] == 3)
r = post(c, "/admin/students/1/status", {"account_status":"Bogus"}, "/admin/students"); check("invalid status rejected", "Invalid account status" in text(r))
post(c, "/admin/students/1/status", {"account_status":"Active"}, "/admin/students")
r = login(s, "STUDENT_01", "StudentPass123"); check("reactivated student can log in", "Welcome, Aanvi Sharma" in text(r))

# ---------- Password reset ----------
r = post(c, "/admin/students/1/reset-password", {"password":"short","confirm_password":"short"}, "/admin/students"); check("short reset password rejected", "at least 12" in text(r))
r = post(c, "/admin/students/3/reset-password", {"password":"StudentPass999","confirm_password":"StudentPass999"}, "/admin/students"); check("reset without account rejected", "No login account" in text(r))
r = post(c, "/admin/students/1/reset-password", {"password":"BrandNewPass99","confirm_password":"BrandNewPass99"}, "/admin/students"); check("student password reset", "reset successfully" in text(r))
s2 = app.test_client()
r = login(s2, "STUDENT_01", "StudentPass123"); check("old password no longer works", "Invalid username" in text(r))
r = login(s2, "STUDENT_01", "BrandNewPass99"); check("new password works", "Welcome, Aanvi" in text(r))

# ---------- Faculty status ----------
r = post(c, "/admin/faculty/12/status", {"account_status":"Inactive"}, "/admin/faculty"); check("faculty deactivated", "status updated" in text(r))
r = f12.get("/faculty/dashboard", follow_redirects=True); check("deactivated faculty signed out", "inactive" in text(r))
r = login(f12, "FACULTY_12", "FacultyNewPass1"); check("inactive faculty login blocked", "inactive" in text(r))
post(c, "/admin/faculty/12/status", {"account_status":"Active"}, "/admin/faculty")
r = post(c, "/admin/faculty/999/status", {"account_status":"Active"}, "/admin/faculty"); check("faculty not found handled", "not found" in text(r))

# ---------- Club CRUD ----------
CL = "/admin/clubs"
r = post(c, CL, {"club_name":"Robotics Club"}, CL); check("club created", "Club created" in text(r))
r = post(c, CL, {"club_name":"robotics club"}, CL); check("duplicate club name rejected", "already exists" in text(r))
r = post(c, CL, {"club_name":"  "}, CL); check("empty club name rejected", "required" in text(r))
rid = db("select club_id from clubs where club_name='Robotics Club'")[0][0]
r = post(c, f"/admin/clubs/{rid}/edit", {"club_name":"Tamasha","club_status":"Active"}, CL); check("rename to existing name rejected", "Another club" in text(r))
r = post(c, f"/admin/clubs/{rid}/edit", {"club_name":"Robotics Society","club_status":"Inactive"}, CL); check("club edited", "updated successfully" in text(r))
check("edit persisted", db("select club_name, club_status from clubs where club_id=?",(rid,))[0] == ("Robotics Society","Inactive"))
r = s2.get("/student/clubs"); check("inactive club hidden from students", "Robotics Society" not in text(r))
r = post(c, f"/admin/clubs/{rid}/delete", {}, CL); check("club with no records deleted", "deleted successfully" in text(r))
r = post(c, "/admin/clubs/1/delete", {}, CL); check("club with records cannot be deleted", "cannot be deleted" in text(r))
r = post(c, "/admin/clubs/9999/delete", {}, CL); check("delete missing club handled", "not found" in text(r))

# ---------- Assignments ----------
AS = "/admin/assignments"
r = c.get(AS); check("assignments page lists current president", "Shubham Kumar Yadav" in text(r))
r = post(c, "/admin/presidents/assign", {"club_id":"3","student_id":"2"}, AS); check("non-member president rejected", "active member" in text(r))
r = post(c, "/admin/presidents/assign", {"club_id":"3","student_id":"1"}, AS); check("president assigned", "president assigned" in text(r))
check("old president ended, new active", db("select count(*) from club_president where club_id=3 and assignment_status='Active' and end_date is null")[0][0] == 1
      and db("select student_id from club_president where club_id=3 and assignment_status='Active'")[0][0] == 1)
r = post(c, "/admin/presidents/assign", {"club_id":"3","student_id":"1"}, AS); check("re-assigning same president rejected", "already the club president" in text(r))
r = post(c, "/admin/presidents/assign", {"club_id":"x","student_id":"1"}, AS); check("bad id rejected", "Invalid" in text(r))
r = s2.get("/student/dashboard"); check("student dashboard shows president role", "You are the president of" in text(r))
r = post(c, "/admin/advisors/assign", {"club_id":"3","faculty_id":"12"}, AS); check("advisor assigned", "advisor assigned" in text(r))
r = post(c, "/admin/advisors/assign", {"club_id":"3","faculty_id":"12"}, AS); check("same advisor rejected", "already the club" in text(r))
r = f.get("/faculty/applications"); check("old advisor no longer sees club 3 applications", "Spring Jam" not in text(r))
login(f12, "FACULTY_12", "FacultyNewPass1")
r = f12.get("/faculty/applications"); check("new advisor sees club 3 applications", "Spring Jam" in text(r))
db("UPDATE faculty_advisors SET account_status='Inactive' WHERE faculty_id=20")
r = post(c, "/admin/advisors/assign", {"club_id":"3","faculty_id":"20"}, AS); check("inactive faculty cannot be advisor", "must exist and be active" in text(r))

# ---------- Errors ----------
r = c.get("/does-not-exist"); check("404 page", r.status_code == 404 and "Page not found" in text(r))
os.environ.pop("MYSQL_PASSWORD")
r = app.test_client().post("/login", data={})
r2 = app.test_client()
t = token(r2, "/login")
r = r2.post("/login", data={"username":"a","password":"b","csrf_token":t})
check("missing MYSQL_PASSWORD -> friendly error page", r.status_code == 500 and "MYSQL_PASSWORD" in text(r))
os.environ["MYSQL_PASSWORD"] = "test"

# audit log
log = open(os.path.join(APP_DIR, "audit.log")).read()
check("audit log records sensitive actions", all(k in log for k in ["LOGIN_SUCCESS","STUDENT_ACCOUNT_CREATED","STUDENT_PASSWORD_RESET","STUDENT_STATUS_CHANGED","ADMIN_DECISION","CLUB_DELETED","LOGIN_FAILED"]))

passed = sum(1 for _, ok in results if ok)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
