# dev_tests (optional)

Automated end-to-end tests for the Flask app that do **not** need MySQL.

- `mysql/connector/__init__.py` is a small stand-in for `mysql.connector` that runs the
  app's SQL on SQLite. It is only loaded by `run_tests.py`; `app.py` itself always uses
  the real `mysql-connector-python` package.
- `build_db.py` recreates the `SEproject.sql` tables (same keys and CHECK constraints)
  in a temporary SQLite file and loads the same data.
- `run_tests.py` logs in as each role with Flask's test client and runs 112 checks.

Run from the project folder:

    python dev_tests/run_tests.py .

Your MySQL database is never touched. The run appends entries to `audit.log`;
delete that file afterwards if you want a clean log.
