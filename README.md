# Hands Together — Community Support Platform

A responsive website for a Bangladesh community support platform. It includes a home page, account registration and sign-in, a Lost & Found board, and a volunteer opportunities page. Flask handles page routes and JSON APIs; SQLite stores submitted data locally.

## Run it with Flask

Install Python 3 first if it is not already on your computer: https://www.python.org/downloads/windows/. On Windows, the installer should make the `py` command available. Then install the Flask dependency from a terminal in this folder:

```bash
py -m pip install -r requirements.txt
```

Start the Flask development server:

```bash
py app.py
```

Then visit `http://127.0.0.1:5000`. The Flask app provides `/`, `/signup`, `/login`, `/found`, and `/volunteer` routes. Port 5000 avoids conflicting with the earlier static preview server on port 8000.

On Windows, you can instead double-click `run.bat`. It installs the listed Flask dependency and starts the app.

## Project structure

```text
HandsTogether/
├── app.py                  # development entry point
├── hands_together/
│   ├── __init__.py         # application factory and configuration
│   ├── routes.py           # page and JSON API routes
│   └── models.py           # SQLite schema and database helpers
├── templates/              # Flask HTML templates
│   ├── index.html
│   ├── signup.html
│   ├── login.html
│   ├── found.html
│   └── volunteer.html
├── static/                 # browser assets
│   ├── styles.css
│   └── app.js
├── instance/
│   └── hands_together.db   # local data (ignored by Git)
├── requirements.txt
└── run.bat
```

## Prototype scope

Flask serves the pages and API. SQLite creates `instance/hands_together.db` on the first run. Account passwords are stored as salted hashes. Lost and found reports and volunteer interest forms are stored in that local database. Missing-person reports are saved with `pending_review` status and do not appear in public results. Sample listings and dates in the browser are demonstration content. Google Fonts are optional; the site falls back to system fonts if they are unavailable. This is a local project prototype; use a production WSGI server, deployment secret, and reviewed privacy/moderation workflow before putting it on the public internet.

## Volunteer accounts

Choose **Volunteer** from the Join Us account type list to create a volunteer account. Volunteers are sent to `/volunteer/profile` after signing up or signing in. Activity registrations made while signed in are saved to that profile.

## Administrator accounts

The Join Us form offers an **Administrator** account type and asks for an access phrase in a masked field. The local development phrase is `We Shall Overcome`; change it before deployment by setting the `HANDS_TOGETHER_ADMIN_PASS` environment variable. Administrators are sent to `/admin`, where they can review missing-person reports, donation submissions, and complaints.
