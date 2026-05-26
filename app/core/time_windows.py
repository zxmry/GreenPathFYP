"""
Time Window Validation for GreenPath (FYP2).

Allows users to set earliest and latest arrival times per delivery stop.
The GA still determines the route sequence; this module checks whether
the optimised sequence can satisfy the time windows and flags violations.

This is a soft-constraint implementation — the GA is not re-architected
to hard-enforce windows (that would require VRPTW which is out of scope),
but violations are clearly reported to the user so they can adjust
departure time or stop order manually.

Time window format expected from frontend
-----------------------------------------
[
  {"address": "KL Tower, KL",  "earliest": "09:00", "latest": "11:00"},
  {"address": "Bangsar, KL",   "earliest": "14:00", "latest": "16:30"}
]
All times are 24-hour "HH:MM" strings.
"""

from datetime import datetime, timedelta


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_time(time_str):
    """Parse "HH:MM" → datetime.time object.  Returns None on failure."""
    try:
        return datetime.strptime(time_str.strip(), "%H:%M").time()
    except (ValueError, AttributeError):
        return None


def _time_to_minutes(t):
    """datetime.time → minutes since midnight."""
    return t.hour * 60 + t.minute


# ── Public API ────────────────────────────────────────────────────────────────

def validate_time_windows(time_windows):
    """
    Basic sanity check on the time window list supplied by the user.

    Returns
    -------
    (bool, str)  — (is_valid, error_message_or_empty_string)
    """
    if not time_windows:
        return True, ""

    for tw in time_windows:
        if "address" not in tw:
            return False, "Each time window must include an 'address' field."

        earliest = _parse_time(tw.get("earliest", ""))
        latest   = _parse_time(tw.get("latest",   ""))

        if tw.get("earliest") and earliest is None:
            return False, f"Invalid earliest time '{tw['earliest']}' for {tw['address']}."
        if tw.get("latest") and latest is None:
            return False, f"Invalid latest time '{tw['latest']}' for {tw['address']}."
        if earliest and latest and earliest >= latest:
            return False, (
                f"Earliest time must be before latest time for {tw['address']}."
            )

    return True, ""


def check_route_feasibility(
    optimized_addresses,
    time_metrics,
    time_windows,
    departure_time="08:00",
):
    """
    Simulate the optimised route against user-defined time windows and
    report whether each stop can be reached within its window.

    Parameters
    ----------
    optimized_addresses : list[str]
        Addresses in the GA's optimised order (first = depot, may repeat at end).
    time_metrics        : dict
        From calculate_time_metrics() — contains optimized_travel_minutes,
        num_stops, stop_time_minutes, average_speed_kmh.
    time_windows        : list[dict]
        [{"address": ..., "earliest": "HH:MM", "latest": "HH:MM"}, ...]
    departure_time      : str
        "HH:MM" — when the driver leaves the depot.

    Returns
    -------
    dict with keys:
        feasible      : bool   — True if no window is violated
        violations    : list   — list of violation description strings
        stop_schedule : list   — [{address, estimated_arrival, status}, ...]
    """
    if not time_windows:
        return {"feasible": True, "violations": [], "stop_schedule": []}

    # Build a lookup: address → {earliest_min, latest_min}
    window_map = {}
    for tw in time_windows:
        e = _parse_time(tw.get("earliest", ""))
        l = _parse_time(tw.get("latest",   ""))
        window_map[tw["address"]] = {
            "earliest_min": _time_to_minutes(e) if e else None,
            "latest_min":   _time_to_minutes(l) if l else None,
        }

    # Simulation parameters
    dep_t = _parse_time(departure_time) or _parse_time("08:00")
    current_min = _time_to_minutes(dep_t)

    stop_time_min   = time_metrics.get("stop_time_minutes", 5)
    total_opt_min   = time_metrics.get("optimized_travel_minutes", 0)
    num_stops       = time_metrics.get("num_stops", 1)
    # Average per-leg travel time (excluding stop time)
    total_stop_time = num_stops * stop_time_min
    total_road_min  = max(total_opt_min - total_stop_time, 0)
    per_leg_min     = total_road_min / max(num_stops, 1)

    # Walk through stops (skip first=depot, skip last if it repeats depot)
    stops_only = optimized_addresses[1:]
    if stops_only and stops_only[-1] == optimized_addresses[0]:
        stops_only = stops_only[:-1]

    schedule   = []
    violations = []

    for addr in stops_only:
        current_min += per_leg_min   # travel to this stop
        arrival_h = int(current_min // 60) % 24
        arrival_m = int(current_min % 60)
        arrival_str = f"{arrival_h:02d}:{arrival_m:02d}"

        status = "on_time"
        window = window_map.get(addr)

        if window:
            e_min = window["earliest_min"]
            l_min = window["latest_min"]

            if e_min and current_min < e_min:
                # Arrived too early — wait until window opens
                wait = e_min - current_min
                current_min = e_min
                status = f"early_wait_{int(wait)}min"
            elif l_min and current_min > l_min:
                status = "violated"
                violations.append(
                    f"'{addr}': estimated arrival {arrival_str} is after "
                    f"latest window {_minutes_to_str(l_min)}."
                )

        schedule.append({
            "address":           addr,
            "estimated_arrival": arrival_str,
            "status":            status,
            "window":            window_map.get(addr),
        })

        current_min += stop_time_min   # time spent at this stop

    return {
        "feasible":      len(violations) == 0,
        "violations":    violations,
        "stop_schedule": schedule,
    }


def _minutes_to_str(minutes):
    h = int(minutes // 60) % 24
    m = int(minutes % 60)
    return f"{h:02d}:{m:02d}"