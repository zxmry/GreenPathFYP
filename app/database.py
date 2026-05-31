"""
GreenPath — SQLite database layer.

Replaces users.json and routes.json with a proper relational database.

Schema
------
users
    phone       TEXT  PRIMARY KEY
    name        TEXT  NOT NULL
    password    TEXT  NOT NULL
    vehicle     TEXT  NOT NULL
    created_at  TEXT  NOT NULL

routes
    id              TEXT  PRIMARY KEY          -- 8-char UUID fragment
    phone           TEXT  NOT NULL             -- FK → users.phone
    timestamp       TEXT  NOT NULL
    vehicle_type    TEXT  NOT NULL
    orig_dist_km    REAL
    opt_dist_km     REAL
    dist_saved_km   REAL
    time_saved_min  REAL
    co2_saved_kg    REAL
    fuel_saved_rm   REAL
    orig_time_min   REAL
    opt_time_min    REAL

route_addresses
    id          INTEGER  PRIMARY KEY AUTOINCREMENT
    route_id    TEXT     NOT NULL   -- FK → routes.id
    address     TEXT     NOT NULL
    position    INTEGER  NOT NULL   -- 0-based order in the original list
    is_optimised INTEGER NOT NULL DEFAULT 0  -- 1 = optimised sequence

time_windows
    id          INTEGER  PRIMARY KEY AUTOINCREMENT
    route_id    TEXT     NOT NULL   -- FK → routes.id
    address     TEXT     NOT NULL
    earliest    TEXT
    latest      TEXT
"""

import sqlite3
import os
from config import DB_PATH


def get_connection():
    """
    Return a configured sqlite3 connection.
    Row factory is set so rows behave like dicts.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # access columns by name: row["phone"]
    conn.execute("PRAGMA journal_mode=WAL") # safe for concurrent readers
    conn.execute("PRAGMA foreign_keys=ON")  # enforce FK constraints
    return conn


def init_db():
    """
    Create all tables if they do not already exist.
    Called once at application startup from create_app().
    Safe to call multiple times — uses IF NOT EXISTS.
    """
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                phone       TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                password    TEXT NOT NULL,
                vehicle     TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS routes (
                id              TEXT PRIMARY KEY,
                phone           TEXT NOT NULL REFERENCES users(phone) ON DELETE CASCADE,
                timestamp       TEXT NOT NULL,
                vehicle_type    TEXT NOT NULL,
                orig_dist_km    REAL DEFAULT 0,
                opt_dist_km     REAL DEFAULT 0,
                dist_saved_km   REAL DEFAULT 0,
                time_saved_min  REAL DEFAULT 0,
                co2_saved_kg    REAL DEFAULT 0,
                fuel_saved_rm   REAL DEFAULT 0,
                orig_time_min   REAL DEFAULT 0,
                opt_time_min    REAL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_routes_phone
                ON routes(phone);

            CREATE INDEX IF NOT EXISTS idx_routes_timestamp
                ON routes(phone, timestamp DESC);

            CREATE TABLE IF NOT EXISTS route_addresses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id     TEXT    NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
                address      TEXT    NOT NULL,
                position     INTEGER NOT NULL,
                is_optimised INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS time_windows (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id    TEXT NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
                address     TEXT NOT NULL,
                earliest    TEXT,
                latest      TEXT
            );
        """)
    conn.close()
    print("✅ SQLite database initialised:", DB_PATH)
