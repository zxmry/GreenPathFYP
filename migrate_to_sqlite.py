"""
migrate_to_sqlite.py
--------------------
One-time migration script.

Run this ONCE from the project root after pulling the SQLite update:

    python migrate_to_sqlite.py

What it does:
  1. Reads users.json  -> inserts rows into the users table
  2. Reads routes.json -> inserts rows into routes, route_addresses, time_windows
     (creates a placeholder user row if the phone is not in users.json)

Safe to re-run — uses INSERT OR IGNORE throughout.
"""

import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from app.database import init_db, get_connection
from config import USERS_FILE, ROUTES_FILE


def migrate_users(conn):
    if not os.path.exists(USERS_FILE):
        print(f"   info  {USERS_FILE} not found — skipping user migration.")
        return 0
    with open(USERS_FILE) as f:
        users = json.load(f)
    count = 0
    for phone, data in users.items():
        conn.execute("""
            INSERT OR IGNORE INTO users (phone, name, password, vehicle, created_at)
            VALUES (?,?,?,?,datetime('now','localtime'))
        """, (phone, data.get("name",""), data.get("password",""), data.get("vehicle","car")))
        count += 1
    print(f"   ok    Migrated {count} user(s) from {USERS_FILE}")
    return count


def ensure_user(conn, phone):
    """Insert a placeholder user row if one doesn't exist (for orphaned route data)."""
    conn.execute("""
        INSERT OR IGNORE INTO users (phone, name, password, vehicle, created_at)
        VALUES (?,?,?,?,datetime('now','localtime'))
    """, (phone, f"Imported user {phone}", "changeme", "car"))


def migrate_routes(conn):
    if not os.path.exists(ROUTES_FILE):
        print(f"   info  {ROUTES_FILE} not found — skipping route migration.")
        return 0
    with open(ROUTES_FILE) as f:
        all_routes = json.load(f)
    total = 0
    for phone, route_list in all_routes.items():
        ensure_user(conn, phone)
        for record in route_list:
            rid = record.get("id","")
            if not rid:
                continue
            m = record.get("metrics",{})
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO routes
                        (id,phone,timestamp,vehicle_type,
                         orig_dist_km,opt_dist_km,dist_saved_km,
                         time_saved_min,co2_saved_kg,fuel_saved_rm,
                         orig_time_min,opt_time_min)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    rid, phone,
                    record.get("timestamp",""),
                    record.get("vehicle_type","car"),
                    m.get("original_distance_km",0),
                    m.get("optimized_distance_km",0),
                    m.get("distance_saved_km",0),
                    m.get("time_saved_minutes",0),
                    m.get("co2_saved_kg",0),
                    m.get("fuel_cost_saved_rm",0),
                    m.get("original_travel_minutes",0),
                    m.get("optimized_travel_minutes",0),
                ))
                for i,a in enumerate(record.get("addresses",[])):
                    conn.execute("INSERT OR IGNORE INTO route_addresses (route_id,address,position,is_optimised) VALUES (?,?,?,0)",(rid,a,i))
                for i,a in enumerate(record.get("optimized_route",[])):
                    conn.execute("INSERT OR IGNORE INTO route_addresses (route_id,address,position,is_optimised) VALUES (?,?,?,1)",(rid,a,i))
                for tw in record.get("time_windows",[]):
                    conn.execute("INSERT OR IGNORE INTO time_windows (route_id,address,earliest,latest) VALUES (?,?,?,?)",(rid,tw.get("address",""),tw.get("earliest"),tw.get("latest")))
                total += 1
            except Exception as e:
                print(f"   warn  Skipped route {rid}: {e}")
    print(f"   ok    Migrated {total} route record(s) from {ROUTES_FILE}")
    return total


if __name__ == "__main__":
    print("="*55)
    print("  GreenPath — JSON to SQLite Migration")
    print("="*55)
    init_db()
    conn = get_connection()
    with conn:
        u = migrate_users(conn)
        r = migrate_routes(conn)
    conn.close()
    print("="*55)
    print(f"  Done. {u} user(s), {r} route record(s) migrated.")
    print("  Verify data then delete users.json and routes.json.")
    print("="*55)
