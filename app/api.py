"""API blueprint: route optimization endpoint."""

from flask import Blueprint, jsonify, request, session

from app.auth import login_required
from app.core.metrics import calculate_time_metrics, calculate_fuel_cost_metrics
from app.core.routing import calculate_original_route_distance
from app.core.time_windows import validate_time_windows, check_route_feasibility
from app.graph.road_graph import build_delivery_graph, get_graph_stats, render_graph_base64
from app.services.geo_service import get_coordinates, get_distance_matrix, get_route_shape
from app.services.history_service import save_route, get_user_routes, get_cumulative_stats
from app.solver.genetic import GeneticOptimizer
from config import GA_DEFAULTS
from app.services.fuel_service import get_latest_fuel_prices

api_bp = Blueprint("api", __name__)


# ── Fuel prices ───────────────────────────────────────────────────────────────

@api_bp.route("/api/fuel-prices", methods=["GET"])
def fuel_prices():
    data = get_latest_fuel_prices()
    return jsonify(data)


# ── Route history ─────────────────────────────────────────────────────────────

@api_bp.route("/api/route-history", methods=["GET"])
@login_required
def route_history():
    phone = session.get("user", {}).get("phone", "")
    if not phone:
        return jsonify({"error": "User session missing phone"}), 400
    routes = get_user_routes(phone)
    stats  = get_cumulative_stats(phone)
    return jsonify({"routes": routes, "cumulative_stats": stats})


@api_bp.route("/api/route-history/<route_id>", methods=["DELETE"])
@login_required
def delete_route_record(route_id):
    from app.services.history_service import delete_route
    phone = session.get("user", {}).get("phone", "")
    delete_route(phone, route_id)
    return jsonify({"status": "deleted"})


# ── Main optimisation endpoint ────────────────────────────────────────────────

@api_bp.route("/api/process-route", methods=["POST"])
@login_required
def process_route():
    data = request.json
    if not data or "addresses" not in data:
        return jsonify({"error": "No addresses provided"}), 400

    raw_addresses = data["addresses"]
    time_windows  = data.get("time_windows", [])    # FYP2: optional per-stop windows
    departure_time = data.get("departure_time", "08:00")

    print(f"\n{'='*60}")
    print("🚀 STARTING ROUTE OPTIMIZATION")
    print(f"{'='*60}")

    # ── Validate time windows before anything else ────────────────
    if time_windows:
        valid, err = validate_time_windows(time_windows)
        if not valid:
            return jsonify({"error": f"Invalid time windows: {err}"}), 400
        print(f"✅ {len(time_windows)} time window(s) validated")

    # 1. GEOCODING
    print(f"\n📍 GEOCODING ADDRESSES")
    valid_coords    = []
    found_addresses = []
    for addr in raw_addresses:
        coord = get_coordinates(addr)
        if coord:
            valid_coords.append(list(coord))
            found_addresses.append(addr)
            print(f"   ✓ {addr}")
        else:
            print(f"   ✗ Failed: {addr}")

    if len(valid_coords) < 2:
        return jsonify({"error": "Need at least 2 valid addresses"}), 400

    # 2. DISTANCE MATRIX
    print(f"\n🧮 GENERATING DISTANCE MATRIX")
    matrix = get_distance_matrix(valid_coords)
    if not matrix:
        return jsonify({"error": "Failed to generate distance matrix"}), 500

    # 3. ORIGINAL ROUTE
    print(f"\n📏 CALCULATING ORIGINAL ROUTE")
    original_distance_meters = calculate_original_route_distance(
        found_addresses, valid_coords, matrix
    )
    original_distance_km = original_distance_meters / 1000.0

    # 4. GENETIC ALGORITHM
    print(f"\n🧬 RUNNING GENETIC ALGORITHM")
    optimizer = GeneticOptimizer(
        distance_matrix=matrix,
        pop_size=GA_DEFAULTS["pop_size"],
        generations=GA_DEFAULTS["generations"],
    )
    best_route_indices, optimized_distance_meters = optimizer.solve()
    optimized_distance_km = optimized_distance_meters / 1000.0

    # Rotate to start at depot (index 0)
    if 0 in best_route_indices:
        z = best_route_indices.index(0)
        best_route_indices = best_route_indices[z:] + best_route_indices[:z]

    optimized_addresses    = [found_addresses[i] for i in best_route_indices]
    optimized_stops_coords = [list(valid_coords[i]) for i in best_route_indices]
    optimized_addresses.append(optimized_addresses[0])
    optimized_stops_coords.append(list(optimized_stops_coords[0]))

    # 5. ROUTE SHAPES
    print(f"\n🗺️ GETTING ROUTE GEOMETRIES")
    orig_coords_ordered = [list(valid_coords[i]) for i in range(len(found_addresses))]
    orig_coords_ordered.append(list(orig_coords_ordered[0]))
    original_route_shape  = get_route_shape(orig_coords_ordered)
    optimized_route_shape = get_route_shape(optimized_stops_coords)
    original_route_shape  = [list(p) for p in original_route_shape]  if original_route_shape  else orig_coords_ordered
    optimized_route_shape = [list(p) for p in optimized_route_shape] if optimized_route_shape else optimized_stops_coords

    # 6. VEHICLE-AWARE METRICS
    print(f"\n📊 CALCULATING METRICS")
    vehicle   = session.get("user", {}).get("vehicle", "car")
    num_stops = len(optimized_addresses) - 1

    metrics      = calculate_time_metrics(
        original_distance_km, optimized_distance_km, num_stops, vehicle
    )
    fuel_metrics = calculate_fuel_cost_metrics(
        original_distance_km, optimized_distance_km, vehicle
    )

    # Attach distances for history saving
    metrics["original_distance_km"]  = round(original_distance_km, 2)
    metrics["optimized_distance_km"] = round(optimized_distance_km, 2)
    fuel_metrics["fuel_cost_saved_rm"] = fuel_metrics.get("fuel_cost_saved_rm", 0)

    # 7. GRAPH CONSTRUCTION (FYP2 — GNN layer)
    print(f"\n🕸️ BUILDING DELIVERY GRAPH")
    G, node_labels = build_delivery_graph(matrix, found_addresses, best_route_indices)
    graph_stats    = get_graph_stats(G)
    graph_image_b64 = render_graph_base64(
        G, node_labels,
        coordinates=[list(c) for c in valid_coords],
        optimized_route=best_route_indices,
        title="GreenPath Delivery Network Graph",
    )
    print(f"   ✓ Graph: {graph_stats['nodes']} nodes, {graph_stats['edges']} edges")

    # 8. TIME WINDOW FEASIBILITY CHECK
    tw_result = check_route_feasibility(
        optimized_addresses, metrics, time_windows, departure_time
    )
    if time_windows:
        if tw_result["feasible"]:
            print(f"   ✅ All time windows satisfied")
        else:
            print(f"   ⚠️ {len(tw_result['violations'])} time window violation(s)")

    # 9. SAVE TO HISTORY
    phone = session.get("user", {}).get("phone", "")
    if phone:
        combined_metrics = {**metrics, **fuel_metrics}
        route_id = save_route(
            phone          = phone,
            addresses      = found_addresses,
            optimized_route= optimized_addresses[:-1],   # exclude repeated depot
            vehicle_type   = vehicle,
            metrics        = combined_metrics,
            time_windows   = time_windows or None,
        )
        print(f"   ✓ Route saved to history (id={route_id})")

    print(f"\n✅ OPTIMIZATION COMPLETE!")
    print(f"{'='*60}\n")

    return jsonify({
        "status": "success",
        "optimization_metadata": {
            "algorithm":      "Genetic Algorithm (TSP Solver)",
            "generations":    GA_DEFAULTS["generations"],
            "population_size":GA_DEFAULTS["pop_size"],
        },
        "route_comparison": {
            "original_distance_km":        round(original_distance_km, 2),
            "optimized_distance_km":       round(optimized_distance_km, 2),
            "distance_saved_km":           metrics["distance_savings_km"],
            "distance_savings_percentage": metrics["distance_savings_percentage"],
            "original_co2_kg":             metrics["original_co2_kg"],
            "optimized_co2_kg":            metrics["optimized_co2_kg"],
            "co2_saved_kg":                metrics["co2_saved_kg"],
            "original_travel_minutes":     metrics["original_travel_minutes"],
            "optimized_travel_minutes":    metrics["optimized_travel_minutes"],
            "time_saved_minutes":          metrics["time_saved_minutes"],
            "time_savings_percentage":     metrics["time_savings_percentage"],
            "original_fuel_cost_rm":       fuel_metrics["original_fuel_cost_rm"],
            "optimized_fuel_cost_rm":      fuel_metrics["optimized_fuel_cost_rm"],
            "fuel_cost_saved_rm":          fuel_metrics["fuel_cost_saved_rm"],
            "fuel_cost_savings_percentage":fuel_metrics["fuel_cost_savings_percentage"],
            "fuel_type":                   fuel_metrics.get("fuel_type", "RON95"),
            # Vehicle context
            "vehicle_type":                vehicle,
            "average_speed_kmh":           metrics["average_speed_kmh"],
            "stop_time_minutes":           metrics["stop_time_minutes"],
            "traffic_factor":              metrics["traffic_factor"],
            "co2_per_km":                  metrics["co2_per_km"],
            "num_stops":                   num_stops,
        },
        "routes": {
            "original_route":       found_addresses + [found_addresses[0]],
            "optimized_route":      optimized_addresses,
            "original_route_shape": original_route_shape,
            "optimized_route_shape":optimized_route_shape,
            "stops_coordinates":    optimized_stops_coords[:-1],
        },
        # FYP2 additions
        "graph": {
            "stats":       graph_stats,
            "image_b64":   graph_image_b64,   # embed as <img src="data:image/png;base64,...">
        },
        "time_windows": {
            "feasible":      tw_result["feasible"],
            "violations":    tw_result["violations"],
            "stop_schedule": tw_result["stop_schedule"],
        },
        "debug_info": {
            "total_addresses_submitted": len(raw_addresses),
            "successfully_geocoded":     len(found_addresses),
        },
    })