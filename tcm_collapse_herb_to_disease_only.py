"""
Project a heterogeneous biomedical graph into a Herb–Disease network.

This script constructs a projected graph containing only herb and disease
nodes. An edge is created between a herb and a disease whenever a path
exists between them in the original graph whose length falls within a
specified range.

Intermediate nodes (e.g., Ingredients and Targets) are used only to
discover connectivity and are not included in the final graph.

Optionally, edges can be weighted according to the number of distinct
paths found between each herb–disease pair.

Input:
    - GraphML network containing at least Herb and Disease nodes,
      potentially connected through intermediary node types.

Output:
    - A projected Herb–Disease GraphML network.
"""
import networkx as nx
from tqdm import tqdm
from collections import defaultdict, deque

def collapse_herb_disease(
    input_graphml: str,
    output_graphml: str,
    min_length: int = 2,
    max_length: int = 3,
    weighted: bool = False
):
    """
    Project a heterogeneous graph into a Herb–Disease network.

    A herb and a disease are connected in the projected graph if at least
    one path exists between them in the original graph whose length is
    between ``min_length`` and ``max_length`` edges. Intermediate nodes
    are used only during path discovery and are excluded from the final
    graph.

    The projection can optionally assign edge weights corresponding to
    the number of valid paths discovered between each herb–disease pair.

    Args:
        input_graphml (str): Path to the input GraphML file.
        output_graphml (str): Path where the projected graph will be
            saved.
        min_length (int, optional): Minimum path length (number of edges)
            required to create a Herb–Disease connection. Defaults to 2.
        max_length (int, optional): Maximum path length explored during
            path discovery. Defaults to 3.
        weighted (bool, optional): If True, edge weights represent the
            number of valid paths found between each herb–disease pair.
            If False, a single unweighted edge is created. Defaults to
            False.

    Returns:
        None

    Side Effects:
        - Loads a GraphML file from disk.
        - Writes a projected GraphML file.
        - Prints graph statistics and progress information.

    Notes:
        The search procedure uses breadth-first search (BFS) starting
        from each herb node and explores only intermediary nodes.
        Additional herb nodes encountered during traversal are ignored
        because they are not considered valid intermediate nodes.

    Examples:
        With ``min_length=2`` and ``max_length=3``, the following
        paths generate Herb–Disease edges:

            Herb → Ingredient → Disease
            Herb → Target → Disease
            Herb → Ingredient → Target → Disease
    """
    print(f"Cargando grafo desde {input_graphml}...")
    G = nx.read_graphml(input_graphml)
    print(f"Grafo original: {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas")
    
    # Identify herb and disease nodes that will compose the
    # projected network.
    herbs = [n for n, d in G.nodes(data=True) if d.get('type') == 'Herbs']
    diseases = [n for n, d in G.nodes(data=True) if d.get('type') == 'Diseases']
    print(f"Hierbas: {len(herbs)}")
    print(f"Enfermedades: {len(diseases)}")
    
    # Node types that cannot appear as intermediate vertices
    # during path exploration.
    forbidden_types = {'Herbs', 'Diseases'}
    
    # Store the number of valid paths discovered between
    # each Herb–Disease pair.
    edge_counter = defaultdict(int)
    
    # Perform a bounded BFS from every herb node to identify
    # diseases reachable through intermediary nodes.
    print("Buscando caminos entre hierbas y enfermedades...")
    for src in tqdm(herbs, desc="Procesando hierbas"):
        queue = deque([(src, 0)])
        visited = {src: 0}
        while queue:
            current, depth = queue.popleft()
            if depth >= max_length:
                continue
            for neighbor in G.neighbors(current):
                new_depth = depth + 1
                # If it’s a disease and the depth is within range
                if neighbor in diseases and min_length <= new_depth <= max_length:
                    edge_counter[(src, neighbor)] += 1
                # If it’s not disease and it’s not weed (it’s intermediate allowed), we keep exploring
                elif neighbor not in herbs and new_depth < max_length:
                    if neighbor not in visited or visited[neighbor] > new_depth:
                        visited[neighbor] = new_depth
                        queue.append((neighbor, new_depth))
                # Note: if we find an intermediate grass (it should not happen) we ignore it because it is not an intermediate allowed
                # If we find a disease but at less depth, we already record it; deeper it doesn’t matter.
    
    print(f"Se encontraron {len(edge_counter)} pares (hierba, enfermedad) con caminos.")
    
    # Create the projected Herb–Disease graph and preserve
    # original node attributes.
    H = nx.Graph()
    for node in herbs + diseases:
        H.add_node(node, **G.nodes[node])
    
    # Add either weighted or unweighted edges depending on
    # the selected projection mode.
    if weighted:
        for (h, d), weight in edge_counter.items():
            H.add_edge(h, d, weight=weight)
    else:
        for (h, d) in edge_counter.keys():
            H.add_edge(h, d)
    
    print(f"Grafo colapsado: {H.number_of_nodes()} nodos, {H.number_of_edges()} aristas")
    if weighted:
        weights = [data['weight'] for _, _, data in H.edges(data=True)]
        print(f"Peso medio: {sum(weights)/len(weights):.2f}, máximo: {max(weights)}")
    
    nx.write_graphml(H, output_graphml)
    print(f"Guardado en {output_graphml}")

if __name__ == "__main__":
    collapse_herb_disease(
        input_graphml="tcm_subgraph_clean.graphml",
        output_graphml="tcm_herb_disease_paths_collapsed.graphml",
        min_length=2,      # Includes H-I-D or H-T-D roads (distance 2)
        max_length=3,      # Includes H-I-T-D (distance 3)
        weighted=False
    )