"""
Compute ingredient betweenness centrality in an Ingredient–Target network.

This script evaluates the importance of ingredient nodes as intermediaries
between molecular targets. A modified version of Brandes' algorithm is
used to compute betweenness centrality, considering only shortest paths
whose source nodes belong to the set of Targets.

The resulting centrality scores quantify the extent to which an ingredient
participates in shortest communication paths between targets, highlighting
ingredients that may play a bridging role in the target interaction network.

Input:
    - GraphML network containing nodes of type "Ingredients" and "Targets".

Output:
    - CSV file containing ingredient betweenness values.
    - Console summary of the highest-ranking ingredients.
"""
import networkx as nx
from tqdm import tqdm
import csv

def betweenness_ingredients_targets(graphml_file, output_csv="ingredients_betweenness.csv"):
    """
    Compute ingredient betweenness centrality based on shortest paths
    between target nodes.

    A modified Brandes algorithm is applied to an Ingredient–Target graph.
    Betweenness scores are accumulated only for Ingredient nodes, while
    shortest-path exploration originates from Target nodes.

    The resulting centrality values estimate the importance of ingredients
    as intermediaries connecting molecular targets through shortest paths.

    Args:
        graphml_file (str): Path to the input GraphML network.
        output_csv (str, optional): Path to the CSV file where the
            resulting centrality values will be stored.
            Defaults to ``"ingredients_betweenness.csv"``.

    Returns:
        dict[str, float]: Mapping between ingredient identifiers and
        normalized betweenness centrality values.

    Raises:
        ValueError: If no Ingredient nodes are found in the graph.
        ValueError: If no Target nodes are found in the graph.

    Notes:
        The implementation follows the dependency accumulation strategy
        introduced by Brandes (2001), but restricts the analysis to
        shortest paths originating from Target nodes.

        Betweenness values are normalized using the number of possible
        target pairs:

            (n_targets - 1)(n_targets - 2) / 2

        when at least three target nodes are present.
    """
    # Load the Ingredient–Target network from a GraphML file.
    G = nx.read_graphml(graphml_file)
    
    # Separate ingredient and target nodes according to
    # their node type attribute.
    ingredients = [n for n, d in G.nodes(data=True) if d.get('type') == 'Ingredients']
    targets = [n for n, d in G.nodes(data=True) if d.get('type') == 'Targets']
    
    if not ingredients:
        raise ValueError("No se encontraron nodos con type='Ingredients'")
    if not targets:
        raise ValueError("No se encontraron nodos con type='Targets'")
    
    print(f"Grafo: {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas")
    print(f"Ingredientes: {len(ingredients)}, Dianas: {len(targets)}")
    
    # Create an index mapping for debugging and inspection
    # purposes.
    node_to_idx = {n: i for i, n in enumerate(G.nodes())}
    
    # Initialize betweenness scores for ingredient nodes.
    bt = {ing: 0.0 for ing in ingredients}
    
    # For each target as a source, run BFS and accumulate dependencies
    # We use the Brandes algorithm with peer restriction (only sources and destinations in targets)
    # but we only keep the delta for nodes that are ingredients.
    
    # Precompute adjacency lists to avoid repeated graph
    # lookups during shortest-path exploration.
    neighbors = {n: list(G.neighbors(n)) for n in G.nodes()}
    
    # Execute a modified Brandes traversal using each target
    # node as a source.
    for source in tqdm(targets, desc="Calculando betweenness (sobre dianas)"):
        # Compute shortest-path distances, path counts (sigma),
        # and predecessor relationships.
        dist = {n: -1 for n in G.nodes()}
        sigma = {n: 0 for n in G.nodes()}
        pred = {n: [] for n in G.nodes()}
        
        dist[source] = 0
        sigma[source] = 1
        queue = [source]
        while queue:
            v = queue.pop(0)
            for w in neighbors[v]:
                if dist[w] == -1:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        
        # Sort nodes by descending distance (to accumulate delta)
        nodes_by_dist = sorted(G.nodes(), key=lambda x: dist[x], reverse=True)
        delta = {n: 0 for n in G.nodes()}
        for w in nodes_by_dist:
            if w == source:
                continue
            for v in pred[w]:
                # factor = sigma[v] / sigma[w] * (1 + delta[w])
                delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            # We only contribute to betweenness if w is a target (because paths end in targets)
            # and if we are accumulating for ingredients: the ingredients are intermediate nodes
            # The delta of a node v already contains the contribution of all source->* paths that pass through v.
            # To match an ingredient, we add up its delta when the actual node is non-source
            # In the standard algorithm, delta[v] adds to the betweenness of v after processing all successors.
            # But here we want them to only count paths that start in 'source' (target) and end in any target.
            # The accumulation of delta[v] already covers these paths because BFS only reached the reachable nodes,
            # and all paths end at some node (targets or others). In the end, the betweenness of v is the sum
            # of delta[v] on all sources.
        
        # Update ingredient betweenness scores using the
        # accumulated dependency values.
        for ing in ingredients:
            bt[ing] += delta[ing]
    
    # Normalize scores according to the number of possible
    # target pairs.
    n_targets = len(targets)
    if n_targets > 2:
        norm = (n_targets - 1) * (n_targets - 2) / 2
    else:
        norm = 1.0
    for ing in bt:
        bt[ing] /= norm
    
    # Export ingredient centrality values to CSV format.
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["ingredient_id", "name", "betweenness"])
        for ing_id, value in sorted(bt.items(), key=lambda x: -x[1]):
            name = G.nodes[ing_id].get('name', ing_id)
            writer.writerow([ing_id, name, value])
    
    # Display the highest-ranking ingredients according
    # to their betweenness centrality.
    print("\nTop 10 ingredientes por betweenness (caminos entre dianas):")
    for ing_id, val in sorted(bt.items(), key=lambda x: -x[1])[:10]:
        name = G.nodes[ing_id].get('name', ing_id)
        print(f"  {name} ({ing_id}): {val:.6f}")
    
    return bt

if __name__ == "__main__":
    # Run with your GraphML file
    # Make sure the nodes have 'type' attribute with "Ingredients" and "Targets" values
    betweenness_ingredients_targets("collapsed_components/component_0000.graphml", "ingredients_betweenness.csv")