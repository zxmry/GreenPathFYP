"""
Road Network Graph Construction for GreenPath.

This module models delivery stops and road segments as a weighted
directed graph using NetworkX.  It serves two purposes:

1. Academic / FYP2 contribution — demonstrates the graph representation
   layer that would feed into a Graph Neural Network (GNN) encoder in a
   future phase of the project.

2. Practical visualisation — renders the delivery network as an image
   that can be embedded in the dashboard or saved for reports.

Graph structure
---------------
- Nodes  : each delivery stop (depot + delivery addresses)
- Edges  : every ordered pair (i→j) with weight = OSRM road distance (km)

The adjacency matrix produced here is identical to the OSRM distance
matrix already used by the Genetic Algorithm, so no additional API
calls are required.
"""

import base64
import io
import math

import matplotlib
matplotlib.use("Agg")          # headless — no display needed on server
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx


# ── Graph construction ────────────────────────────────────────────────────────

def build_delivery_graph(distance_matrix, addresses, optimized_route=None):
    """
    Build a weighted directed graph from an OSRM distance matrix.

    Parameters
    ----------
    distance_matrix : list[list[float | None]]
        NxN matrix of road distances in metres.
    addresses : list[str]
        Human-readable label for each node (same order as matrix rows).
    optimized_route : list[int] | None
        Optional list of node indices representing the optimised route.
        When provided, those edges are highlighted in the visualisation.

    Returns
    -------
    G : nx.DiGraph
        Directed weighted graph.
    node_labels : dict
        Mapping of node index → short label for display.
    """
    G = nx.DiGraph()
    n = len(addresses)

    # Add nodes with metadata
    for i, addr in enumerate(addresses):
        short = _short_label(addr, i)
        G.add_node(i, label=short, full_address=addr, is_depot=(i == 0))

    # Add edges (only where OSRM returned a valid distance)
    for i in range(n):
        for j in range(n):
            if i != j:
                dist = distance_matrix[i][j]
                if dist is not None:
                    G.add_edge(i, j, weight=round(dist / 1000, 2))   # km

    node_labels = {i: G.nodes[i]["label"] for i in G.nodes}
    return G, node_labels


def get_graph_stats(G):
    """
    Return a summary of graph properties useful for the FYP report.

    Returns
    -------
    dict with keys: nodes, edges, density, avg_weight_km,
                    is_strongly_connected, diameter_km
    """
    weights = [d["weight"] for _, _, d in G.edges(data=True)]
    try:
        diameter = nx.diameter(G.to_undirected())
    except Exception:
        diameter = None

    return {
        "nodes":                  G.number_of_nodes(),
        "edges":                  G.number_of_edges(),
        "density":                round(nx.density(G), 4),
        "avg_weight_km":          round(sum(weights) / len(weights), 2) if weights else 0,
        "max_weight_km":          round(max(weights), 2) if weights else 0,
        "min_weight_km":          round(min(weights), 2) if weights else 0,
        "is_strongly_connected":  nx.is_strongly_connected(G),
        "diameter_hops":          diameter,
    }


# ── Visualisation ─────────────────────────────────────────────────────────────

def render_graph_base64(
    G,
    node_labels,
    coordinates=None,
    optimized_route=None,
    title="GreenPath Delivery Network Graph",
):
    """
    Render the graph to a PNG image and return it as a base64 string
    so it can be embedded directly in an HTML <img> src attribute.

    Parameters
    ----------
    G : nx.DiGraph
    node_labels : dict
    coordinates : list[tuple[float, float]] | None
        If provided, uses real (lon, lat) positions for layout.
        Otherwise uses spring layout.
    optimized_route : list[int] | None
        Sequence of node indices for the optimised route (highlighted).
    title : str

    Returns
    -------
    str  — base64-encoded PNG (no "data:image/png;base64," prefix)
    """
    fig, ax = plt.subplots(figsize=(10, 7))
    fig.patch.set_facecolor("#F8FAF9")
    ax.set_facecolor("#F8FAF9")

    # ── Node positions ────────────────────────────────────────────
    if coordinates and len(coordinates) == G.number_of_nodes():
        # Use geographic coordinates: x=longitude, y=latitude
        pos = {i: (coordinates[i][1], coordinates[i][0]) for i in G.nodes}
    else:
        pos = nx.spring_layout(G, seed=42, k=2.5)

    # ── Identify optimised route edges ────────────────────────────
    opt_edges = set()
    if optimized_route and len(optimized_route) > 1:
        route = list(optimized_route) + [optimized_route[0]]   # close loop
        for a, b in zip(route, route[1:]):
            opt_edges.add((a, b))

    regular_edges = [(u, v) for u, v in G.edges() if (u, v) not in opt_edges]

    # ── Draw background edges ─────────────────────────────────────
    nx.draw_networkx_edges(
        G, pos, edgelist=regular_edges, ax=ax,
        edge_color="#CCDDCC", arrows=True,
        arrowstyle="-|>", arrowsize=12,
        width=0.8, alpha=0.5,
        connectionstyle="arc3,rad=0.08",
    )

    # ── Draw optimised route edges ────────────────────────────────
    if opt_edges:
        nx.draw_networkx_edges(
            G, pos, edgelist=list(opt_edges), ax=ax,
            edge_color="#2E7D32", arrows=True,
            arrowstyle="-|>", arrowsize=18,
            width=2.8, alpha=0.95,
            connectionstyle="arc3,rad=0.08",
        )

    # ── Node colours (depot = gold, stops = teal) ─────────────────
    node_colors = ["#F9A825" if G.nodes[n]["is_depot"] else "#1B5E20"
                   for n in G.nodes]
    node_sizes  = [900 if G.nodes[n]["is_depot"] else 600 for n in G.nodes]

    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color=node_colors, node_size=node_sizes,
        edgecolors="white", linewidths=1.5,
    )

    # ── Labels ────────────────────────────────────────────────────
    nx.draw_networkx_labels(
        G, pos, labels=node_labels, ax=ax,
        font_size=8, font_color="white", font_weight="bold",
    )

    # ── Edge weight labels (only on optimised route) ──────────────
    if opt_edges:
        opt_weights = {
            (u, v): f"{d['weight']} km"
            for u, v, d in G.edges(data=True)
            if (u, v) in opt_edges
        }
        nx.draw_networkx_edge_labels(
            G, pos, edge_labels=opt_weights, ax=ax,
            font_size=7, font_color="#1B5E20",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7),
            label_pos=0.35,
        )

    # ── Legend ────────────────────────────────────────────────────
    legend_handles = [
        mpatches.Patch(color="#F9A825", label="Depot (start/end)"),
        mpatches.Patch(color="#1B5E20", label="Delivery stop"),
    ]
    if opt_edges:
        legend_handles.append(
            mpatches.Patch(color="#2E7D32", label="Optimised route")
        )
    legend_handles.append(
        mpatches.Patch(color="#CCDDCC", label="Other road connections")
    )
    ax.legend(handles=legend_handles, loc="upper left", fontsize=8,
              framealpha=0.9, facecolor="white")

    ax.set_title(title, fontsize=12, fontweight="bold", color="#1B5E20", pad=12)
    ax.axis("off")
    plt.tight_layout()

    # ── Encode to base64 ──────────────────────────────────────────
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ── Internal helpers ──────────────────────────────────────────────────────────

def _short_label(address, index):
    """
    Produce a short 2–3 character label for graph display.
    Index 0 is always 'D' (depot).
    """
    if index == 0:
        return "D"
    # Use first letter of first meaningful word
    parts = [p for p in address.replace(",", " ").split()
             if len(p) > 2 and p.lower() not in
             ("jalan", "the", "and", "kuala", "lumpur", "selangor", "malaysia")]
    if parts:
        return parts[0][:3].upper()
    return f"S{index}"