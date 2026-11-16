"""SQLite persistence helpers and schema for Hands Together."""

import sqlite3
from contextlib import contextmanager

from flask import current_app


def connect_db():
    """Open a SQLite connection configured for this application."""
    db = sqlite3.connect(current_app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


@contextmanager
def database():
    """Provide a transaction that is committed or rolled back safely."""
    db = connect_db()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Create the local database tables when they do not already exist."""
    with database() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                account_type TEXT NOT NULL DEFAULT 'Community member',
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('lost','found','missing')),
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                report_date TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'published',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS volunteer_signups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                activity TEXT NOT NULL,
                full_name TEXT NOT NULL,
                contact TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donor_name TEXT NOT NULL,
                email TEXT NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0),
                method TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','accepted','rejected')),
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                reviewed_by INTEGER REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','resolved','rejected')),
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                reviewed_by INTEGER REFERENCES users(id)
            );
            """
        )
        columns = {row["name"] for row in db.execute("PRAGMA table_info(volunteer_signups)")}
        if "user_id" not in columns:
            db.execute("ALTER TABLE volunteer_signups ADD COLUMN user_id INTEGER REFERENCES users(id)")
