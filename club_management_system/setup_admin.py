# ============================================================
# SAU CLUB MANAGEMENT SYSTEM — ADMINISTRATOR ACCOUNT SETUP
# ============================================================
#
# User_Accounts is empty in the original SQL dump, so nobody can
# log in to create accounts through the web interface. This script
# is the controlled way to create an administrator login.
#
# It links a new login to an EXISTING row in Admin_Representatives.
# It never creates new administrator records and never changes
# existing accounts.
#
# Usage (from the project folder, with the virtual env active):
#     python setup_admin.py
#
# Run it once for the first administrator (admin_id 1 by default).
# It can be run again later for other admin_id values.
# ============================================================

import os
import getpass
import mysql.connector

from mysql.connector import Error, IntegrityError
from werkzeug.security import generate_password_hash


MIN_PASSWORD_LENGTH = 12
MAX_USERNAME_LENGTH = 100

DB_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "user": os.environ.get("MYSQL_USER", "root"),
    "database": os.environ.get("MYSQL_DATABASE", "sau_club_management")
}

DEFAULT_ADMIN_ID = 1


def list_admins(cursor):

    cursor.execute(
        """
        SELECT ar.admin_id, ar.admin_name, ar.designation,
               ar.account_status, ua.username
        FROM admin_representatives ar
        LEFT JOIN user_accounts ua ON ar.admin_id = ua.admin_id
        ORDER BY ar.admin_id
        """
    )

    print("\nAdministrator records:")
    print("-" * 72)

    for row in cursor.fetchall():
        login = row["username"] if row["username"] else "(no login)"
        print(
            f"{row['admin_id']:>3}  {row['admin_name'][:30]:<30}  "
            f"{row['account_status']:<8}  {login}"
        )

    print("-" * 72)


def create_admin_account():

    connection = None
    cursor = None

    try:
        print("\n====================================")
        print(" SAU CLUB MANAGEMENT SYSTEM")
        print(" ADMINISTRATOR ACCOUNT SETUP")
        print("====================================\n")

        # Use MYSQL_PASSWORD if it is already set, otherwise ask
        # for it without displaying it.
        mysql_password = os.environ.get("MYSQL_PASSWORD")

        if not mysql_password:
            mysql_password = getpass.getpass("MySQL password: ")

        DB_CONFIG["password"] = mysql_password

        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)

        print("Database connection successful.")

        list_admins(cursor)

        # 1. Choose which administrator record to link.
        admin_input = input(
            f"\nAdmin ID to create a login for "
            f"[default {DEFAULT_ADMIN_ID}]: "
        ).strip()

        try:
            admin_id = int(admin_input) if admin_input else DEFAULT_ADMIN_ID
        except ValueError:
            print("Error: Admin ID must be a number.")
            return

        # 2. Verify administrator record.
        cursor.execute(
            """
            SELECT admin_id, admin_name, designation, account_status
            FROM admin_representatives
            WHERE admin_id = %s
            """,
            (admin_id,)
        )

        admin = cursor.fetchone()

        if admin is None:
            print("Error: Administrator record not found.")
            return

        if admin["account_status"].lower() != "active":
            print("Error: Administrator account is inactive.")
            return

        print("\nAdministrator found:")
        print("Name:", admin["admin_name"])
        print("Designation:", admin["designation"])
        print("Status:", admin["account_status"])

        # 3. Check whether this administrator already has an account.
        cursor.execute(
            """
            SELECT account_id, username
            FROM user_accounts
            WHERE admin_id = %s
            """,
            (admin_id,)
        )

        existing_account = cursor.fetchone()

        if existing_account:
            print("\nAn account already exists for this administrator.")
            print("Username:", existing_account["username"])
            print("No changes have been made.")
            return

        # 4. Get username.
        username = input("\nChoose administrator username: ").strip()

        if not username:
            print("Error: Username cannot be empty.")
            return

        if len(username) > MAX_USERNAME_LENGTH:
            print(f"Error: Username cannot exceed {MAX_USERNAME_LENGTH} "
                  f"characters.")
            return

        if " " in username:
            print("Error: Username cannot contain spaces.")
            return

        # 5. Get password securely.
        password = getpass.getpass("Choose password: ")
        confirm_password = getpass.getpass("Confirm password: ")

        if len(password) < MIN_PASSWORD_LENGTH:
            print(f"Error: Password must contain at least "
                  f"{MIN_PASSWORD_LENGTH} characters.")
            return

        if password != confirm_password:
            print("Error: Passwords do not match.")
            return

        # 6. Hash password using Werkzeug.
        password_hash = generate_password_hash(
            password,
            method="pbkdf2:sha256"
        )

        # 7. Insert account.
        cursor.execute(
            """
            INSERT INTO user_accounts
            (admin_id, username, password_hash)
            VALUES (%s, %s, %s)
            """,
            (admin_id, username, password_hash)
        )

        connection.commit()

        print("\n====================================")
        print(" ADMIN ACCOUNT CREATED SUCCESSFULLY")
        print("====================================")
        print("Administrator:", admin["admin_name"])
        print("Username:", username)
        print("Admin ID:", admin_id)
        print("Password: Stored securely as a hash.")
        print("\nYou can now use these credentials to log in.")

    except IntegrityError:
        if connection and connection.is_connected():
            connection.rollback()

        print("\nError: Username already exists or account constraint failed.")

    except Error as error:
        if connection and connection.is_connected():
            connection.rollback()

        print("\nMySQL error:", error)

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    create_admin_account()
