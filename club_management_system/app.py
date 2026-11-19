# ============================================================
# SAU CLUB MANAGEMENT SYSTEM
# Backend: Python + Flask
# Database: MySQL
# ============================================================
#
#  file layout for my dummy friends
#   1.  Imports and configuration
#   2.  Database connection
#   3.  Password hashing and validation helpers
#   4.  Audit logging
#   5.  CSRF protection
#   6.  Access control (login_required / role_required)
#   7.  Authentication (login / logout)
#   8.  Student module
#   9.  Faculty advisor module
#   10. Application approval helpers
#   11. Admin module (dashboard, clubs, students, faculty,
#       assignments, applications)
#   12. Error handling
#   13. Run the application
# ============================================================


# ============================================================
# 1. IMPORTS AND CONFIGURATION
# ============================================================

from flask import (
    Flask, render_template, request,
    redirect, session, url_for, flash, abort
)
import os
import logging
import secrets

import mysql.connector

from mysql.connector import Error, IntegrityError

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from functools import wraps
from datetime import date, datetime, timedelta


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

# Use an environment variable for the secret key when available.
# The fallback is suitable only for local development.
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "development-key-change-before-deployment"
)

# Keep permanent login sessions valid for two hours.
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=2)

# Cookie security settings.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Validation rules shared by all account forms.
MIN_PASSWORD_LENGTH = 12
MAX_USERNAME_LENGTH = 100          # User_Accounts.username is VARCHAR(100)
MAX_CLUB_NAME_LENGTH = 100         # Clubs.club_name is VARCHAR(100)
MAX_TITLE_LENGTH = 150             # Applications.title is VARCHAR(150)
MAX_VENUE_LENGTH = 150             # Applications.requested_venue is VARCHAR(150)

VALID_ACCOUNT_STATUSES = ["Active", "Inactive"]
VALID_APPLICATION_FILTERS = ["all", "Pending", "Approved", "Rejected"]


# ============================================================
# 2. DATABASE CONNECTION
# ============================================================

class DatabaseConfigError(RuntimeError):
    """Raised when the MySQL password environment variable is missing."""


def get_db_connection():

    mysql_password = os.environ.get("MYSQL_PASSWORD")

    if not mysql_password:
        raise DatabaseConfigError(
            "MYSQL_PASSWORD environment variable is not configured."
        )

    # Host, user and database can be overridden with environment
    # variables, but the defaults match the original setup.
    connection = mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "localhost"),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("sa242018"),
        database=os.environ.get("MYSQL_DATABASE", "sau_club_management")
    )

    return connection


# ============================================================
# 3. PASSWORD HASHING AND VALIDATION HELPERS
# ============================================================

def hash_password(password):

    return generate_password_hash(
        password,
        method="pbkdf2:sha256"
    )


def verify_password(stored_hash, entered_password):

    return check_password_hash(
        stored_hash,
        entered_password
    )


def validate_password(password, confirm_password):
    """
    Return an error message if the password is unacceptable,
    otherwise return None.
    """

    if not password or not confirm_password:
        return "Both password fields are required."

    if len(password) < MIN_PASSWORD_LENGTH:
        return (
            f"Password must contain at least "
            f"{MIN_PASSWORD_LENGTH} characters."
        )

    if password != confirm_password:
        return "Passwords do not match."

    return None


def validate_new_credentials(username, password, confirm_password):
    """Validate a username plus password pair for a new account."""

    if not username:
        return "Username is required."

    if len(username) > MAX_USERNAME_LENGTH:
        return f"Username cannot exceed {MAX_USERNAME_LENGTH} characters."

    if " " in username:
        return "Username cannot contain spaces."

    return validate_password(password, confirm_password)


def get_decisions_by_application(cursor, application_ids):
    """
    Fetch every approval decision for the given applications and
    group them in a dictionary: {application_id: [decision, ...]}.

    The IN (...) list is built from "%s" placeholders only, so the
    values are still passed safely as query parameters.
    """

    if not application_ids:
        return {}

    placeholders = ", ".join(["%s"] * len(application_ids))

    cursor.execute(f"""
        SELECT
            ad.application_id,
            ad.faculty_id,
            ad.admin_id,
            ad.decision,
            ad.comments,
            ad.decision_date,
            COALESCE(f.faculty_name, ar.admin_name) AS reviewer_name,
            CASE
                WHEN ad.faculty_id IS NOT NULL THEN 'Faculty Advisor'
                ELSE 'Administrator'
            END AS reviewer_role

        FROM Approval_Decisions ad

        LEFT JOIN Faculty_Advisors f
            ON ad.faculty_id = f.faculty_id

        LEFT JOIN Admin_Representatives ar
            ON ad.admin_id = ar.admin_id

        WHERE ad.application_id IN ({placeholders})

        ORDER BY ad.decision_date
    """, tuple(application_ids))

    grouped = {}

    for row in cursor.fetchall():
        grouped.setdefault(row["application_id"], []).append(row)

    return grouped


# ------------------------------------------------------------
# Template display filters
# ------------------------------------------------------------
# mysql-connector returns DATE/DATETIME columns as Python date and
# datetime objects. These filters format them consistently in the
# templates, e.g. {{ application.submission_date|datetime_display }}.

@app.template_filter("datetime_display")
def datetime_display(value, with_time=True):

    if value is None or value == "":
        return "—"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value

    if isinstance(value, datetime):
        if with_time:
            return value.strftime("%d %b %Y, %H:%M")
        return value.strftime("%d %b %Y")

    if isinstance(value, date):
        return value.strftime("%d %b %Y")

    return value


@app.template_filter("money")
def money(value):

    if value is None:
        return "—"

    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return value


# ============================================================
# 4. AUDIT LOGGING
# ============================================================
# Sensitive actions (logins, account creation, password resets,
# status changes, deletions, decisions) are appended to audit.log.
# There is no audit table in the SQL schema, so a plain text log
# file is used instead of inventing a new table.

audit_logger = logging.getLogger("sau_audit")
audit_logger.setLevel(logging.INFO)
audit_logger.propagate = False

if not audit_logger.handlers:
    _audit_handler = logging.FileHandler(
        os.path.join(BASE_DIR, "audit.log"),
        encoding="utf-8"
    )
    _audit_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(message)s")
    )
    audit_logger.addHandler(_audit_handler)


def audit(action, details="", account_id=None, role=None):

    audit_logger.info(
        "account_id=%s | role=%s | ip=%s | %s | %s",
        account_id if account_id is not None else session.get("account_id"),
        role if role is not None else session.get("role"),
        request.remote_addr,
        action,
        details
    )


# ============================================================
# 5. CSRF PROTECTION
# ============================================================
# Every POST form contains a hidden csrf_token field. The token is
# stored in the user's session. A POST request without the matching
# token is rejected, which stops other websites from submitting
# forms on behalf of a logged-in user.

def get_csrf_token():

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    return session["csrf_token"]


# Make csrf_token() callable inside every Jinja2 template.
app.jinja_env.globals["csrf_token"] = get_csrf_token


@app.before_request
def csrf_protect():

    if request.method == "POST":

        submitted_token = request.form.get("csrf_token", "")
        session_token = session.get("csrf_token", "")

        if (
            not submitted_token
            or not session_token
            or not secrets.compare_digest(submitted_token, session_token)
        ):
            abort(400)


# ============================================================
# 6. ACCESS CONTROL
# ============================================================

# Used to re-check that a logged-in user is still active.
STATUS_QUERIES = {
    "student": """
        SELECT account_status
        FROM Students
        WHERE student_id = %s
    """,
    "faculty": """
        SELECT account_status
        FROM Faculty_Advisors
        WHERE faculty_id = %s
    """,
    "admin": """
        SELECT account_status
        FROM Admin_Representatives
        WHERE admin_id = %s
    """
}


def session_user_is_active():
    """
    Return True if the user stored in the session still exists and
    is Active. This means an administrator can deactivate a user and
    the user is signed out on their next page request.
    """

    role = session.get("role")
    user_id = session.get("user_id")

    if role not in STATUS_QUERIES or user_id is None:
        return False

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(STATUS_QUERIES[role], (user_id,))
        row = cursor.fetchone()

        return (
            row is not None
            and str(row["account_status"]).lower() == "active"
        )

    finally:

        cursor.close()
        connection.close()


def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "account_id" not in session:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login"))

        if not session_user_is_active():
            session.clear()
            flash(
                "Your account is inactive. Please contact the "
                "administrator.",
                "error"
            )
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


def role_required(required_role):

    def decorator(function):

        @wraps(function)
        def wrapper(*args, **kwargs):

            if "account_id" not in session:
                return redirect(url_for("login"))

            if session.get("role") != required_role:
                abort(403)

            return function(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================
# 7. AUTHENTICATION
# ============================================================

@app.route("/")
def home():

    if "account_id" not in session:
        return redirect(url_for("login"))

    role = session.get("role")

    if role == "student":
        return redirect(url_for("student_dashboard"))

    elif role == "faculty":
        return redirect(url_for("faculty_dashboard"))

    elif role == "admin":
        return redirect(url_for("admin_dashboard"))

    session.clear()
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():

    # If the user is already logged in, send them to their dashboard.
    if request.method == "GET" and "account_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please enter both username and password.", "error")
            return redirect(url_for("login"))

        connection = None
        cursor = None

        try:

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            query = """
                SELECT *
                FROM User_Accounts
                WHERE username = %s
            """

            cursor.execute(query, (username,))
            account = cursor.fetchone()

            # The same message is used for "no such user" and
            # "wrong password" so attackers cannot discover
            # which usernames exist.
            if account is None:
                audit("LOGIN_FAILED", f"username={username}",
                      account_id="-", role="-")
                flash("Invalid username or password.", "error")
                return redirect(url_for("login"))

            if not verify_password(
                account["password_hash"], password
            ):
                audit("LOGIN_FAILED", f"username={username}",
                      account_id=account["account_id"], role="-")
                flash("Invalid username or password.", "error")
                return redirect(url_for("login"))

            # Identify role.

            if account["student_id"] is not None:

                role = "student"
                user_id = account["student_id"]

                status_query = """
                    SELECT account_status,
                           student_name AS display_name
                    FROM Students
                    WHERE student_id = %s
                """

            elif account["faculty_id"] is not None:

                role = "faculty"
                user_id = account["faculty_id"]

                status_query = """
                    SELECT account_status,
                           faculty_name AS display_name
                    FROM Faculty_Advisors
                    WHERE faculty_id = %s
                """

            elif account["admin_id"] is not None:

                role = "admin"
                user_id = account["admin_id"]

                status_query = """
                    SELECT account_status,
                           admin_name AS display_name
                    FROM Admin_Representatives
                    WHERE admin_id = %s
                """

            else:
                flash("Invalid account configuration.", "error")
                return redirect(url_for("login"))

            # Check account status.

            cursor.execute(status_query, (user_id,))
            user_status = cursor.fetchone()

            if (
                user_status is None
                or str(user_status["account_status"]).lower() != "active"
            ):
                audit("LOGIN_BLOCKED_INACTIVE", f"username={username}",
                      account_id=account["account_id"], role=role)
                flash(
                    "Your account is inactive. Please contact the "
                    "administrator.",
                    "error"
                )
                return redirect(url_for("login"))

            # Create session. session.clear() first prevents an old
            # session (and its CSRF token) being reused.

            session.clear()
            session.permanent = True

            session["account_id"] = account["account_id"]
            session["user_id"] = user_id
            session["role"] = role
            session["username"] = account["username"]
            session["display_name"] = user_status["display_name"]

            audit("LOGIN_SUCCESS", f"username={username}")

            return redirect(url_for("home"))

        except Error as error:

            print("Login database error:", error)
            flash("Unable to process login. Please try again.", "error")

            return redirect(url_for("login"))

        finally:

            if cursor is not None:
                cursor.close()

            if connection is not None and connection.is_connected():
                connection.close()

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():

    if "account_id" in session:
        audit("LOGOUT")

    session.clear()

    flash("You have been signed out.", "success")

    return redirect(url_for("login"))


# ============================================================
# 8. STUDENT MODULE
# ============================================================

@app.route("/student/dashboard")
@login_required
@role_required("student")
def student_dashboard():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        student_id = session["user_id"]

        cursor.execute("""
            SELECT *
            FROM Students
            WHERE student_id = %s
        """, (student_id,))

        student = cursor.fetchone()

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM Memberships
            WHERE student_id = %s
              AND membership_status = 'Active'
        """, (student_id,))

        membership_count = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM Applications
            WHERE student_id = %s
              AND application_status = 'Pending'
        """, (student_id,))

        pending_count = cursor.fetchone()["total"]

        # Clubs the student currently belongs to.
        cursor.execute("""
            SELECT c.club_id, c.club_name, m.join_date
            FROM Memberships m
            JOIN Clubs c ON m.club_id = c.club_id
            WHERE m.student_id = %s
              AND m.membership_status = 'Active'
            ORDER BY c.club_name
        """, (student_id,))

        my_clubs = cursor.fetchall()

        # Clubs where the student is the current president.
        cursor.execute("""
            SELECT c.club_name
            FROM Club_President cp
            JOIN Clubs c ON cp.club_id = c.club_id
            WHERE cp.student_id = %s
              AND cp.assignment_status = 'Active'
              AND cp.end_date IS NULL
        """, (student_id,))

        president_of = cursor.fetchall()

        # Five most recent applications.
        cursor.execute("""
            SELECT a.application_id, a.title,
                   a.application_status, a.submission_date,
                   c.club_name
            FROM Applications a
            JOIN Clubs c ON a.club_id = c.club_id
            WHERE a.student_id = %s
            ORDER BY a.submission_date DESC
            LIMIT 5
        """, (student_id,))

        recent_applications = cursor.fetchall()

        return render_template(
            "student_dashboard.html",
            student=student,
            membership_count=membership_count,
            pending_count=pending_count,
            my_clubs=my_clubs,
            president_of=president_of,
            recent_applications=recent_applications
        )

    finally:

        cursor.close()
        connection.close()


# ------------------------------------------------------------
# VIEW CLUBS
# ------------------------------------------------------------

@app.route("/student/clubs")
@login_required
@role_required("student")
def view_clubs():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        student_id = session["user_id"]

        query = """
            SELECT
                c.club_id,
                c.club_name,
                c.club_status,
                m.membership_status,

                (
                    SELECT COUNT(*)
                    FROM Memberships m2
                    WHERE m2.club_id = c.club_id
                      AND m2.membership_status = 'Active'
                ) AS member_count

            FROM Clubs c

            LEFT JOIN Memberships m
                ON c.club_id = m.club_id
                AND m.student_id = %s

            WHERE c.club_status = 'Active'

            ORDER BY c.club_name
        """

        cursor.execute(query, (student_id,))
        clubs = cursor.fetchall()

        return render_template(
            "student_clubs.html",
            clubs=clubs
        )

    finally:

        cursor.close()
        connection.close()


# ------------------------------------------------------------
# JOIN CLUB
# ------------------------------------------------------------

@app.route("/student/clubs/<int:club_id>/join", methods=["POST"])
@login_required
@role_required("student")
def join_club(club_id):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        student_id = session["user_id"]

        cursor.execute("""
            SELECT club_id, club_name
            FROM Clubs
            WHERE club_id = %s
              AND club_status = 'Active'
        """, (club_id,))

        club = cursor.fetchone()

        if club is None:
            flash("Club not found or inactive.", "error")
            return redirect(url_for("view_clubs"))

        cursor.execute("""
            SELECT membership_status
            FROM Memberships
            WHERE student_id = %s
              AND club_id = %s
        """, (student_id, club_id))

        membership = cursor.fetchone()

        if membership is not None:

            if membership["membership_status"] == "Active":
                flash("You are already a member of this club.", "error")

            else:
                flash(
                    "A membership record already exists. Please "
                    "contact the administrator.",
                    "error"
                )

            return redirect(url_for("view_clubs"))

        cursor.execute("""
            INSERT INTO Memberships
                (student_id, club_id, join_date, membership_status)
            VALUES (%s, %s, %s, 'Active')
        """, (student_id, club_id, date.today()))

        connection.commit()

        flash(f"You successfully joined {club['club_name']}.", "success")

        return redirect(url_for("view_clubs"))

    except IntegrityError:

        connection.rollback()
        flash("Membership could not be created.", "error")

        return redirect(url_for("view_clubs"))

    finally:

        cursor.close()
        connection.close()


# ------------------------------------------------------------
# VIEW MEMBERSHIPS
# ------------------------------------------------------------

@app.route("/student/memberships")
@login_required
@role_required("student")
def view_memberships():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                c.club_id,
                c.club_name,
                c.club_status,
                m.join_date,
                m.membership_status

            FROM Memberships m

            JOIN Clubs c
                ON m.club_id = c.club_id

            WHERE m.student_id = %s

            ORDER BY m.join_date DESC, c.club_name
        """, (session["user_id"],))

        memberships = cursor.fetchall()

        return render_template(
            "student_memberships.html",
            memberships=memberships
        )

    finally:

        cursor.close()
        connection.close()


# ------------------------------------------------------------
# SUBMIT EVENT APPLICATION
# ------------------------------------------------------------

def parse_datetime_local(value):
    """
    Convert the value of an <input type="datetime-local"> field
    (for example "2026-12-05T10:00") into a Python datetime.
    Returns None if the value is missing or invalid.
    """

    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@app.route("/student/applications/new", methods=["GET", "POST"])
@login_required
@role_required("student")
def submit_application():

    if request.method == "POST":

        student_id = session["user_id"]

        club_id = request.form.get("club_id")
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        proposed_start = request.form.get("proposed_start")
        proposed_end = request.form.get("proposed_end")

        venue = request.form.get("requested_venue", "").strip()
        purpose = request.form.get("event_purpose", "").strip()

        funding_required = (
            request.form.get("funding_required") == "yes"
        )

        requested_amount = request.form.get("requested_amount")
        funding_purpose = request.form.get("funding_purpose", "").strip()

        if not all([
            club_id, title, description,
            proposed_start, proposed_end, venue, purpose
        ]):
            flash("Please complete all required fields.", "error")
            return redirect(url_for("submit_application"))

        if len(title) > MAX_TITLE_LENGTH:
            flash(
                f"Title cannot exceed {MAX_TITLE_LENGTH} characters.",
                "error"
            )
            return redirect(url_for("submit_application"))

        if len(venue) > MAX_VENUE_LENGTH:
            flash(
                f"Venue cannot exceed {MAX_VENUE_LENGTH} characters.",
                "error"
            )
            return redirect(url_for("submit_application"))

        start_datetime = parse_datetime_local(proposed_start)
        end_datetime = parse_datetime_local(proposed_end)

        if start_datetime is None or end_datetime is None:
            flash("Please enter valid event start and end times.", "error")
            return redirect(url_for("submit_application"))

        if end_datetime <= start_datetime:
            flash("Event end must be after event start.", "error")
            return redirect(url_for("submit_application"))

        if start_datetime <= datetime.now():
            flash("Event start must be in the future.", "error")
            return redirect(url_for("submit_application"))

        try:

            club_id = int(club_id)

            if funding_required:

                if not requested_amount or not funding_purpose:
                    flash(
                        "Please provide the funding amount and purpose.",
                        "error"
                    )
                    return redirect(url_for("submit_application"))

                requested_amount = float(requested_amount)

                if requested_amount <= 0:
                    flash(
                        "Funding amount must be greater than zero.",
                        "error"
                    )
                    return redirect(url_for("submit_application"))

                # Applications.requested_amount is DECIMAL(12,2).
                if requested_amount >= 10_000_000_000:
                    flash("Funding amount is too large.", "error")
                    return redirect(url_for("submit_application"))

                requested_amount = round(requested_amount, 2)

            else:

                # The database CHECK constraint requires both of these
                # to be NULL when no funding is requested.
                requested_amount = None
                funding_purpose = None

        except (ValueError, TypeError):

            flash("Invalid club ID or funding amount.", "error")
            return redirect(url_for("submit_application"))

        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        try:

            # Student must be an active member of an active club.

            cursor.execute("""
                SELECT m.membership_status
                FROM Memberships m
                JOIN Clubs c ON m.club_id = c.club_id
                WHERE m.student_id = %s
                  AND m.club_id = %s
                  AND c.club_status = 'Active'
            """, (student_id, club_id))

            membership = cursor.fetchone()

            if (
                membership is None
                or membership["membership_status"] != "Active"
            ):
                flash("You must be an active club member to apply.", "error")
                return redirect(url_for("submit_application"))

            cursor.execute("""
                INSERT INTO Applications (
                    club_id,
                    student_id,
                    title,
                    description,
                    submission_date,
                    application_status,
                    proposed_start,
                    proposed_end,
                    requested_venue,
                    event_purpose,
                    funding_required,
                    requested_amount,
                    funding_purpose
                )
                VALUES (
                    %s, %s, %s, %s, NOW(), 'Pending',
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                club_id,
                student_id,
                title,
                description,
                start_datetime,
                end_datetime,
                venue,
                purpose,
                funding_required,
                requested_amount,
                funding_purpose
            ))

            connection.commit()

            audit(
                "APPLICATION_SUBMITTED",
                f"application_id={cursor.lastrowid} club_id={club_id}"
            )

            flash("Application submitted successfully.", "success")

            return redirect(url_for("view_applications"))

        except Error as error:

            connection.rollback()
            print("Application submission error:", error)

            flash("Unable to submit application.", "error")

            return redirect(url_for("submit_application"))

        finally:

            cursor.close()
            connection.close()

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT c.club_id, c.club_name
            FROM Clubs c

            JOIN Memberships m
                ON c.club_id = m.club_id

            WHERE m.student_id = %s
              AND m.membership_status = 'Active'
              AND c.club_status = 'Active'

            ORDER BY c.club_name
        """, (session["user_id"],))

        clubs = cursor.fetchall()

        return render_template(
            "application_form.html",
            clubs=clubs
        )

    finally:

        cursor.close()
        connection.close()


# ------------------------------------------------------------
# TRACK APPLICATIONS
# ------------------------------------------------------------

@app.route("/student/applications")
@login_required
@role_required("student")
def view_applications():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                a.*,
                c.club_name

            FROM Applications a

            JOIN Clubs c
                ON a.club_id = c.club_id

            WHERE a.student_id = %s

            ORDER BY a.submission_date DESC
        """, (session["user_id"],))

        applications = cursor.fetchall()

        decisions = get_decisions_by_application(
            cursor,
            [a["application_id"] for a in applications]
        )

        return render_template(
            "student_applications.html",
            applications=applications,
            decisions=decisions
        )

    finally:

        cursor.close()
        connection.close()


# ============================================================
# 9. FACULTY ADVISOR MODULE
# ============================================================

@app.route("/faculty/dashboard")
@login_required
@role_required("faculty")
def faculty_dashboard():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        faculty_id = session["user_id"]

        cursor.execute("""
            SELECT *
            FROM Faculty_Advisors
            WHERE faculty_id = %s
        """, (faculty_id,))

        faculty = cursor.fetchone()

        cursor.execute("""
            SELECT
                c.club_id,
                c.club_name,
                c.club_status,

                (
                    SELECT COUNT(*)
                    FROM Memberships m
                    WHERE m.club_id = c.club_id
                      AND m.membership_status = 'Active'
                ) AS member_count,

                (
                    SELECT s.student_name
                    FROM Club_President cp
                    JOIN Students s ON cp.student_id = s.student_id
                    WHERE cp.club_id = c.club_id
                      AND cp.assignment_status = 'Active'
                      AND cp.end_date IS NULL
                    ORDER BY cp.start_date DESC
                    LIMIT 1
                ) AS president_name

            FROM Club_Advisor ca

            JOIN Clubs c
                ON ca.club_id = c.club_id

            WHERE ca.faculty_id = %s
              AND ca.assignment_status = 'Active'
              AND ca.end_date IS NULL

            ORDER BY c.club_name
        """, (faculty_id,))

        clubs = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) AS total

            FROM Applications a

            JOIN Club_Advisor ca
                ON a.club_id = ca.club_id

            WHERE ca.faculty_id = %s
              AND ca.assignment_status = 'Active'
              AND ca.end_date IS NULL
              AND a.application_status = 'Pending'
        """, (faculty_id,))

        pending_count = cursor.fetchone()["total"]

        # Pending applications that this faculty member has not
        # yet given a decision on.
        cursor.execute("""
            SELECT a.application_id, a.title, a.submission_date,
                   c.club_name, s.student_name

            FROM Applications a
            JOIN Clubs c ON a.club_id = c.club_id
            JOIN Students s ON a.student_id = s.student_id
            JOIN Club_Advisor ca ON a.club_id = ca.club_id

            WHERE ca.faculty_id = %s
              AND ca.assignment_status = 'Active'
              AND ca.end_date IS NULL
              AND a.application_status = 'Pending'
              AND NOT EXISTS (
                  SELECT 1
                  FROM Approval_Decisions ad
                  WHERE ad.application_id = a.application_id
                    AND ad.faculty_id = %s
                    AND ad.decision IN ('Approved', 'Rejected')
              )

            ORDER BY a.submission_date
            LIMIT 5
        """, (faculty_id, faculty_id))

        awaiting_review = cursor.fetchall()

        return render_template(
            "faculty_dashboard.html",
            faculty=faculty,
            clubs=clubs,
            pending_count=pending_count,
            awaiting_review=awaiting_review
        )

    finally:

        cursor.close()
        connection.close()


# ------------------------------------------------------------
# FACULTY VIEW APPLICATIONS
# ------------------------------------------------------------

@app.route("/faculty/applications")
@login_required
@role_required("faculty")
def faculty_applications():

    status_filter = request.args.get("status", "all")

    if status_filter not in VALID_APPLICATION_FILTERS:
        status_filter = "all"

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        query = """
            SELECT
                a.*,
                c.club_name,
                s.student_name

            FROM Applications a

            JOIN Clubs c
                ON a.club_id = c.club_id

            JOIN Students s
                ON a.student_id = s.student_id

            JOIN Club_Advisor ca
                ON a.club_id = ca.club_id

            WHERE ca.faculty_id = %s
              AND ca.assignment_status = 'Active'
              AND ca.end_date IS NULL
        """

        params = [session["user_id"]]

        if status_filter != "all":
            query += " AND a.application_status = %s"
            params.append(status_filter)

        query += " ORDER BY a.submission_date DESC"

        cursor.execute(query, params)

        applications = cursor.fetchall()

        decisions = get_decisions_by_application(
            cursor,
            [a["application_id"] for a in applications]
        )

        return render_template(
            "faculty_applications.html",
            applications=applications,
            decisions=decisions,
            status_filter=status_filter
        )

    finally:

        cursor.close()
        connection.close()


# ------------------------------------------------------------
# FACULTY APPROVE / REJECT APPLICATION
# ------------------------------------------------------------

@app.route(
    "/faculty/applications/<int:application_id>/decision",
    methods=["POST"]
)
@login_required
@role_required("faculty")
def faculty_decision(application_id):

    decision = request.form.get("decision")
    comments = request.form.get("comments", "").strip()

    if decision not in ["Approved", "Rejected"]:
        flash("Invalid decision.", "error")
        return redirect(url_for("faculty_applications"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        faculty_id = session["user_id"]

        # Verify that this faculty member advises the club.

        cursor.execute("""
            SELECT a.application_id

            FROM Applications a

            JOIN Club_Advisor ca
                ON a.club_id = ca.club_id

            WHERE a.application_id = %s
              AND ca.faculty_id = %s
              AND ca.assignment_status = 'Active'
              AND ca.end_date IS NULL
        """, (application_id, faculty_id))

        if cursor.fetchone() is None:
            flash(
                "You are not authorised to review this application.",
                "error"
            )
            return redirect(url_for("faculty_applications"))

        connection.start_transaction()

        cursor.execute("""
            INSERT INTO Approval_Decisions (
                application_id,
                faculty_id,
                admin_id,
                decision,
                comments,
                decision_date
            )
            VALUES (%s, %s, NULL, %s, %s, NOW())

            ON DUPLICATE KEY UPDATE
                decision = VALUES(decision),
                comments = VALUES(comments),
                decision_date = NOW()
        """, (
            application_id,
            faculty_id,
            decision,
            comments
        ))

        new_status = update_application_status(cursor, application_id)

        connection.commit()

        audit(
            "FACULTY_DECISION",
            f"application_id={application_id} decision={decision} "
            f"new_status={new_status}"
        )

        flash(
            f"Faculty decision recorded. Application status is now "
            f"{new_status}.",
            "success"
        )

    except Error as error:

        connection.rollback()
        print("Faculty decision error:", error)

        flash("Unable to record faculty decision.", "error")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("faculty_applications"))


# ============================================================
# 10. APPLICATION APPROVAL HELPER
# ============================================================
# Rule (unchanged from the original project):
#   - any "Rejected" decision          -> application Rejected
#   - at least two "Approved" decisions -> application Approved
#   - otherwise                         -> application Pending
# In practice the two approvals come from the club's faculty
# advisor and an administrator.

def update_application_status(cursor, application_id):

    cursor.execute("""
        SELECT
            SUM(decision = 'Approved') AS approvals,
            SUM(decision = 'Rejected') AS rejections

        FROM Approval_Decisions

        WHERE application_id = %s
    """, (application_id,))

    result = cursor.fetchone()

    approvals = result["approvals"] or 0
    rejections = result["rejections"] or 0

    if rejections > 0:
        status = "Rejected"

    elif approvals >= 2:
        status = "Approved"

    else:
        status = "Pending"

    cursor.execute("""
        UPDATE Applications
        SET application_status = %s
        WHERE application_id = %s
    """, (status, application_id))

    return status


# ============================================================
# 11. ADMIN REPRESENTATIVE MODULE
# ============================================================

@app.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("SELECT COUNT(*) AS total FROM Students")
        students = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM Clubs")
        clubs = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM Applications
            WHERE application_status = 'Pending'
        """)
        pending = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM Faculty_Advisors
        """)
        faculty = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM Memberships
            WHERE membership_status = 'Active'
        """)
        memberships = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) AS total FROM User_Accounts")
        accounts = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT a.application_id, a.title, a.submission_date,
                   c.club_name, s.student_name
            FROM Applications a
            JOIN Clubs c ON a.club_id = c.club_id
            JOIN Students s ON a.student_id = s.student_id
            WHERE a.application_status = 'Pending'
            ORDER BY a.submission_date
            LIMIT 5
        """)
        pending_applications = cursor.fetchall()

        return render_template(
            "admin_dashboard.html",
            students=students,
            clubs=clubs,
            pending=pending,
            faculty=faculty,
            memberships=memberships,
            accounts=accounts,
            pending_applications=pending_applications
        )

    finally:

        cursor.close()
        connection.close()


# ------------------------------------------------------------
# CLUB MANAGEMENT — CREATE AND VIEW
# ------------------------------------------------------------

@app.route("/admin/clubs", methods=["GET", "POST"])
@login_required
@role_required("admin")
def manage_clubs():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        if request.method == "POST":

            club_name = request.form.get("club_name", "").strip()

            if not club_name:
                flash("Club name is required.", "error")
                return redirect(url_for("manage_clubs"))

            if len(club_name) > MAX_CLUB_NAME_LENGTH:
                flash(
                    f"Club name cannot exceed {MAX_CLUB_NAME_LENGTH} "
                    f"characters.",
                    "error"
                )
                return redirect(url_for("manage_clubs"))

            # The schema has no UNIQUE constraint on club_name, so
            # duplicates are prevented here instead.
            cursor.execute("""
                SELECT club_id
                FROM Clubs
                WHERE LOWER(club_name) = LOWER(%s)
            """, (club_name,))

            if cursor.fetchone() is not None:
                flash("A club with this name already exists.", "error")
                return redirect(url_for("manage_clubs"))

            try:

                cursor.execute("""
                    INSERT INTO Clubs (club_name, club_status)
                    VALUES (%s, 'Active')
                """, (club_name,))

                connection.commit()

                audit(
                    "CLUB_CREATED",
                    f"club_id={cursor.lastrowid} name={club_name}"
                )

                flash("Club created successfully.", "success")

            except IntegrityError:

                connection.rollback()
                flash("Unable to create club. Check for duplicates.", "error")

            return redirect(url_for("manage_clubs"))

        cursor.execute("""
            SELECT
                c.*,

                (
                    SELECT COUNT(*)
                    FROM Memberships m
                    WHERE m.club_id = c.club_id
                      AND m.membership_status = 'Active'
                ) AS member_count,

                (
                    SELECT s.student_name
                    FROM Club_President cp
                    JOIN Students s ON cp.student_id = s.student_id
                    WHERE cp.club_id = c.club_id
                      AND cp.assignment_status = 'Active'
                      AND cp.end_date IS NULL
                    ORDER BY cp.start_date DESC
                    LIMIT 1
                ) AS president_name,

                (
                    SELECT f.faculty_name
                    FROM Club_Advisor ca
                    JOIN Faculty_Advisors f ON ca.faculty_id = f.faculty_id
                    WHERE ca.club_id = c.club_id
                      AND ca.assignment_status = 'Active'
                      AND ca.end_date IS NULL
                    ORDER BY ca.start_date DESC
                    LIMIT 1
                ) AS advisor_name

            FROM Clubs c

            ORDER BY c.club_id
        """)

        clubs = cursor.fetchall()

        return render_template(
            "admin_clubs.html",
            clubs=clubs
        )

    finally:

        cursor.close()
        connection.close()


# ------------------------------------------------------------
# UPDATE CLUB
# ------------------------------------------------------------

@app.route("/admin/clubs/<int:club_id>/edit", methods=["POST"])
@login_required
@role_required("admin")
def edit_club(club_id):

    club_name = request.form.get("club_name", "").strip()
    club_status = request.form.get("club_status")

    if not club_name or club_status not in VALID_ACCOUNT_STATUSES:
        flash("Invalid club details.", "error")
        return redirect(url_for("manage_clubs"))

    if len(club_name) > MAX_CLUB_NAME_LENGTH:
        flash(
            f"Club name cannot exceed {MAX_CLUB_NAME_LENGTH} characters.",
            "error"
        )
        return redirect(url_for("manage_clubs"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT club_id
            FROM Clubs
            WHERE LOWER(club_name) = LOWER(%s)
              AND club_id <> %s
        """, (club_name, club_id))

        if cursor.fetchone() is not None:
            flash("Another club already uses this name.", "error")
            return redirect(url_for("manage_clubs"))

        cursor.execute("""
            UPDATE Clubs
            SET club_name = %s,
                club_status = %s
            WHERE club_id = %s
        """, (club_name, club_status, club_id))

        connection.commit()

        audit(
            "CLUB_UPDATED",
            f"club_id={club_id} name={club_name} status={club_status}"
        )

        flash("Club updated successfully.", "success")

    except Error as error:

        connection.rollback()
        print("Club update error:", error)
        flash("Unable to update club.", "error")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("manage_clubs"))


# ------------------------------------------------------------
# DELETE CLUB
# ------------------------------------------------------------

@app.route("/admin/clubs/<int:club_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_club(club_id):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            DELETE FROM Clubs
            WHERE club_id = %s
        """, (club_id,))

        if cursor.rowcount == 0:
            connection.rollback()
            flash("Club not found.", "error")

        else:
            connection.commit()
            audit("CLUB_DELETED", f"club_id={club_id}")
            flash("Club deleted successfully.", "success")

    except IntegrityError:

        # Foreign keys in Memberships, Applications and Club_Advisor
        # stop a club with history from being deleted.
        connection.rollback()

        flash(
            "This club has related records and cannot be deleted. "
            "Consider marking it inactive instead.",
            "error"
        )

    except Error as error:

        connection.rollback()
        print("Club delete error:", error)
        flash("Unable to delete club.", "error")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("manage_clubs"))


# ------------------------------------------------------------
# STUDENT MANAGEMENT
# ------------------------------------------------------------

@app.route("/admin/students")
@login_required
@role_required("admin")
def manage_students():

    # Read search and filter values from the URL.
    search_query = request.args.get("search", "").strip()
    login_filter = request.args.get("login_status", "all")
    student_filter = request.args.get("student_status", "all")

    # Validate filter values.
    if login_filter not in ["all", "created", "not_created"]:
        login_filter = "all"

    if student_filter not in ["all", "Active", "Inactive"]:
        student_filter = "all"

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # Get overall counts independently of table filters.
        cursor.execute("""
            SELECT
                COUNT(*) AS total_students,

                SUM(
                    CASE
                        WHEN ua.account_id IS NOT NULL THEN 1
                        ELSE 0
                    END
                ) AS accounts_created,

                SUM(
                    CASE
                        WHEN ua.account_id IS NULL THEN 1
                        ELSE 0
                    END
                ) AS accounts_not_created

            FROM Students s

            LEFT JOIN User_Accounts ua
                ON s.student_id = ua.student_id
        """)

        summary = cursor.fetchone()

        # Build the student list query.
        query = """
            SELECT
                s.student_id,
                s.student_name,
                s.department,
                s.program,
                s.account_status,
                ua.username,
                CASE
                    WHEN ua.account_id IS NULL THEN 'Not Created'
                    ELSE 'Created'
                END AS login_status

            FROM Students s

            LEFT JOIN User_Accounts ua
                ON s.student_id = ua.student_id

            WHERE 1 = 1
        """

        params = []

        # Search by student name or student ID.
        if search_query:

            query += """
                AND (
                    s.student_name LIKE %s
                    OR CAST(s.student_id AS CHAR) LIKE %s
                )
            """

            search_pattern = f"%{search_query}%"

            params.extend([
                search_pattern,
                search_pattern
            ])

        # Filter by login account status.
        if login_filter == "created":

            query += " AND ua.account_id IS NOT NULL"

        elif login_filter == "not_created":

            query += " AND ua.account_id IS NULL"

        # Filter by student record status.
        if student_filter != "all":

            query += " AND s.account_status = %s"
            params.append(student_filter)

        query += " ORDER BY s.student_id"

        cursor.execute(query, params)

        students = cursor.fetchall()

        return render_template(
            "admin_students.html",
            students=students,
            summary=summary,
            search_query=search_query,
            login_filter=login_filter,
            student_filter=student_filter
        )

    finally:

        cursor.close()
        connection.close()


# ------------------------------------------------------------
# CREATE STUDENT LOGIN ACCOUNT
# ------------------------------------------------------------

@app.route(
    "/admin/students/<int:student_id>/create-account",
    methods=["POST"]
)
@login_required
@role_required("admin")
def create_student_account(student_id):

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    # Validate submitted fields.
    error_message = validate_new_credentials(
        username, password, confirm_password
    )

    if error_message:
        flash(error_message, "error")
        return redirect(url_for("manage_students"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # Confirm that the student exists and is active.
        cursor.execute("""
            SELECT student_id, account_status
            FROM Students
            WHERE student_id = %s
        """, (student_id,))

        student = cursor.fetchone()

        if not student:

            flash("Student record not found.", "error")
            return redirect(url_for("manage_students"))

        if student["account_status"] != "Active":

            flash("Cannot create an account for an inactive student.", "error")
            return redirect(url_for("manage_students"))

        # Check whether this student already has a login account.
        cursor.execute("""
            SELECT account_id
            FROM User_Accounts
            WHERE student_id = %s
        """, (student_id,))

        existing_account = cursor.fetchone()

        if existing_account:

            flash("This student already has a login account.", "error")
            return redirect(url_for("manage_students"))

        # Check that the username is not already taken.
        cursor.execute("""
            SELECT account_id
            FROM User_Accounts
            WHERE username = %s
        """, (username,))

        if cursor.fetchone():

            flash("This username is already in use.", "error")
            return redirect(url_for("manage_students"))

        # Hash the password before storing it.
        password_hash = hash_password(password)

        # Create the login account.
        cursor.execute("""
            INSERT INTO User_Accounts (
                student_id,
                username,
                password_hash
            )
            VALUES (%s, %s, %s)
        """, (
            student_id,
            username,
            password_hash
        ))

        connection.commit()

        audit(
            "STUDENT_ACCOUNT_CREATED",
            f"student_id={student_id} username={username}"
        )

        flash("Student login account created successfully.", "success")

    except IntegrityError:

        # Safety net: the UNIQUE constraints on username and
        # student_id still protect the data if two admins submit
        # at the same moment.
        connection.rollback()
        flash(
            "Username already exists or an account "
            "was created for this student.",
            "error"
        )

    except Error as error:

        connection.rollback()
        print("Student account creation error:", error)
        flash("Unable to create student account.", "error")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("manage_students"))


# ------------------------------------------------------------
# RESET STUDENT PASSWORD
# ------------------------------------------------------------

@app.route(
    "/admin/students/<int:student_id>/reset-password",
    methods=["POST"]
)
@login_required
@role_required("admin")
def reset_student_password(student_id):

    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    # Validate password fields.
    error_message = validate_password(password, confirm_password)

    if error_message:
        flash(error_message, "error")
        return redirect(url_for("manage_students"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # Check whether the student has an existing login account.
        cursor.execute("""
            SELECT account_id
            FROM User_Accounts
            WHERE student_id = %s
        """, (student_id,))

        account = cursor.fetchone()

        if not account:

            flash("No login account exists for this student.", "error")
            return redirect(url_for("manage_students"))

        # Generate a secure password hash.
        new_password_hash = hash_password(password)

        # Update the existing account.
        cursor.execute("""
            UPDATE User_Accounts
            SET password_hash = %s
            WHERE student_id = %s
        """, (new_password_hash, student_id))

        connection.commit()

        audit("STUDENT_PASSWORD_RESET", f"student_id={student_id}")

        flash("Student password reset successfully.", "success")

    except Error as error:

        connection.rollback()
        print("Student password reset error:", error)
        flash("Unable to reset student password.", "error")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("manage_students"))


# ------------------------------------------------------------
# UPDATE STUDENT ACCOUNT STATUS
# ------------------------------------------------------------

@app.route(
    "/admin/students/<int:student_id>/status",
    methods=["POST"]
)
@login_required
@role_required("admin")
def update_student_status(student_id):

    status = request.form.get("account_status")

    if status not in VALID_ACCOUNT_STATUSES:
        flash("Invalid account status.", "error")
        return redirect(url_for("manage_students"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # Check the record exists first. (MySQL reports rowcount 0
        # when the new value equals the old value, so rowcount alone
        # cannot tell "not found" from "unchanged".)
        cursor.execute("""
            SELECT student_id
            FROM Students
            WHERE student_id = %s
        """, (student_id,))

        if cursor.fetchone() is None:
            flash("Student record not found.", "error")
            return redirect(url_for("manage_students"))

        cursor.execute("""
            UPDATE Students
            SET account_status = %s
            WHERE student_id = %s
        """, (status, student_id))

        connection.commit()

        audit(
            "STUDENT_STATUS_CHANGED",
            f"student_id={student_id} status={status}"
        )

        flash("Student account status updated successfully.", "success")

    except Error as error:

        connection.rollback()
        print("Student status update error:", error)
        flash("Unable to update student status.", "error")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("manage_students"))


# ------------------------------------------------------------
# FACULTY MANAGEMENT
# ------------------------------------------------------------

@app.route("/admin/faculty")
@login_required
@role_required("admin")
def manage_faculty():

    search_query = request.args.get("search", "").strip()
    login_filter = request.args.get("login_status", "all")
    faculty_filter = request.args.get("faculty_status", "all")

    if login_filter not in ["all", "created", "not_created"]:
        login_filter = "all"

    if faculty_filter not in ["all", "Active", "Inactive"]:
        faculty_filter = "all"

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                COUNT(*) AS total_faculty,

                SUM(
                    CASE
                        WHEN ua.account_id IS NOT NULL THEN 1
                        ELSE 0
                    END
                ) AS accounts_created,

                SUM(
                    CASE
                        WHEN ua.account_id IS NULL THEN 1
                        ELSE 0
                    END
                ) AS accounts_not_created

            FROM Faculty_Advisors f

            LEFT JOIN User_Accounts ua
                ON f.faculty_id = ua.faculty_id
        """)

        summary = cursor.fetchone()

        query = """
            SELECT
                f.faculty_id,
                f.faculty_name,
                f.department,
                f.account_status,
                ua.username,

                (
                    SELECT COUNT(*)
                    FROM Club_Advisor ca
                    WHERE ca.faculty_id = f.faculty_id
                      AND ca.assignment_status = 'Active'
                      AND ca.end_date IS NULL
                ) AS clubs_advised

            FROM Faculty_Advisors f

            LEFT JOIN User_Accounts ua
                ON f.faculty_id = ua.faculty_id

            WHERE 1 = 1
        """

        params = []

        if search_query:

            query += """
                AND (
                    f.faculty_name LIKE %s
                    OR CAST(f.faculty_id AS CHAR) LIKE %s
                )
            """

            search_pattern = f"%{search_query}%"
            params.extend([search_pattern, search_pattern])

        if login_filter == "created":
            query += " AND ua.account_id IS NOT NULL"

        elif login_filter == "not_created":
            query += " AND ua.account_id IS NULL"

        if faculty_filter != "all":
            query += " AND f.account_status = %s"
            params.append(faculty_filter)

        query += " ORDER BY f.faculty_id"

        cursor.execute(query, params)

        faculty = cursor.fetchall()

        return render_template(
            "admin_faculty.html",
            faculty=faculty,
            summary=summary,
            search_query=search_query,
            login_filter=login_filter,
            faculty_filter=faculty_filter
        )

    finally:

        cursor.close()
        connection.close()


@app.route("/admin/faculty/<int:faculty_id>/status", methods=["POST"])
@login_required
@role_required("admin")
def update_faculty_status(faculty_id):

    status = request.form.get("account_status")

    if status not in VALID_ACCOUNT_STATUSES:
        flash("Invalid account status.", "error")
        return redirect(url_for("manage_faculty"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT faculty_id
            FROM Faculty_Advisors
            WHERE faculty_id = %s
        """, (faculty_id,))

        if cursor.fetchone() is None:
            flash("Faculty record not found.", "error")
            return redirect(url_for("manage_faculty"))

        cursor.execute("""
            UPDATE Faculty_Advisors
            SET account_status = %s
            WHERE faculty_id = %s
        """, (status, faculty_id))

        connection.commit()

        audit(
            "FACULTY_STATUS_CHANGED",
            f"faculty_id={faculty_id} status={status}"
        )

        flash("Faculty account status updated.", "success")

    except Error as error:

        connection.rollback()
        print("Faculty status update error:", error)
        flash("Unable to update faculty status.", "error")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("manage_faculty"))


# ------------------------------------------------------------
# CREATE FACULTY LOGIN ACCOUNT
# ------------------------------------------------------------

@app.route(
    "/admin/faculty/<int:faculty_id>/create-account",
    methods=["POST"]
)
@login_required
@role_required("admin")
def create_faculty_account(faculty_id):

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    error_message = validate_new_credentials(
        username, password, confirm_password
    )

    if error_message:
        flash(error_message, "error")
        return redirect(url_for("manage_faculty"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT faculty_id, account_status
            FROM Faculty_Advisors
            WHERE faculty_id = %s
        """, (faculty_id,))

        member = cursor.fetchone()

        if not member:
            flash("Faculty record not found.", "error")
            return redirect(url_for("manage_faculty"))

        if member["account_status"] != "Active":
            flash(
                "Cannot create an account for an inactive faculty member.",
                "error"
            )
            return redirect(url_for("manage_faculty"))

        cursor.execute("""
            SELECT account_id
            FROM User_Accounts
            WHERE faculty_id = %s
        """, (faculty_id,))

        if cursor.fetchone():
            flash("This faculty member already has a login account.", "error")
            return redirect(url_for("manage_faculty"))

        cursor.execute("""
            SELECT account_id
            FROM User_Accounts
            WHERE username = %s
        """, (username,))

        if cursor.fetchone():
            flash("This username is already in use.", "error")
            return redirect(url_for("manage_faculty"))

        cursor.execute("""
            INSERT INTO User_Accounts (
                faculty_id,
                username,
                password_hash
            )
            VALUES (%s, %s, %s)
        """, (faculty_id, username, hash_password(password)))

        connection.commit()

        audit(
            "FACULTY_ACCOUNT_CREATED",
            f"faculty_id={faculty_id} username={username}"
        )

        flash("Faculty login account created successfully.", "success")

    except IntegrityError:

        connection.rollback()
        flash(
            "Username already exists or an account was created for "
            "this faculty member.",
            "error"
        )

    except Error as error:

        connection.rollback()
        print("Faculty account creation error:", error)
        flash("Unable to create faculty account.", "error")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("manage_faculty"))


# ------------------------------------------------------------
# RESET FACULTY PASSWORD
# ------------------------------------------------------------

@app.route(
    "/admin/faculty/<int:faculty_id>/reset-password",
    methods=["POST"]
)
@login_required
@role_required("admin")
def reset_faculty_password(faculty_id):

    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    error_message = validate_password(password, confirm_password)

    if error_message:
        flash(error_message, "error")
        return redirect(url_for("manage_faculty"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT account_id
            FROM User_Accounts
            WHERE faculty_id = %s
        """, (faculty_id,))

        if not cursor.fetchone():
            flash("No login account exists for this faculty member.", "error")
            return redirect(url_for("manage_faculty"))

        cursor.execute("""
            UPDATE User_Accounts
            SET password_hash = %s
            WHERE faculty_id = %s
        """, (hash_password(password), faculty_id))

        connection.commit()

        audit("FACULTY_PASSWORD_RESET", f"faculty_id={faculty_id}")

        flash("Faculty password reset successfully.", "success")

    except Error as error:

        connection.rollback()
        print("Faculty password reset error:", error)
        flash("Unable to reset faculty password.", "error")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("manage_faculty"))


# ------------------------------------------------------------
# PRESIDENT AND ADVISOR ASSIGNMENTS — VIEW
# ------------------------------------------------------------

@app.route("/admin/assignments")
@login_required
@role_required("admin")
def manage_assignments():

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        # Every club with its current president and advisor.
        cursor.execute("""
            SELECT
                c.club_id,
                c.club_name,
                c.club_status,

                (
                    SELECT cp.student_id
                    FROM Club_President cp
                    WHERE cp.club_id = c.club_id
                      AND cp.assignment_status = 'Active'
                      AND cp.end_date IS NULL
                    ORDER BY cp.start_date DESC
                    LIMIT 1
                ) AS president_id,

                (
                    SELECT s.student_name
                    FROM Club_President cp
                    JOIN Students s ON cp.student_id = s.student_id
                    WHERE cp.club_id = c.club_id
                      AND cp.assignment_status = 'Active'
                      AND cp.end_date IS NULL
                    ORDER BY cp.start_date DESC
                    LIMIT 1
                ) AS president_name,

                (
                    SELECT ca.faculty_id
                    FROM Club_Advisor ca
                    WHERE ca.club_id = c.club_id
                      AND ca.assignment_status = 'Active'
                      AND ca.end_date IS NULL
                    ORDER BY ca.start_date DESC
                    LIMIT 1
                ) AS advisor_id,

                (
                    SELECT f.faculty_name
                    FROM Club_Advisor ca
                    JOIN Faculty_Advisors f ON ca.faculty_id = f.faculty_id
                    WHERE ca.club_id = c.club_id
                      AND ca.assignment_status = 'Active'
                      AND ca.end_date IS NULL
                    ORDER BY ca.start_date DESC
                    LIMIT 1
                ) AS advisor_name

            FROM Clubs c

            ORDER BY c.club_name
        """)

        clubs = cursor.fetchall()

        # Active student members of each club (president candidates).
        cursor.execute("""
            SELECT m.club_id, s.student_id, s.student_name
            FROM Memberships m
            JOIN Students s ON m.student_id = s.student_id
            WHERE m.membership_status = 'Active'
              AND s.account_status = 'Active'
            ORDER BY s.student_name
        """)

        members_by_club = {}

        for row in cursor.fetchall():
            members_by_club.setdefault(row["club_id"], []).append(row)

        # Active faculty (advisor candidates).
        cursor.execute("""
            SELECT faculty_id, faculty_name
            FROM Faculty_Advisors
            WHERE account_status = 'Active'
            ORDER BY faculty_name
        """)

        faculty = cursor.fetchall()

        return render_template(
            "admin_assignments.html",
            clubs=clubs,
            members_by_club=members_by_club,
            faculty=faculty
        )

    finally:

        cursor.close()
        connection.close()


# ------------------------------------------------------------
# ASSIGN CLUB PRESIDENT
# ------------------------------------------------------------

@app.route("/admin/presidents/assign", methods=["POST"])
@login_required
@role_required("admin")
def assign_president():

    student_id = request.form.get("student_id")
    club_id = request.form.get("club_id")

    try:

        student_id = int(student_id)
        club_id = int(club_id)

    except (ValueError, TypeError):

        flash("Invalid student or club ID.", "error")
        return redirect(url_for("manage_assignments"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT club_status
            FROM Clubs
            WHERE club_id = %s
        """, (club_id,))

        club = cursor.fetchone()

        if club is None or club["club_status"] != "Active":
            flash("The club must exist and be active.", "error")
            return redirect(url_for("manage_assignments"))

        # Student must be an active club member with an active record.

        cursor.execute("""
            SELECT m.student_id
            FROM Memberships m
            JOIN Students s ON m.student_id = s.student_id
            WHERE m.student_id = %s
              AND m.club_id = %s
              AND m.membership_status = 'Active'
              AND s.account_status = 'Active'
        """, (student_id, club_id))

        if cursor.fetchone() is None:
            flash(
                "The student must be an active member of this club.",
                "error"
            )
            return redirect(url_for("manage_assignments"))

        cursor.execute("""
            SELECT president_assignment_id
            FROM Club_President
            WHERE club_id = %s
              AND student_id = %s
              AND assignment_status = 'Active'
              AND end_date IS NULL
        """, (club_id, student_id))

        if cursor.fetchone() is not None:
            flash("This student is already the club president.", "error")
            return redirect(url_for("manage_assignments"))

        connection.start_transaction()

        # End previous active presidency for this club.

        cursor.execute("""
            UPDATE Club_President
            SET end_date = %s,
                assignment_status = 'Inactive'
            WHERE club_id = %s
              AND assignment_status = 'Active'
              AND end_date IS NULL
        """, (date.today(), club_id))

        # Create new assignment.

        cursor.execute("""
            INSERT INTO Club_President (
                student_id,
                club_id,
                start_date,
                end_date,
                assignment_status
            )
            VALUES (%s, %s, %s, NULL, 'Active')
        """, (student_id, club_id, date.today()))

        connection.commit()

        audit(
            "PRESIDENT_ASSIGNED",
            f"club_id={club_id} student_id={student_id}"
        )

        flash("Club president assigned successfully.", "success")

    except Error as error:

        connection.rollback()
        print("President assignment error:", error)
        flash("Unable to assign club president.", "error")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("manage_assignments"))


# ------------------------------------------------------------
# ASSIGN FACULTY ADVISOR
# ------------------------------------------------------------

@app.route("/admin/advisors/assign", methods=["POST"])
@login_required
@role_required("admin")
def assign_advisor():

    faculty_id = request.form.get("faculty_id")
    club_id = request.form.get("club_id")

    try:

        faculty_id = int(faculty_id)
        club_id = int(club_id)

    except (ValueError, TypeError):

        flash("Invalid faculty or club ID.", "error")
        return redirect(url_for("manage_assignments"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT club_status
            FROM Clubs
            WHERE club_id = %s
        """, (club_id,))

        club = cursor.fetchone()

        if club is None or club["club_status"] != "Active":
            flash("The club must exist and be active.", "error")
            return redirect(url_for("manage_assignments"))

        cursor.execute("""
            SELECT account_status
            FROM Faculty_Advisors
            WHERE faculty_id = %s
        """, (faculty_id,))

        member = cursor.fetchone()

        if member is None or member["account_status"] != "Active":
            flash("The faculty member must exist and be active.", "error")
            return redirect(url_for("manage_assignments"))

        cursor.execute("""
            SELECT advisor_assignment_id
            FROM Club_Advisor
            WHERE club_id = %s
              AND faculty_id = %s
              AND assignment_status = 'Active'
              AND end_date IS NULL
        """, (club_id, faculty_id))

        if cursor.fetchone() is not None:
            flash(
                "This faculty member is already the club's advisor.",
                "error"
            )
            return redirect(url_for("manage_assignments"))

        connection.start_transaction()

        cursor.execute("""
            UPDATE Club_Advisor
            SET end_date = %s,
                assignment_status = 'Inactive'
            WHERE club_id = %s
              AND assignment_status = 'Active'
              AND end_date IS NULL
        """, (date.today(), club_id))

        cursor.execute("""
            INSERT INTO Club_Advisor (
                faculty_id,
                club_id,
                start_date,
                end_date,
                assignment_status
            )
            VALUES (%s, %s, %s, NULL, 'Active')
        """, (faculty_id, club_id, date.today()))

        connection.commit()

        audit(
            "ADVISOR_ASSIGNED",
            f"club_id={club_id} faculty_id={faculty_id}"
        )

        flash("Faculty advisor assigned successfully.", "success")

    except Error as error:

        connection.rollback()
        print("Advisor assignment error:", error)
        flash("Unable to assign advisor.", "error")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("manage_assignments"))


# ------------------------------------------------------------
# ADMIN VIEW ALL APPLICATIONS
# ------------------------------------------------------------

@app.route("/admin/applications")
@login_required
@role_required("admin")
def admin_applications():

    status_filter = request.args.get("status", "all")

    if status_filter not in VALID_APPLICATION_FILTERS:
        status_filter = "all"

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:

        query = """
            SELECT
                a.*,
                c.club_name,
                s.student_name

            FROM Applications a

            JOIN Clubs c
                ON a.club_id = c.club_id

            JOIN Students s
                ON a.student_id = s.student_id
        """

        params = []

        if status_filter != "all":
            query += " WHERE a.application_status = %s"
            params.append(status_filter)

        query += " ORDER BY a.submission_date DESC"

        cursor.execute(query, params)

        applications = cursor.fetchall()

        decisions = get_decisions_by_application(
            cursor,
            [a["application_id"] for a in applications]
        )

        return render_template(
            "admin_applications.html",
            applications=applications,
            decisions=decisions,
            status_filter=status_filter
        )

    finally:

        cursor.close()
        connection.close()


# ------------------------------------------------------------
# ADMIN APPROVE / REJECT APPLICATION
# ------------------------------------------------------------

@app.route(
    "/admin/applications/<int:application_id>/decision",
    methods=["POST"]
)
@login_required
@role_required("admin")
def admin_decision(application_id):

    decision = request.form.get("decision")
    comments = request.form.get("comments", "").strip()

    if decision not in ["Approved", "Rejected"]:
        flash("Invalid decision.", "error")
        return redirect(url_for("admin_applications"))

    connection = get_db_connection()

    # A dictionary cursor is required because
    # update_application_status() reads result columns by name.
    cursor = connection.cursor(dictionary=True)

    try:

        admin_id = session["user_id"]

        cursor.execute("""
            SELECT application_id
            FROM Applications
            WHERE application_id = %s
        """, (application_id,))

        if cursor.fetchone() is None:
            flash("Application not found.", "error")
            return redirect(url_for("admin_applications"))

        connection.start_transaction()

        cursor.execute("""
            INSERT INTO Approval_Decisions (
                application_id,
                faculty_id,
                admin_id,
                decision,
                comments,
                decision_date
            )
            VALUES (%s, NULL, %s, %s, %s, NOW())

            ON DUPLICATE KEY UPDATE
                decision = VALUES(decision),
                comments = VALUES(comments),
                decision_date = NOW()
        """, (
            application_id,
            admin_id,
            decision,
            comments
        ))

        new_status = update_application_status(cursor, application_id)

        connection.commit()

        audit(
            "ADMIN_DECISION",
            f"application_id={application_id} decision={decision} "
            f"new_status={new_status}"
        )

        flash(
            f"Administrative decision recorded. Application status is "
            f"now {new_status}.",
            "success"
        )

    except Error as error:

        connection.rollback()
        print("Admin decision error:", error)
        flash("Unable to record administrative decision.", "error")

    finally:

        cursor.close()
        connection.close()

    return redirect(url_for("admin_applications"))


# ============================================================
# 12. ERROR HANDLING
# ============================================================
# Each handler renders the shared error.html page instead of
# returning a bare string.

@app.errorhandler(400)
def bad_request(error):

    return render_template(
        "error.html",
        code=400,
        title="Request could not be processed",
        message=(
            "The form was missing its security token or the session "
            "expired. Go back, refresh the page and try again."
        )
    ), 400


@app.errorhandler(403)
def forbidden(error):

    return render_template(
        "error.html",
        code=403,
        title="Access denied",
        message="You do not have permission to access this page."
    ), 403


@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "error.html",
        code=404,
        title="Page not found",
        message="The page you requested does not exist."
    ), 404


@app.errorhandler(Error)
def database_error(error):

    # Any MySQL error that a route did not handle itself.
    print("Unhandled database error:", error)

    return render_template(
        "error.html",
        code=500,
        title="Database error",
        message=(
            "The system could not complete the request because of a "
            "database problem. Please try again later."
        )
    ), 500


@app.errorhandler(DatabaseConfigError)
def database_config_error(error):

    print("Database configuration error:", error)

    return render_template(
        "error.html",
        code=500,
        title="Database not configured",
        message=(
            "The MYSQL_PASSWORD environment variable is not set. "
            "Set it in the terminal before running app.py."
        )
    ), 500


# ============================================================
# 13. RUN FLASK APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(debug=True)
