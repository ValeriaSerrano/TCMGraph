import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import csv

NODES_CSV = "graph/nodes.csv"
EDGES_CSV  = "graph/edges.csv"

# Node type color mapping
TYPE_COLORS = {
    "Herbs":       "#2ecc71",  # green
    "Ingredients": "#3498db",  # blue
    "Diseases":    "#e74c3c",  # red
    "Targets":     "#f39c12",  # orange
}

def load_graph():
    """
    Load a graph from CSV files.

    Nodes are loaded from NODES_CSV and edges from EDGES_CSV.
    Each node includes the attributes:
        - name
        - record_type

    Returns:
        networkx.Graph: An undirected graph with nodes and edges loaded.
    """
    G = nx.Graph()

    with open(NODES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            G.add_node(row["id"],
                       name=row["name"],
                       record_type=row["record_type"])

    with open(EDGES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            G.add_edge(row["source"], row["target"])

    return G

def print_stats(G):
    """
    Print basic statistics of the graph.

    Includes:
        - Total number of nodes
        - Total number of edges
        - Node count per type
        - Top 10 nodes by degree (most connected nodes)

    Args:
        G (networkx.Graph): The graph to analyze.
    """
    print(f"Nodes:   {G.number_of_nodes():,}")
    print(f"Edges: {G.number_of_edges():,}")

    type_counts = {}
    for _, data in G.nodes(data=True):
        t = data.get("record_type", "Unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    for t, c in sorted(type_counts.items()):
        print(f"  {t:15} {c:,}")

    # Top 10 most connected nodes
    print("\nTop 10 most connected nodes:")
    top = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:10]

    for nid, deg in top:
        name = G.nodes[nid].get("name", nid)
        rtype = G.nodes[nid].get("record_type", "")
        print(f"  {deg:5} connections — {name} ({rtype})")

def visualize(G, sample_size=2000):
    """
    Visualize a subgraph sampled from the most connected nodes.

    Since the full graph is too large to render efficiently with matplotlib,
    this function selects the top-N nodes by degree and visualizes the
    induced subgraph.

    Args:
        G (networkx.Graph): The full graph.
        sample_size (int, optional): Number of top-degree nodes to include.
                                    Defaults to 2000.

    Output:
        Saves the visualization as an image and displays it.
    """
    print(f"\nVisualizing a sample of the top {sample_size} most connected nodes...")

    # Select top-N nodes by degree
    top_nodes = sorted(G.degree(), key=lambda x: x[1], reverse=True)[:sample_size]
    top_ids   = [n for n, _ in top_nodes]
    subgraph  = G.subgraph(top_ids)

    # Assign colors based on node type
    colors = [
        TYPE_COLORS.get(subgraph.nodes[n].get("record_type", ""), "#95a5a6")
        for n in subgraph.nodes()
    ]

    # Compute layout
    print("Computing layout (this may take a few seconds)...")
    pos = nx.spring_layout(subgraph, seed=42, k=0.3)

    fig, ax = plt.subplots(figsize=(18, 14))
    ax.set_facecolor("#1a1a2e")
    fig.patch.set_facecolor("#1a1a2e")

    nx.draw_networkx_edges(subgraph, pos,
                           alpha=0.08, width=0.4,
                           edge_color="white", ax=ax)

    nx.draw_networkx_nodes(subgraph, pos,
                           node_color=colors,
                           node_size=15,
                           alpha=0.85, ax=ax)

    # Leyend
    legend = [mpatches.Patch(color=c, label=t) for t, c in TYPE_COLORS.items()]
    ax.legend(handles=legend, loc="upper left",
              facecolor="#2c2c54", labelcolor="white", fontsize=11)

    ax.set_title(f"TCMBank Graph — Top {sample_size} most connected nodes (sampled)",
                 color="white", fontsize=14)
    ax.axis("off")

    plt.tight_layout()
    plt.savefig("graph/tcmbank_graph.png", dpi=150, bbox_inches="tight")
    print("Image saved to graph/tcmbank_graph.png")
    plt.show()


if __name__ == "__main__":
    print("Loading graph...")
    G = load_graph()

    print_stats(G)
    visualize(G, sample_size=2000)