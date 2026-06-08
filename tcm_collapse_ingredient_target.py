"""
Collapse intermediary node types and extract connected components.

This script loads a GraphML graph and removes selected node types by
replacing paths that traverse those nodes with direct connections between
relevant nodes. The resulting collapsed graph preserves connectivity while
reducing graph complexity.

After collapsing, the graph is decomposed into connected components. Each
component is exported as an independent GraphML file, and a metadata CSV
file is generated containing basic statistics for every component.

Typical use case:

    Ingredients -- Herbs -- Diseases -- Targets

becomes:

    Ingredients -- Targets

when ``Herbs`` and ``Diseases`` are specified as removable node types.

Input:
    - GraphML network containing node type information.

Output:
    - Collapsed graph.
    - Individual GraphML files for each connected component.
    - Metadata CSV summarizing all exported components.
"""
import networkx as nx
from tqdm import tqdm
from collections import deque, defaultdict
import csv
import os

def collapse_irrelevant_nodes(
    input_graphml: str,
    output_dir: str, # Directory where to store the components
    types_to_remove: list = ["Herbs", "Diseases"],
    keep_types: list = ["Targets", "Ingredients"],
    verbose: bool = True
):
    """
    Collapse selected node types while preserving connectivity.

    Nodes whose type belongs to ``types_to_remove`` are treated as
    intermediary nodes and removed from the final graph. Two relevant
    nodes become connected in the collapsed graph if a path exists
    between them through only removable nodes.

    The resulting graph contains all nodes whose type belongs to
    ``keep_types`` as well as any node whose type is not explicitly
    listed in ``types_to_remove``.

    After graph construction, the collapsed graph is partitioned into
    connected components. Each component is exported as an individual
    GraphML file and summarized in a metadata CSV file.

    Args:
        input_graphml (str): Path to the input GraphML file.
        output_dir (str): Directory where component files and metadata
            will be written.
        types_to_remove (list[str], optional): Node types that should
            be collapsed and removed from the final graph.
            Defaults to ``["Herbs", "Diseases"]``.
        keep_types (list[str], optional): Node types explicitly
            preserved in the collapsed graph.
            Defaults to ``["Targets", "Ingredients"]``.
        verbose (bool, optional): Whether to print progress and graph
            statistics. Defaults to ``True``.

    Returns:
        tuple[networkx.Graph, list[set]]:
            A tuple containing:

            - The collapsed graph.
            - A list of connected components, where each component is
              represented as a set of node identifiers.

    Side Effects:
        - Creates the output directory if it does not exist.
        - Exports one GraphML file per connected component.
        - Generates a CSV file containing component metadata.
        - Prints progress information and graph statistics.

    Notes:
        Connectivity is preserved using breadth-first search (BFS)
        traversals through removable nodes. If multiple paths connect
        the same pair of relevant nodes, only a single edge is added
        to the collapsed graph.
    """
    print(f"Cargando grafo desde {input_graphml}...")
    G = nx.read_graphml(input_graphml)
    if verbose:
        print(f"Grafo original: {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas")
    
    # Identify nodes that will remain in the final graph and nodes
    # that will be treated as intermediary connectors.
    nodes_to_keep = set()
    nodes_to_remove = set()
    for node, attrs in G.nodes(data=True):
        node_type = attrs.get('type', 'Unknown')
        if node_type in keep_types:
            nodes_to_keep.add(node)
        elif node_type in types_to_remove:
            nodes_to_remove.add(node)
        else:
            nodes_to_keep.add(node)   # Other types are maintained
    
    if verbose:
        print(f"Nodos a mantener: {len(nodes_to_keep)}")
        print(f"Nodos a eliminar/colapsar: {len(nodes_to_remove)}")
    
    # Initialize the collapsed graph using only relevant nodes.
    H = nx.Graph()
    for node in nodes_to_keep:
        H.add_node(node, **G.nodes[node])
    
    # Discover indirect connections between relevant nodes by
    # traversing removable nodes using BFS.
    print("Buscando caminos entre nodos relevantes...")
    edges_to_add = set()
    
    for source in tqdm(nodes_to_keep, desc="Procesando nodos relevantes"):
        visited = {source}
        queue = deque([(source, source)])
        while queue:
            current, origin = queue.popleft()
            for neighbor in G.neighbors(current):
                if neighbor in visited:
                    continue
                if neighbor in nodes_to_keep:
                    if neighbor != origin:
                        edge = tuple(sorted([origin, neighbor]))
                        edges_to_add.add(edge)
                elif neighbor in nodes_to_remove:
                    visited.add(neighbor)
                    queue.append((neighbor, origin))
    
    # Add collapsed edges discovered during the traversal phase.
    print(f"Añadiendo {len(edges_to_add)} aristas colapsadas...")
    for u, v in edges_to_add:
        H.add_edge(u, v)
    
    # Preserve any direct edges that already existed between
    # relevant nodes in the original graph.
    direct_edges = 0
    for u, v in G.edges():
        if u in nodes_to_keep and v in nodes_to_keep:
            if not H.has_edge(u, v):
                H.add_edge(u, v)
                direct_edges += 1
    
    if verbose:
        print(f"Aristas directas preexistentes: {direct_edges}")
        print(f"Grafo colapsado: {H.number_of_nodes()} nodos, {H.number_of_edges()} aristas")
    
    # Create output directory if it doesn’t exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get connected components
    components = list(nx.connected_components(H))
    num_comp = len(components)
    print(f"El grafo colapsado tiene {num_comp} componentes conexas.")
    
    # Save each component in a file and generate metadata
    metadata = []
    for idx, comp_nodes in enumerate(components):
        subH = H.subgraph(comp_nodes).copy()
        comp_size = subH.number_of_nodes()
        comp_edges = subH.number_of_edges()
        out_file = os.path.join(output_dir, f"component_{idx:04d}.graphml")
        nx.write_graphml(subH, out_file)
        metadata.append({
            "component_id": idx,
            "nodes": comp_size,
            "edges": comp_edges,
            "file": out_file
        })
        print(f"Componente {idx}: {comp_size} nodos, {comp_edges} aristas -> guardada en {out_file}")
    
    # Save metadata to CSV for reference
    meta_file = os.path.join(output_dir, "components_metadata_ingredient_target.csv")
    with open(meta_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["component_id", "nodes", "edges", "file"])
        writer.writeheader()
        writer.writerows(metadata)
    print(f"Metadatos guardados en {meta_file}")
    
    return H, components

# Example of use
if __name__ == "__main__":
    H, components = collapse_irrelevant_nodes(
        input_graphml="tcm_subgraph_clean.graphml",
        output_dir="collapsed_components",
        types_to_remove=["Herbs", "Diseases"],
        keep_types=["Targets", "Ingredients"]
    )