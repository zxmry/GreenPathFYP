"""Route metrics calculations: time, CO₂, and fuel cost.

FYP2 change: all calculations are now vehicle-aware.
Speed, CO₂ rate and stop time differ per vehicle type so results
are accurate whether the user registered as a motorcyclist, car
driver or van operator.
"""

from config import VEHICLE_PARAMS

# ── Vehicle parameter lookup ──────────────────────────────────────────────────

def _get_vehicle_params(vehicle_type):
    """
    Return the correct VEHICLE_PARAMS entry for the given vehicle string.
    Falls back to 'car' if the type is unrecognised.
    """
    v = vehicle_type.lower() if vehicle_type else ""
    if any(w in v for w in ["motorcycle", "moto", "bike"]):
        return VEHICLE_PARAMS["motorcycle"]
    if any(w in v for w in ["van", "truck", "lorry"]):
        return VEHICLE_PARAMS["van"]
    return VEHICLE_PARAMS["car"]   # default


# ── Time & CO₂ metrics ────────────────────────────────────────────────────────

def calculate_time_metrics(
    original_distance_km,
    optimized_distance_km,
    num_stops,
    vehicle_type="car",
):
    """
    Calculate realistic time and CO₂ metrics for delivery routes.

    Now vehicle-aware: speed, traffic factor, stop time and CO₂
    rate all vary per vehicle type.

    Parameters
    ----------
    original_distance_km  : float
    optimized_distance_km : float
    num_stops             : int   — number of delivery stops (excl. return)
    vehicle_type          : str   — from user profile ("motorcycle"/"car"/"van")

    Returns
    -------
    dict with all time, distance and CO₂ metrics.
    """
    params = _get_vehicle_params(vehicle_type)

    speed_kmh      = params["average_speed_kmh"]
    traffic_factor = params["traffic_factor"]
    stop_time_min  = params["stop_time_minutes"]
    co2_per_km     = params["co2_per_km"]

    # Travel time (hours, road only)
    orig_travel_h = (original_distance_km  / speed_kmh) * traffic_factor
    opt_travel_h  = (optimized_distance_km / speed_kmh) * traffic_factor

    # Stop time (same number of stops for both routes)
    stop_time_h = (num_stops * stop_time_min) / 60

    # Total time (hours → minutes)
    orig_total_min = (orig_travel_h + stop_time_h) * 60
    opt_total_min  = (opt_travel_h  + stop_time_h) * 60
    time_saved_min = orig_total_min - opt_total_min

    # Distance savings
    dist_saved_km = original_distance_km - optimized_distance_km
    dist_savings_pct = (
        (dist_saved_km / original_distance_km) * 100
        if original_distance_km > 0 else 0
    )
    time_savings_pct = (
        (time_saved_min / orig_total_min) * 100
        if orig_total_min > 0 else 0
    )

    # CO₂ (vehicle-specific rate)
    orig_co2_kg = original_distance_km  * co2_per_km
    opt_co2_kg  = optimized_distance_km * co2_per_km
    co2_saved_kg = orig_co2_kg - opt_co2_kg

    return {
        "original_travel_minutes":   round(orig_total_min, 1),
        "optimized_travel_minutes":  round(opt_total_min, 1),
        "time_saved_minutes":        round(time_saved_min, 1),
        "distance_savings_km":       round(dist_saved_km, 2),
        "distance_savings_percentage": round(dist_savings_pct, 1),
        "time_savings_percentage":   round(time_savings_pct, 1),
        "original_co2_kg":           round(orig_co2_kg, 2),
        "optimized_co2_kg":          round(opt_co2_kg, 2),
        "co2_saved_kg":              round(co2_saved_kg, 2),
        "num_stops":                 num_stops,
        # Expose params used so frontend can show them
        "average_speed_kmh":         speed_kmh,
        "stop_time_minutes":         stop_time_min,
        "traffic_factor":            traffic_factor,
        "co2_per_km":                co2_per_km,
        "vehicle_type":              vehicle_type,
    }


# ── Fuel cost metrics ─────────────────────────────────────────────────────────

def calculate_fuel_cost_metrics(
    original_distance_km,
    optimized_distance_km,
    vehicle_type,
):
    """
    Calculate fuel cost metrics using vehicle-specific efficiency
    and live Malaysian fuel prices from data.gov.my.
    """
    from app.services.fuel_service import get_latest_fuel_prices

    params     = _get_vehicle_params(vehicle_type)
    efficiency = params["efficiency_l_per_100km"]
    fuel_type  = params["fuel_type"]

    live_prices = get_latest_fuel_prices()
    price_per_l = live_prices.get(fuel_type, live_prices.get("ron95", 2.05))

    print(
        f"   🛢️  Fuel calc: {vehicle_type} → "
        f"{efficiency}L/100km @ RM{price_per_l}/L "
        f"({fuel_type.upper()}, live price)"
    )

    orig_liters = (original_distance_km  / 100) * efficiency
    opt_liters  = (optimized_distance_km / 100) * efficiency

    orig_cost_rm  = round(orig_liters * price_per_l, 2)
    opt_cost_rm   = round(opt_liters  * price_per_l, 2)
    saved_rm      = round(orig_cost_rm - opt_cost_rm, 2)
    savings_pct   = (
        round((saved_rm / orig_cost_rm) * 100, 1)
        if orig_cost_rm > 0 else 0
    )

    return {
        "original_fuel_cost_rm":        orig_cost_rm,
        "optimized_fuel_cost_rm":       opt_cost_rm,
        "fuel_cost_saved_rm":           saved_rm,
        "fuel_cost_savings_percentage": savings_pct,
        "fuel_efficiency_l_per_100km":  efficiency,
        "fuel_price_rm_per_l":          price_per_l,
        "fuel_type":                    fuel_type.upper(),
    }