from flask import Flask, jsonify, request, render_template, send_from_directory, session, redirect, url_for, flash
from services import get_coordinates, get_distance_matrix, get_route_shape
from solver import GeneticOptimizer
import os
import json

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.secret_key = 'greenpath-secret-key-change-in-production-2024'

# Ensure static folder exists
if not os.path.exists('static'):
    os.makedirs('static')

@app.route('/')
def home():
    session.clear()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        
        if action == 'signup':
            name = request.form.get('name', '').strip()
            vehicle = request.form.get('vehicle', '')
            if len(name) < 2 or not vehicle or len(password) < 8:
                flash('Please fill all fields correctly. Password min 8 chars.', 'error')
                return render_template('login.html')
            # Persistent signup
            USERS[phone] = {'name': name, 'password': password, 'vehicle': vehicle}
            save_users(USERS)
            session['user'] = USERS[phone]
            flash(f'Welcome {name}! Account created.', 'success')
            return redirect(url_for('dashboard'))
        
        elif action == 'login':
            user = USERS.get(phone)
            if user and user['password'] == password:
                session['user'] = {'name': user['name'], 'phone': phone, 'vehicle': user['vehicle']}
                flash(f'Welcome back, {user["name"]}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid phone or password.', 'error')
        
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please log in to access dashboard.', 'warning')
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

USERS_FILE = 'users.json'

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

USERS = load_users()

def login_required(f):
    def wrap(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

def calculate_original_route_distance(address_order, coordinates, distance_matrix):
    """
    Calculate the ACTUAL distance for the user's original address order.
    This answers the lecturer's question: "How do you know the original route?"
    
    Parameters:
    - address_order: List of addresses in the order user entered them
    - coordinates: List of corresponding coordinates
    - distance_matrix: The full NxN distance matrix from OSRM
    
    Returns:
    - Total distance in meters for the original route
    """
    total_distance = 0
    
    print(f"   Calculating original route for {len(address_order)} addresses...")
    
    # Create mapping from address to its index in the matrix
    address_to_index = {addr: i for i, addr in enumerate(address_order)}
    
    # Calculate distance following the user's EXACT input order
    for i in range(len(address_order)):
        current_idx = address_to_index[address_order[i]]
        
        # Next address (wrap around to start for last address)
        if i + 1 < len(address_order):
            next_idx = address_to_index[address_order[i + 1]]
        else:
            next_idx = address_to_index[address_order[0]]  # Return to start
            
        # Get distance from the pre-calculated matrix
        segment_dist = distance_matrix[current_idx][next_idx]
        
        # Handle None/unreachable values (same as solver.py)
        if segment_dist is None:
            segment_dist = 1000000000  # Very large number as penalty
            print(f"     ⚠️ Segment {i+1}: {address_order[i]} → {address_order[(i+1) % len(address_order)]} is unreachable")
        else:
            print(f"     Segment {i+1}: {address_order[i]} → {address_order[(i+1) % len(address_order)]}: {segment_dist/1000:.2f} km")
            
        total_distance += segment_dist
    
    return total_distance

def calculate_time_metrics(original_distance_km, optimized_distance_km, num_stops):
    """
    Calculate realistic time metrics for delivery routes.
    
    Parameters:
    - original_distance_km: Original route distance in kilometers
    - optimized_distance_km: Optimized route distance in kilometers  
    - num_stops: Number of delivery stops (excluding return to start)
    
    Returns:
    - Dictionary with all time metrics
    """
    # Realistic parameters for urban delivery in Kuala Lumpur
    params = {
        'average_speed_kmh': 35,      # Realistic urban delivery speed
        'stop_time_minutes': 5,        # Average time per delivery stop
        'traffic_factor': 1.2,         # 20% time penalty for KL traffic
        'co2_per_km': 0.120            # kg CO₂ per km (diesel delivery van)
    }
    
    # Calculate travel time (excluding stops)
    original_travel_hours = original_distance_km / params['average_speed_kmh']
    optimized_travel_hours = optimized_distance_km / params['average_speed_kmh']
    
    # Apply traffic factor
    original_travel_hours *= params['traffic_factor']
    optimized_travel_hours *= params['traffic_factor']
    
    # Add stop time
    total_stop_time_hours = (num_stops * params['stop_time_minutes']) / 60
    
    # Total time including stops
    original_total_hours = original_travel_hours + total_stop_time_hours
    optimized_total_hours = optimized_travel_hours + total_stop_time_hours
    
    # Convert to minutes for display
    original_total_minutes = original_total_hours * 60
    optimized_total_minutes = optimized_total_hours * 60
    
    # Calculate savings
    time_saved_minutes = original_total_minutes - optimized_total_minutes
    
    # Calculate percentages
    distance_savings_km = original_distance_km - optimized_distance_km
    distance_savings_percentage = (distance_savings_km / original_distance_km) * 100 if original_distance_km > 0 else 0
    time_savings_percentage = (time_saved_minutes / original_total_minutes) * 100 if original_total_minutes > 0 else 0
    
    # CO₂ calculations
    original_co2_kg = original_distance_km * params['co2_per_km']
    optimized_co2_kg = optimized_distance_km * params['co2_per_km']
    co2_saved_kg = original_co2_kg - optimized_co2_kg
    
    return {
        'original_travel_minutes': round(original_total_minutes, 1),
        'optimized_travel_minutes': round(optimized_total_minutes, 1),
        'time_saved_minutes': round(time_saved_minutes, 1),
        'distance_savings_km': round(distance_savings_km, 2),
        'distance_savings_percentage': round(distance_savings_percentage, 1),
        'time_savings_percentage': round(time_savings_percentage, 1),
        'original_co2_kg': round(original_co2_kg, 2),
        'optimized_co2_kg': round(optimized_co2_kg, 2),
        'co2_saved_kg': round(co2_saved_kg, 2),
        'num_stops': num_stops,
        'average_speed_kmh': params['average_speed_kmh'],
        'stop_time_minutes': params['stop_time_minutes']
    }

def calculate_fuel_cost_metrics(original_distance_km, optimized_distance_km, vehicle_type):
    """
    Calculate fuel cost metrics based on distance, vehicle type, fuel efficiency, and Malaysian fuel prices.
    
    Fuel efficiency (L/100km): motorcycle=4.0, car=8.0, van/truck/lorry=12.0
    Fuel prices (RM/L): motorcycle/car=1.99, van/truck/lorry=5.1
    
    Parameters:
    - original_distance_km, optimized_distance_km: Route distances in km
    - vehicle_type: String from user session (e.g., "GreenPath Car")
    
    Returns:
    - Dictionary with fuel costs in RM and savings
    """
    # Map vehicle type to fuel category and efficiency
    vehicle_lower = vehicle_type.lower()
    if any(word in vehicle_lower for word in ['motorcycle', 'moto', 'bike']):
        fuel_efficiency_l_per_100km = 4.0
        fuel_price_rm_per_l = 1.99
    elif any(word in vehicle_lower for word in ['car', 'sedan']):
        fuel_efficiency_l_per_100km = 8.0
        fuel_price_rm_per_l = 1.99
    else:  # van, truck, lorry, default
        fuel_efficiency_l_per_100km = 12.0
        fuel_price_rm_per_l = 5.1
    
    print(f"   🛢️  Fuel calc: {vehicle_type} → {fuel_efficiency_l_per_100km}L/100km @ RM{fuel_price_rm_per_l}/L")
    
    # Fuel used = (distance_km / 100) * efficiency
    original_fuel_liters = (original_distance_km / 100) * fuel_efficiency_l_per_100km
    optimized_fuel_liters = (optimized_distance_km / 100) * fuel_efficiency_l_per_100km
    
    # Fuel cost = fuel_liters * price_per_liter
    original_fuel_cost_rm = round(original_fuel_liters * fuel_price_rm_per_l, 2)
    optimized_fuel_cost_rm = round(optimized_fuel_liters * fuel_price_rm_per_l, 2)
    
    fuel_cost_saved_rm = round(original_fuel_cost_rm - optimized_fuel_cost_rm, 2)
    fuel_cost_savings_percentage = round((fuel_cost_saved_rm / original_fuel_cost_rm) * 100, 1) if original_fuel_cost_rm > 0 else 0
    
    return {
        'original_fuel_cost_rm': original_fuel_cost_rm,
        'optimized_fuel_cost_rm': optimized_fuel_cost_rm,
        'fuel_cost_saved_rm': fuel_cost_saved_rm,
        'fuel_cost_savings_percentage': fuel_cost_savings_percentage,
        'fuel_efficiency_l_per_100km': fuel_efficiency_l_per_100km,
        'fuel_price_rm_per_l': fuel_price_rm_per_l
    }

@app.route('/api/process-route', methods=['POST'])
@login_required
def process_route():
    data = request.json
    if not data or 'addresses' not in data:
        return jsonify({"error": "No addresses provided"}), 400

    
    raw_addresses = data['addresses']
    
    print(f"\n" + "="*60)
    print("🚀 STARTING ROUTE OPTIMIZATION")
    print("="*60)
    print(f"📝 User entered {len(raw_addresses)} addresses:")
    for i, addr in enumerate(raw_addresses):
        print(f"   {i+1}. {addr}")
    
    # 1. GEOCODING: Convert addresses to coordinates
    print(f"\n📍 GEOCODING ADDRESSES")
    print("-"*40)
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
        return jsonify({
            "error": "Need at least 2 valid addresses",
            "details": {
                "total_addresses": len(raw_addresses),
                "valid_addresses": len(valid_coords),
                "successful_addresses": found_addresses
            }
        }), 400

    # 2. DISTANCE MATRIX: Get all pairwise distances
    print(f"\n🧮 GENERATING DISTANCE MATRIX")
    print("-"*40)
    matrix = get_distance_matrix(valid_coords)
    if not matrix:
        return jsonify({"error": "Failed to generate distance matrix"}), 500
    print(f"   ✓ Matrix generated: {len(matrix)}x{len(matrix[0])}")

    # 3. CALCULATE ORIGINAL ROUTE (USER'S INPUT ORDER)
    print(f"\n📏 CALCULATING ORIGINAL ROUTE")
    print("-"*40)
    print("   Following user's exact input order:")
    original_distance_meters = calculate_original_route_distance(found_addresses, valid_coords, matrix)
    original_distance_km = original_distance_meters / 1000.0
    print(f"   ✓ Original route distance: {original_distance_km:.2f} km")

    # 4. GENETIC ALGORITHM OPTIMIZATION
    print(f"\n🧬 RUNNING GENETIC ALGORITHM")
    print("-"*40)
    optimizer = GeneticOptimizer(distance_matrix=matrix, pop_size=100, generations=50)
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
        best_route_indices = best_route_indices[zero_pos:] + best_route_indices[:zero_pos]

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
    print("-"*40)
    
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
    print("-"*40)
    num_stops = len(optimized_addresses) - 1  # Excluding duplicate start
    
    metrics = calculate_time_metrics(
        original_distance_km, 
        optimized_distance_km, 
        num_stops
    )
    
    # Get user vehicle for fuel calculations
    vehicle = session.get('user', {}).get('vehicle', 'GreenPath Car')
    
    # Calculate fuel metrics
    fuel_metrics = calculate_fuel_cost_metrics(
        original_distance_km, 
        optimized_distance_km, 
        vehicle
    )
    print(f"   • Original: {metrics['original_travel_minutes']:.0f} min, {metrics['original_co2_kg']:.1f} kg CO₂")
    print(f"   • Optimized: {metrics['optimized_travel_minutes']:.0f} min, {metrics['optimized_co2_kg']:.1f} kg CO₂")
    print(f"   • Time saved: {metrics['time_saved_minutes']:.0f} min ({metrics['time_savings_percentage']:.1f}%)")
    print(f"   • CO₂ saved: {metrics['co2_saved_kg']:.1f} kg")
    print(f"   • Fuel cost saved: RM{fuel_metrics['fuel_cost_saved_rm']:.2f} ({fuel_metrics['fuel_cost_savings_percentage']:.1f}%)")

    # 8. PREPARE FINAL RESULTS
    print(f"\n✅ OPTIMIZATION COMPLETE!")
    print("="*60)
    print(f"   Original Route: {original_distance_km:.2f} km")
    print(f"   Optimized Route: {optimized_distance_km:.2f} km")
    print(f"   Distance Saved: {metrics['distance_savings_km']:.2f} km ({metrics['distance_savings_percentage']:.1f}%)")
    print(f"   CO₂ Saved: {metrics['co2_saved_kg']:.2f} kg")
    print(f"   Time Saved: {metrics['time_saved_minutes']:.0f} minutes")
    print("="*60 + "\n")

    return jsonify({
        "status": "success",
        "optimization_metadata": {
            "algorithm": "Genetic Algorithm (TSP Solver)",
            "generations": 50,
            "population_size": 100,
            "calculation_method": "Real comparison between user's input order vs optimized sequence"
        },
        "route_comparison": {
            # Distances
            "original_distance_km": round(original_distance_km, 2),
            "optimized_distance_km": round(optimized_distance_km, 2),
            "distance_saved_km": metrics['distance_savings_km'],
            "distance_savings_percentage": metrics['distance_savings_percentage'],
            
            # CO₂ Emissions
            "original_co2_kg": metrics['original_co2_kg'],
            "optimized_co2_kg": metrics['optimized_co2_kg'],
            "co2_saved_kg": metrics['co2_saved_kg'],
            
            # Time Metrics
            "original_travel_minutes": metrics['original_travel_minutes'],
            "optimized_travel_minutes": metrics['optimized_travel_minutes'],
            "time_saved_minutes": metrics['time_saved_minutes'],
            "time_savings_percentage": metrics['time_savings_percentage'],
            
            # Fuel Cost Metrics (NEW)
            "original_fuel_cost_rm": fuel_metrics['original_fuel_cost_rm'],
            "optimized_fuel_cost_rm": fuel_metrics['optimized_fuel_cost_rm'],
            "fuel_cost_saved_rm": fuel_metrics['fuel_cost_saved_rm'],
            "fuel_cost_savings_percentage": fuel_metrics['fuel_cost_savings_percentage'],
            
            # Parameters used
            "average_speed_kmh": metrics['average_speed_kmh'],
            "stop_time_minutes": metrics['stop_time_minutes'],
            "num_stops": metrics['num_stops'],
            "vehicle_type": vehicle
        },
        "routes": {
            "original_route": found_addresses + [found_addresses[0]],  # With return to start
            "optimized_route": optimized_addresses,
            "original_route_shape": original_route_shape,
            "optimized_route_shape": optimized_route_shape,
            "stops_coordinates": optimized_stops_coords[:-1]  # Exclude duplicate start
        },
        "debug_info": {
            "total_addresses_submitted": len(raw_addresses),
            "successfully_geocoded": len(found_addresses),
            "message": "Original route calculated based on user's exact input order"
        }
    })

if __name__ == '__main__':
    # Create necessary folders
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    print("="*60)
    print("🚀 GREENPATH DELIVERY OPTIMIZER")
    print("="*60)
    print("📁 System Check:")
    print(f"   • Working directory: {os.getcwd()}")
    print(f"   • app.py: {'✅ Found' if os.path.exists('app.py') else '❌ Missing'}")
    print(f"   • templates/index.html: {'✅ Found' if os.path.exists('templates/index.html') else '❌ Missing'}")
    print(f"   • static/ folder: {'✅ Found' if os.path.exists('static') else '❌ Missing'}")
    print(f"   • services.py: {'✅ Found' if os.path.exists('services.py') else '❌ Missing'}")
    print(f"   • solver.py: {'✅ Found' if os.path.exists('solver.py') else '❌ Missing'}")
    print("="*60)
    print("💡 Algorithm Features:")
    print("   • Real original route calculation (user's input order)")
    print("   • Genetic Algorithm optimization")
    print("   • CO₂ and time savings based on actual distances")
    print("   • Detailed route visualization data")
    print("="*60)
    
    app.run(debug=True, port=5000)