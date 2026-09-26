"""
wsgi.py — production entry point.

Used by a WSGI server such as gunicorn, e.g. on Render:

    gunicorn wsgi:app --bind 0.0.0.0:$PORT

Local development should keep using run_dashboard.py, which uses
Flask's built-in dev server and auto-opens a browser tab.
"""
from netdiag.webapp import app

if __name__ == "__main__":
    app.run()
