"""API blueprint: route optimization endpoint."""

from flask import Blueprint, jsonify, request, session

from app.auth import login_required
from app.core.metrics import calculate_time_metrics, calculate_fuel_cost_metrics
from app.core.routing import calculate_original_route_distance
from app.services.geo_service import get_coordinates, get_distance_matrix, get_route_shape
from app.solver.genetic import GeneticOptimizer
from config import GA_DEFAULTS

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/process-route", methods=["POST"])
@login_required
def process_route():
    data = request.json
    if not data or "addresses" not in data:
        return jsonify({"error": "No addresses provided"}), 400

    raw_addresses = data["addresses"]

    print(f"\n" + "=" * 60)
    print("🚀 STARTING ROUTE OPTIMIZATION")
    print("=" * 60)
    print(f"📝 User entered {len(raw_addresses)} addresses:")
    for i, addr in enumerate(raw_addresses):
        print(f"   {i + 1}. {addr}")

    # 1. GEOCODING: Convert addresses to coordinates
    print(f"\n📍 GEOCODING ADDRESSES")
    print("-" * 40)
    valid_coords = []
    found_addresses = []

    for i, addr in enumerate(raw_addresses):
        print(f"   Processing: '{addr}'")
        coord = get_coordinates(addr)
        if coord:
            valid_coords.append(list(coord))
            found_addresses.append(addr)
            print(f"   ✓ Success → ({coord[0]:.4f}, {coord[1]:.4f})")
        else:
            print(f"   ✗ Failed to geocode")

    print(f"\n📊 GEOCODING RESULTS:")
    print(f"   • Submitted: {len(raw_addresses)} addresses")
    print(f"   • Successfully geocoded: {len(valid_coords)} addresses")

    if len(valid_coords) < 2:
        return jsonify(
            {
                "error": "Need at least 2 valid addresses",
                "details": {
                    "total_addresses": len(raw_addresses),
                    "valid_addresses": len(valid_coords),
                    "successful_addresses": found_addresses,
                },
            }
        ), 400

    # 2. DISTANCE MATRIX: Get all pairwise distances
    print(f"\n🧮 GENERATING DISTANCE MATRIX")
    print("-" * 40)
    matrix = get_distance_matrix(valid_coords)
    if not matrix:
        return jsonify({"error": "Failed to generate distance matrix"}), 500
    print(f"   ✓ Matrix generated: {len(matrix)}x{len(matrix[0])}")

    # 3. CALCULATE ORIGINAL ROUTE (USER'S INPUT ORDER)
    print(f"\n📏 CALCULATING ORIGINAL ROUTE")
    print("-" * 40)
    print("   Following user's exact input order:")
    original_distance_meters = calculate_original_route_distance(
        found_addresses, valid_coords, matrix
    )
    original_distance_km = original_distance_meters / 1000.0
    print(f"   ✓ Original route distance: {original_distance_km:.2f} km")

    # 4. GENETIC ALGORITHM OPTIMIZATION
    print(f"\n🧬 RUNNING GENETIC ALGORITHM")
    print("-" * 40)
    optimizer = GeneticOptimizer(
        distance_matrix=matrix,
        pop_size=GA_DEFAULTS["pop_size"],
        generations=GA_DEFAULTS["generations"],
    )
    best_route_indices, optimized_distance_meters = optimizer.solve()
    optimized_distance_km = optimized_distance_meters / 1000.0
    print(f"   ✓ Optimized route distance: {optimized_distance_km:.2f} km")

    # Show optimization results
    distance_saved_km = original_distance_km - optimized_distance_km
    distance_savings_percentage = (distance_saved_km / original_distance_km) * 100
    print(f"   💰 Savings: {distance_saved_km:.2f} km ({distance_savings_percentage:.1f}%)")

    # 5. RECONSTRUCT OPTIMIZED ROUTE
    # Rotate to start at index 0 for better presentation
    if 0 in best_route_indices:
        zero_pos = best_route_indices.index(0)
        best_route_indices = (
            best_route_indices[zero_pos:] + best_route_indices[:zero_pos]
        )

    optimized_addresses = []
    optimized_stops_coords = []

    for idx in best_route_indices:
        optimized_addresses.append(found_addresses[idx])
        optimized_stops_coords.append(list(valid_coords[idx]))

    # Add return to start to complete the loop
    optimized_addresses.append(optimized_addresses[0])
    optimized_stops_coords.append(list(optimized_stops_coords[0]))

    # 6. GET DETAILED ROAD SHAPES FOR VISUALIZATION
    print(f"\n🗺️ GETTING ROUTE GEOMETRIES")
    print("-" * 40)

    # Get shape for ORIGINAL route
    print("   Getting original route shape...")
    original_route_coords = []
    for addr in found_addresses:
        idx = found_addresses.index(addr)
        original_route_coords.append(list(valid_coords[idx]))
    original_route_coords.append(list(original_route_coords[0]))  # Return to start

    original_route_shape = get_route_shape(original_route_coords)
    if not original_route_shape:
        print("   ⚠️ Using straight-line fallback for original route")
        original_route_shape = original_route_coords
    else:
        original_route_shape = [list(point) for point in original_route_shape]

    # Get shape for OPTIMIZED route
    print("   Getting optimized route shape...")
    optimized_route_shape = get_route_shape(optimized_stops_coords)
    if not optimized_route_shape:
        print("   ⚠️ Using straight-line fallback for optimized route")
        optimized_route_shape = optimized_stops_coords
    else:
        optimized_route_shape = [list(point) for point in optimized_route_shape]

    print("   ✓ Both route shapes obtained")

    # 7. CALCULATE COMPREHENSIVE METRICS
    print(f"\n📊 CALCULATING METRICS")
    print("-" * 40)
    num_stops = len(optimized_addresses) - 1  # Excluding duplicate start

    metrics = calculate_time_metrics(
        original_distance_km, optimized_distance_km, num_stops
    )

    # Get user vehicle for fuel calculations
    vehicle = session.get("user", {}).get("vehicle", "GreenPath Car")

    # Calculate fuel metrics
    fuel_metrics = calculate_fuel_cost_metrics(
        original_distance_km, optimized_distance_km, vehicle
    )
    print(
        f"   • Original: {metrics['original_travel_minutes']:.0f} min, "
        f"{metrics['original_co2_kg']:.1f} kg CO₂"
    )
    print(
        f"   • Optimized: {metrics['optimized_travel_minutes']:.0f} min, "
        f"{metrics['optimized_co2_kg']:.1f} kg CO₂"
    )
    print(
        f"   • Time saved: {metrics['time_saved_minutes']:.0f} min "
        f"({metrics['time_savings_percentage']:.1f}%)"
    )
    print(f"   • CO₂ saved: {metrics['co2_saved_kg']:.1f} kg")
    print(
        f"   • Fuel cost saved: RM{fuel_metrics['fuel_cost_saved_rm']:.2f} "
        f"({fuel_metrics['fuel_cost_savings_percentage']:.1f}%)"
    )

    # 8. PREPARE FINAL RESULTS
    print(f"\n✅ OPTIMIZATION COMPLETE!")
    print("=" * 60)
    print(f"   Original Route: {original_distance_km:.2f} km")
    print(f"   Optimized Route: {optimized_distance_km:.2f} km")
    print(
        f"   Distance Saved: {metrics['distance_savings_km']:.2f} km "
        f"({metrics['distance_savings_percentage']:.1f}%)"
    )
    print(f"   CO₂ Saved: {metrics['co2_saved_kg']:.2f} kg")
    print(f"   Time Saved: {metrics['time_saved_minutes']:.0f} minutes")
    print("=" * 60 + "\n")

    return jsonify(
        {
            "status": "success",
            "optimization_metadata": {
                "algorithm": "Genetic Algorithm (TSP Solver)",
                "generations": GA_DEFAULTS["generations"],
                "population_size": GA_DEFAULTS["pop_size"],
                "calculation_method": (
                    "Real comparison between user's input order vs optimized sequence"
                ),
            },
            "route_comparison": {
                # Distances
                "original_distance_km": round(original_distance_km, 2),
                "optimized_distance_km": round(optimized_distance_km, 2),
                "distance_saved_km": metrics["distance_savings_km"],
                "distance_savings_percentage": metrics["distance_savings_percentage"],
                # CO₂ Emissions
                "original_co2_kg": metrics["original_co2_kg"],
                "optimized_co2_kg": metrics["optimized_co2_kg"],
                "co2_saved_kg": metrics["co2_saved_kg"],
                # Time Metrics
                "original_travel_minutes": metrics["original_travel_minutes"],
                "optimized_travel_minutes": metrics["optimized_travel_minutes"],
                "time_saved_minutes": metrics["time_saved_minutes"],
                "time_savings_percentage": metrics["time_savings_percentage"],
                # Fuel Cost Metrics
                "original_fuel_cost_rm": fuel_metrics["original_fuel_cost_rm"],
                "optimized_fuel_cost_rm": fuel_metrics["optimized_fuel_cost_rm"],
                "fuel_cost_saved_rm": fuel_metrics["fuel_cost_saved_rm"],
                "fuel_cost_savings_percentage": fuel_metrics[
                    "fuel_cost_savings_percentage"
                ],
                # Parameters used
                "average_speed_kmh": metrics["average_speed_kmh"],
                "stop_time_minutes": metrics["stop_time_minutes"],
                "num_stops": metrics["num_stops"],
                "vehicle_type": vehicle,
            },
            "routes": {
                "original_route": found_addresses + [found_addresses[0]],
                "optimized_route": optimized_addresses,
                "original_route_shape": original_route_shape,
                "optimized_route_shape": optimized_route_shape,
                "stops_coordinates": optimized_stops_coords[:-1],
            },
            "debug_info": {
                "total_addresses_submitted": len(raw_addresses),
                "successfully_geocoded": len(found_addresses),
                "message": "Original route calculated based on user's exact input order",
            },
        }
    )

