"""Route metrics calculations: time, CO₂, and fuel cost."""

from config import ROUTE_PARAMS, VEHICLE_FUEL_PARAMS


def calculate_time_metrics(original_distance_km, optimized_distance_km, num_stops):
    """
    Calculate realistic time metrics for delivery routes.

    Parameters:
        original_distance_km: Original route distance in kilometers.
        optimized_distance_km: Optimized route distance in kilometers.
        num_stops: Number of delivery stops (excluding return to start).

    Returns:
        Dictionary with all time metrics.
    """
    params = ROUTE_PARAMS

    # Travel time (excluding stops)
    original_travel_hours = original_distance_km / params["average_speed_kmh"]
    optimized_travel_hours = optimized_distance_km / params["average_speed_kmh"]

    # Apply traffic factor
    original_travel_hours *= params["traffic_factor"]
    optimized_travel_hours *= params["traffic_factor"]

    # Add stop time
    total_stop_time_hours = (num_stops * params["stop_time_minutes"]) / 60

    # Total time including stops
    original_total_hours = original_travel_hours + total_stop_time_hours
    optimized_total_hours = optimized_travel_hours + total_stop_time_hours

    # Convert to minutes for display
    original_total_minutes = original_total_hours * 60
    optimized_total_minutes = optimized_total_hours * 60

    # Calculate savings
    time_saved_minutes = original_total_minutes - optimized_total_minutes

    # Percentages
    distance_savings_km = original_distance_km - optimized_distance_km
    distance_savings_percentage = (
        (distance_savings_km / original_distance_km) * 100
        if original_distance_km > 0 else 0
    )
    time_savings_percentage = (
        (time_saved_minutes / original_total_minutes) * 100
        if original_total_minutes > 0 else 0
    )

    # CO₂ calculations
    original_co2_kg = original_distance_km * params["co2_per_km"]
    optimized_co2_kg = optimized_distance_km * params["co2_per_km"]
    co2_saved_kg = original_co2_kg - optimized_co2_kg

    return {
        "original_travel_minutes": round(original_total_minutes, 1),
        "optimized_travel_minutes": round(optimized_total_minutes, 1),
        "time_saved_minutes": round(time_saved_minutes, 1),
        "distance_savings_km": round(distance_savings_km, 2),
        "distance_savings_percentage": round(distance_savings_percentage, 1),
        "time_savings_percentage": round(time_savings_percentage, 1),
        "original_co2_kg": round(original_co2_kg, 2),
        "optimized_co2_kg": round(optimized_co2_kg, 2),
        "co2_saved_kg": round(co2_saved_kg, 2),
        "num_stops": num_stops,
        "average_speed_kmh": params["average_speed_kmh"],
        "stop_time_minutes": params["stop_time_minutes"],
    }


def calculate_fuel_cost_metrics(original_distance_km, optimized_distance_km, vehicle_type):
    """
    Calculate fuel cost metrics based on distance, vehicle type, fuel efficiency,
    and live Malaysian fuel prices from data.gov.my.
    """
    from app.services.fuel_service import get_latest_fuel_prices  # import here to avoid circular imports

    vehicle_lower = vehicle_type.lower()

    # Get live fuel prices
    live_prices = get_latest_fuel_prices()

    if any(word in vehicle_lower for word in ["motorcycle", "moto", "bike"]):
        fuel_efficiency_l_per_100km = VEHICLE_FUEL_PARAMS["motorcycle"]["efficiency_l_per_100km"]
        fuel_price_rm_per_l = live_prices["ron95"]  # motorcycles use RON95
    elif any(word in vehicle_lower for word in ["car", "sedan"]):
        fuel_efficiency_l_per_100km = VEHICLE_FUEL_PARAMS["car"]["efficiency_l_per_100km"]
        fuel_price_rm_per_l = live_prices["ron95"]  # cars use RON95
    else:  # van, truck, lorry, default
        fuel_efficiency_l_per_100km = VEHICLE_FUEL_PARAMS["van"]["efficiency_l_per_100km"]
        fuel_price_rm_per_l = live_prices["diesel"]  # vans/trucks use diesel

    print(
        f"   🛢️  Fuel calc: {vehicle_type} → "
        f"{fuel_efficiency_l_per_100km}L/100km @ RM{fuel_price_rm_per_l}/L (live price)"
    )

    # Fuel used = (distance_km / 100) * efficiency
    original_fuel_liters = (original_distance_km / 100) * fuel_efficiency_l_per_100km
    optimized_fuel_liters = (optimized_distance_km / 100) * fuel_efficiency_l_per_100km

    # Fuel cost = fuel_liters * price_per_liter
    original_fuel_cost_rm = round(original_fuel_liters * fuel_price_rm_per_l, 2)
    optimized_fuel_cost_rm = round(optimized_fuel_liters * fuel_price_rm_per_l, 2)

    fuel_cost_saved_rm = round(original_fuel_cost_rm - optimized_fuel_cost_rm, 2)
    fuel_cost_savings_percentage = (
        round((fuel_cost_saved_rm / original_fuel_cost_rm) * 100, 1)
        if original_fuel_cost_rm > 0 else 0
    )

    return {
        "original_fuel_cost_rm": original_fuel_cost_rm,
        "optimized_fuel_cost_rm": optimized_fuel_cost_rm,
        "fuel_cost_saved_rm": fuel_cost_saved_rm,
        "fuel_cost_savings_percentage": fuel_cost_savings_percentage,
        "fuel_efficiency_l_per_100km": fuel_efficiency_l_per_100km,
        "fuel_price_rm_per_l": fuel_price_rm_per_l,
    }

