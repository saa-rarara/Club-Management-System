import sqlite3, re, sys
dump, out = sys.argv[1], sys.argv[2]
schema = """
CREATE TABLE admin_representatives (admin_id INTEGER PRIMARY KEY AUTOINCREMENT, admin_name TEXT COLLATE NOCASE NOT NULL, designation TEXT COLLATE NOCASE, account_status TEXT COLLATE NOCASE NOT NULL);
CREATE TABLE students (student_id INTEGER PRIMARY KEY AUTOINCREMENT, student_name TEXT COLLATE NOCASE NOT NULL, department TEXT, program TEXT, account_status TEXT COLLATE NOCASE NOT NULL);
CREATE TABLE faculty_advisors (faculty_id INTEGER PRIMARY KEY AUTOINCREMENT, faculty_name TEXT COLLATE NOCASE NOT NULL, department TEXT, account_status TEXT COLLATE NOCASE NOT NULL);
CREATE TABLE clubs (club_id INTEGER PRIMARY KEY AUTOINCREMENT, club_name TEXT COLLATE NOCASE NOT NULL, club_status TEXT COLLATE NOCASE NOT NULL);
CREATE TABLE memberships (student_id INTEGER NOT NULL REFERENCES students(student_id), club_id INTEGER NOT NULL REFERENCES clubs(club_id), join_date TEXT NOT NULL, membership_status TEXT COLLATE NOCASE NOT NULL, PRIMARY KEY(student_id, club_id));
CREATE TABLE applications (application_id INTEGER PRIMARY KEY AUTOINCREMENT, club_id INTEGER NOT NULL REFERENCES clubs(club_id), student_id INTEGER NOT NULL REFERENCES students(student_id), title TEXT NOT NULL, description TEXT, submission_date TEXT NOT NULL, application_status TEXT COLLATE NOCASE NOT NULL, proposed_start TEXT NOT NULL, proposed_end TEXT NOT NULL, requested_venue TEXT NOT NULL, event_purpose TEXT, funding_required INTEGER NOT NULL DEFAULT 0, requested_amount REAL, funding_purpose TEXT,
  CHECK (proposed_end > proposed_start),
  CHECK ((funding_required = 0 AND requested_amount IS NULL AND funding_purpose IS NULL) OR (funding_required = 1 AND requested_amount > 0 AND funding_purpose IS NOT NULL)));
CREATE TABLE approval_decisions (decision_id INTEGER PRIMARY KEY AUTOINCREMENT, application_id INTEGER NOT NULL REFERENCES applications(application_id), faculty_id INTEGER REFERENCES faculty_advisors(faculty_id), admin_id INTEGER REFERENCES admin_representatives(admin_id), decision TEXT NOT NULL, comments TEXT, decision_date TEXT NOT NULL,
  UNIQUE(application_id, faculty_id), UNIQUE(application_id, admin_id),
  CHECK ((faculty_id IS NOT NULL AND admin_id IS NULL) OR (faculty_id IS NULL AND admin_id IS NOT NULL)),
  CHECK (decision IN ('Approved','Rejected','Pending')));
CREATE TABLE club_advisor (advisor_assignment_id INTEGER PRIMARY KEY AUTOINCREMENT, faculty_id INTEGER NOT NULL REFERENCES faculty_advisors(faculty_id), club_id INTEGER NOT NULL REFERENCES clubs(club_id), start_date TEXT NOT NULL, end_date TEXT, assignment_status TEXT COLLATE NOCASE NOT NULL, CHECK (end_date IS NULL OR end_date >= start_date));
CREATE TABLE club_president (president_assignment_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, club_id INTEGER NOT NULL, start_date TEXT NOT NULL, end_date TEXT, assignment_status TEXT COLLATE NOCASE NOT NULL, FOREIGN KEY(student_id, club_id) REFERENCES memberships(student_id, club_id), CHECK (end_date IS NULL OR end_date >= start_date));
CREATE TABLE user_accounts (account_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER UNIQUE REFERENCES students(student_id), faculty_id INTEGER UNIQUE REFERENCES faculty_advisors(faculty_id), admin_id INTEGER UNIQUE REFERENCES admin_representatives(admin_id), username TEXT COLLATE NOCASE NOT NULL UNIQUE, password_hash TEXT NOT NULL,
  CHECK ((student_id IS NOT NULL) + (faculty_id IS NOT NULL) + (admin_id IS NOT NULL) = 1));
"""
con = sqlite3.connect(out); con.executescript(schema)
n=0
for line in open(dump, encoding="utf-8"):
    if line.startswith("INSERT INTO"):
        con.execute(line.replace("`","").rstrip().rstrip(";")); n+=1
con.commit()
for t in ["students","faculty_advisors","admin_representatives","clubs","memberships","applications","approval_decisions","user_accounts"]:
    print(t, con.execute(f"select count(*) from {t}").fetchone()[0])
