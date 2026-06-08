"""
Identify duplicate nodes in a GraphML network based on their name and type.

The script loads a GraphML graph, groups nodes by the combination of their
``name`` and ``type`` attributes, and reports groups containing more than
one node. This is useful for detecting duplicated entities that may have
been assigned different identifiers during graph construction.

Input:
    - A GraphML file containing node attributes ``name`` and ``type``.

Output:
    - The number of duplicated groups found.
    - A list of duplicated groups sorted by descending group size,
      including the entity name, type, node IDs, and duplicate count.
"""
import networkx as nx
from collections import defaultdict

# Path to the GraphML file to analyze
INPUT_FILE = "tcm_subgraph.graphml"

# Load the graph from the GraphML file
G = nx.read_graphml(INPUT_FILE)

# Dictionary mapping (name, type) pairs to the list of node IDs
# sharing those attributes
groups = defaultdict(list)

# Group nodes according to their name and type attributes
for node_id, data in G.nodes(data=True):
    name = str(data.get("name", "")).strip()
    node_type = str(data.get("type", "")).strip()
    groups[(name, node_type)].append(node_id)

# Keep only groups containing more than one node,
# which are considered potential duplicates
duplicates = {
    k: v
    for k, v in groups.items()
    if len(v) > 1
}

print(f"Grupos duplicados encontrados: {len(duplicates)}")

# Display duplicate groups ordered by decreasing number of nodes.
for (name, node_type), ids in sorted(
        duplicates.items(),
        key=lambda x: len(x[1]),
        reverse=True):
    print(
        f"{name} | {node_type} | {ids} -> {len(ids)} nodos"
    )