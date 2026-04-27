"""Original route distance calculation logic."""


def calculate_original_route_distance(address_order, coordinates, distance_matrix):
    """
    Calculate the ACTUAL distance for the user's original address order.
    This answers the lecturer's question: "How do you know the original route?"

    Parameters:
        address_order: List of addresses in the order user entered them.
        coordinates: List of corresponding coordinates.
        distance_matrix: The full NxN distance matrix from OSRM.

    Returns:
        Total distance in meters for the original route.
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
            print(
                f"     ⚠️ Segment {i+1}: {address_order[i]} → "
                f"{address_order[(i+1) % len(address_order)]} is unreachable"
            )
        else:
            print(
                f"     Segment {i+1}: {address_order[i]} → "
                f"{address_order[(i+1) % len(address_order)]}: {segment_dist/1000:.2f} km"
            )

        total_distance += segment_dist

    return total_distance

