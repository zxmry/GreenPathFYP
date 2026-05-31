"""
Route History Service — SQLite version.

Public API is IDENTICAL to the original JSON version so api.py
needs zero changes.  Every function accepts the same parameters
and returns the same data shapes.
"""

import uuid
from datetime import datetime
from app.database import get_connection


# ── Public API ────────────────────────────────────────────────────────────────

def save_route(phone, addresses, optimized_route, vehicle_type, metrics, time_windows=None):
    """
    Persist a completed route optimisation.

    Inserts one row into routes, N rows into route_addresses
    (original + optimised sequences) and optionally into time_windows.

    Returns the new route id (8-char string).
    """
    route_id  = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    conn = get_connection()
    with conn:
        # 1. Insert main route record
        conn.execute("""
            INSERT INTO routes (
                id, phone, timestamp, vehicle_type,
                orig_dist_km, opt_dist_km, dist_saved_km,
                time_saved_min, co2_saved_kg, fuel_saved_rm,
                orig_time_min, opt_time_min
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            route_id, phone, timestamp, vehicle_type,
            metrics.get("original_distance_km",    0),
            metrics.get("optimized_distance_km",   0),
            metrics.get("distance_savings_km",     0),
            metrics.get("time_saved_minutes",      0),
            metrics.get("co2_saved_kg",            0),
            metrics.get("fuel_cost_saved_rm",      0),
            metrics.get("original_travel_minutes", 0),
            metrics.get("optimized_travel_minutes",0),
        ))

        # 2. Original address sequence (is_optimised = 0)
        conn.executemany("""
            INSERT INTO route_addresses (route_id, address, position, is_optimised)
            VALUES (?,?,?,0)
        """, [(route_id, addr, i) for i, addr in enumerate(addresses)])

        # 3. Optimised address sequence (is_optimised = 1)
        conn.executemany("""
            INSERT INTO route_addresses (route_id, address, position, is_optimised)
            VALUES (?,?,?,1)
        """, [(route_id, addr, i) for i, addr in enumerate(optimized_route)])

        # 4. Time windows (optional)
        if time_windows:
            conn.executemany("""
                INSERT INTO time_windows (route_id, address, earliest, latest)
                VALUES (?,?,?,?)
            """, [
                (route_id, tw.get("address",""), tw.get("earliest"), tw.get("latest"))
                for tw in time_windows
            ])

    conn.close()
    print(f"   ✅ Route {route_id} saved to SQLite for user {phone}")
    return route_id


def get_user_routes(phone, limit=20):
    """
    Return the most recent `limit` route records for the user.
    Returns a list of dicts matching the original JSON shape.
    """
    conn = get_connection()

    # Fetch route rows newest-first
    rows = conn.execute("""
        SELECT * FROM routes
        WHERE phone = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (phone, limit)).fetchall()

    result = []
    for row in rows:
        rid = row["id"]

        # Original addresses in order
        orig_addrs = [
            r["address"] for r in conn.execute("""
                SELECT address FROM route_addresses
                WHERE route_id = ? AND is_optimised = 0
                ORDER BY position
            """, (rid,)).fetchall()
        ]

        # Optimised addresses in order
        opt_addrs = [
            r["address"] for r in conn.execute("""
                SELECT address FROM route_addresses
                WHERE route_id = ? AND is_optimised = 1
                ORDER BY position
            """, (rid,)).fetchall()
        ]

        # Time windows for this route
        tws = [
            {"address": r["address"], "earliest": r["earliest"], "latest": r["latest"]}
            for r in conn.execute("""
                SELECT address, earliest, latest FROM time_windows
                WHERE route_id = ?
            """, (rid,)).fetchall()
        ]

        record = {
            "id":              rid,
            "timestamp":       row["timestamp"],
            "addresses":       orig_addrs,
            "optimized_route": opt_addrs,
            "vehicle_type":    row["vehicle_type"],
            "metrics": {
                "original_distance_km":    row["orig_dist_km"],
                "optimized_distance_km":   row["opt_dist_km"],
                "distance_saved_km":       row["dist_saved_km"],
                "time_saved_minutes":      row["time_saved_min"],
                "co2_saved_kg":            row["co2_saved_kg"],
                "fuel_cost_saved_rm":      row["fuel_saved_rm"],
                "original_travel_minutes": row["orig_time_min"],
                "optimized_travel_minutes":row["opt_time_min"],
            },
        }
        if tws:
            record["time_windows"] = tws

        result.append(record)

    conn.close()
    return result


def get_cumulative_stats(phone):
    """
    Compute cumulative sustainability stats using a single SQL aggregate query.
    Much more efficient than loading all records into Python and summing in a loop.
    """
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COUNT(*)              AS total_routes,
            ROUND(SUM(co2_saved_kg),      2) AS total_co2_saved_kg,
            ROUND(SUM(fuel_saved_rm),     2) AS total_fuel_saved_rm,
            ROUND(SUM(dist_saved_km),     2) AS total_distance_saved_km,
            ROUND(SUM(time_saved_min),    1) AS total_time_saved_min
        FROM routes
        WHERE phone = ?
    """, (phone,)).fetchone()
    conn.close()

    if not row or row["total_routes"] == 0:
        return {
            "total_routes": 0,
            "total_co2_saved_kg": 0,
            "total_fuel_saved_rm": 0,
            "total_distance_saved_km": 0,
            "total_time_saved_min": 0,
        }

    return {
        "total_routes":            row["total_routes"],
        "total_co2_saved_kg":      row["total_co2_saved_kg"]      or 0,
        "total_fuel_saved_rm":     row["total_fuel_saved_rm"]      or 0,
        "total_distance_saved_km": row["total_distance_saved_km"] or 0,
        "total_time_saved_min":    row["total_time_saved_min"]     or 0,
    }


def delete_route(phone, route_id):
    """
    Delete a specific route for the user.
    CASCADE in the schema automatically removes linked route_addresses
    and time_windows rows.
    """
    conn = get_connection()
    with conn:
        conn.execute("""
            DELETE FROM routes WHERE id = ? AND phone = ?
        """, (route_id, phone))
    conn.close()
    return True
