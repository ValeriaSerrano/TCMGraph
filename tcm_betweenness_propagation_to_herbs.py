"""
Compute ingredient betweenness centrality and propagate it to herbs.

This script analyzes a heterogeneous TCMBank network containing Herbs,
Ingredients, Targets, and Diseases. The workflow consists of two stages:

1. Ingredient centrality computation:
   A bipartite Ingredient–Target subgraph is extracted and the
   betweenness centrality of ingredient nodes is computed considering
   only shortest paths whose source and target nodes are Targets.

2. Herb centrality propagation:
   Ingredient betweenness values are propagated to herb nodes through
   direct Herb–Ingredient relationships. For each herb, two summary
   statistics are computed:

       - Maximum ingredient betweenness.
       - Sum of ingredient betweenness values.

The resulting metrics provide an estimate of how strongly a herb is
associated with ingredients that play an important intermediary role
between molecular targets.

Input:
    - Complete TCMBank GraphML network.

Output:
    - CSV file containing ingredient betweenness values.
    - CSV file containing propagated herb-level metrics.
    - Ranking of herbs according to propagated ingredient betweenness.
"""
import networkx as nx
import csv


GRAPHML_FILE = "tcm_subgraph_clean.graphml" # Full graph (with all types)
OUTPUT_ING_BT_CSV = "ingredients_betweenness.csv" # Ingredient Betweenness
OUTPUT_HERB_BT_CSV = "herbs_propagated_betweenness.csv" # Herbs with max/sum


print("Cargando grafo completo...")
G_full = nx.read_graphml(GRAPHML_FILE)

# Construct the Ingredient–Target bipartite subgraph.
#
# Only Ingredients and Targets are retained because the
# betweenness analysis focuses on ingredient-mediated
# connectivity between molecular targets.
print("Extrayendo subgrafo ingrediente-diana...")
nodes_keep = [n for n, d in G_full.nodes(data=True) if d.get('type') in ['Ingredients', 'Targets']]
G_bi = G_full.subgraph(nodes_keep).copy()
print(f"Subgrafo bipartito: {G_bi.number_of_nodes()} nodos, {G_bi.number_of_edges()} aristas")

# Separate Target and Ingredient nodes for subset
# betweenness computation.
targets = [n for n, d in G_bi.nodes(data=True) if d.get('type') == 'Targets']
ingredients = [n for n, d in G_bi.nodes(data=True) if d.get('type') == 'Ingredients']

# Compute subset betweenness centrality.
#
# Only shortest paths whose source and destination nodes
# are Targets contribute to the centrality score.
#
# Ingredients with high scores act as important bridges
# between molecular targets.
if len(targets) < 2:
    raise ValueError("Se necesitan al menos dos dianas para calcular betweenness.")

print(f"Calculando betweenness subset (fuentes y destinos = dianas)...")
bt_subset = nx.betweenness_centrality_subset(
    G_bi, sources=targets, targets=targets, normalized=True
)

# Retain centrality values only for Ingredient nodes.
ing_betweenness = {node: bt_subset[node] for node in ingredients}

# Save ingredient betweenness scores for downstream analysis.
with open(OUTPUT_ING_BT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["ingredient_id", "name", "betweenness"])
    for ing_id, val in sorted(ing_betweenness.items(), key=lambda x: -x[1]):
        name = G_bi.nodes[ing_id].get('name', ing_id)
        writer.writerow([ing_id, name, val])

print(f"Betweenness de ingredientes guardado en {OUTPUT_ING_BT_CSV}")

# Propagate ingredient centrality to herbs through direct
# Herb–Ingredient relationships.
herb_max = {}
herb_sum = {}

for node, attrs in G_full.nodes(data=True):
    if attrs.get('type') == 'Herbs':
        # Identify ingredients directly associated with the current herb.
        neigh = list(G_full.neighbors(node))
        ing_neigh = [n for n in neigh if G_full.nodes[n].get('type') == 'Ingredients']
        if not ing_neigh:
            herb_max[node] = 0.0
            herb_sum[node] = 0.0
        else:
            values = [ing_betweenness.get(ing, 0.0) for ing in ing_neigh]
            herb_max[node] = max(values)
            herb_sum[node] = sum(values)

# Compute herb-level summaries:
#
# - Maximum ingredient betweenness.
# - Sum of ingredient betweenness values.
#
# These metrics capture both the strongest individual
# ingredient contribution and the cumulative contribution
# of all associated ingredients.
with open(OUTPUT_HERB_BT_CSV, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["herb_id", "name", "max_ingredient_betweenness", "sum_ingredient_betweenness"])
    for herb_id in herb_max:
        name = G_full.nodes[herb_id].get('name', herb_id)
        writer.writerow([herb_id, name, herb_max[herb_id], herb_sum[herb_id]])

# Save propagated ingredient centrality measures at the herb level.
print(f"Propagación a hierbas guardada en {OUTPUT_HERB_BT_CSV}")

# Display the herbs associated with the highest ingredient
# betweenness values.
sorted_herbs = sorted(herb_max.items(), key=lambda x: x[1], reverse=True)
print("\nTop 10 hierbas por máximo betweenness de ingredientes:")
for herb_id, val in sorted_herbs[:10]:
    name = G_full.nodes[herb_id].get('name', herb_id)
    print(f"  {name} ({herb_id}): {val:.6f}")