"""
Analyze the relationship between ingredient-derived centrality and
network centrality in a projected Herb–Disease graph.

This script computes multiple centrality measures for herb nodes in a
Herb–Disease projection and compares them against ingredient-based
betweenness scores that have previously been propagated to herbs.

The analysis includes:

1. Degree centrality.
2. Closeness centrality.
3. Betweenness centrality.
4. Group comparison using the Mann–Whitney U test.
5. Correlation analysis using Spearman's rank correlation.
6. Visualization through boxplots and scatter plots.

For weighted graphs, edge weights are interpreted as connection
strengths and converted into distances using:

    distance = 1 / weight

so that stronger biological relationships correspond to shorter paths
during shortest-path-based centrality calculations.

Input:
    - A projected Herb–Disease GraphML network.
    - A CSV file containing ingredient-derived betweenness scores
      associated with herb nodes.

Output:
    - A CSV file containing all computed centrality measures.
    - Boxplot visualizations comparing high- and low-centrality groups.
    - Scatter plots showing the relationship between ingredient-derived
      and network-derived centrality metrics.

The goal is to evaluate whether herbs associated with highly central
ingredients also occupy structurally important positions in the
projected Herb–Disease network.
"""
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import mannwhitneyu, spearmanr
from tqdm import tqdm
import numpy as np


HERB_DISEASE_GRAPHML = "tcm_herb_disease_paths_collapsed.graphml"
HERB_BT_CSV = "herbs_propagated_betweenness.csv"
OUTPUT_CSV = "herb_centrality_analysis.csv"
OUTPUT_PLOT = "herb_centrality_comparison.png"
TOP_PERCENTILE = 90   # Percentile to define "high among ingredients"


# Load the projected Herb–Disease network.
print("1. Cargando grafo colapsado hierba-enfermedad...")
H = nx.read_graphml(HERB_DISEASE_GRAPHML)
print(f"   Nodos: {H.number_of_nodes()}, Aristas: {H.number_of_edges()}")

# If edge weights are available, convert them into distances
# so that shortest-path-based centralities can be computed.
#
# Stronger connections (higher weights) correspond to shorter
# effective distances.
has_weights = all('weight' in data for _, _, data in H.edges(data=True))
if has_weights:
    print("   El grafo contiene pesos. Se convertirán a distancias (1/weight).")
    # Create a new graph with the attribute 'distance' = 1/weight
    H_dist = nx.Graph()
    # Add nodes with their original attributes
    for node, attrs in tqdm(H.nodes(data=True), desc="   Copiando nodos"):
        H_dist.add_node(node, **attrs)
    # Add edges with distance = 1/weight (avoiding division by zero)
    for u, v, attrs in tqdm(H.edges(data=True), desc="   Convirtiendo aristas a distancia"):
        w = attrs.get('weight', 1)
        if w == 0:
            dist = float('inf')  # If weight 0, infinite distance (practically not connected)
        else:
            dist = 1.0 / w
        H_dist.add_edge(u, v, distance=dist, weight=w)  # We keep the original weight just in case
    H = H_dist
    weight_param = 'distance'
    print("   Listo. Se usará el atributo 'distance' para closeness y betweenness.")
else:
    print("   El grafo no tiene pesos. Se calcularán centralidades sin ponderar.")
    weight_param = None

# Restrict the analysis to nodes representing herbs.
herbs = [n for n, d in H.nodes(data=True) if d.get('type') == 'Herbs']
print(f"2. Hierbas en el grafo colapsado: {len(herbs)}")

# Compute node degree for each herb.
#
# Since only herb nodes are analyzed, the degree corresponds
# to the number of diseases connected to each herb in the
# projected network.
print("3. Calculando degree centrality...")
degree = dict(H.degree(herbs))
print("   Degree centrality completada.")

# Compute closeness centrality using weighted shortest paths
# when distance information is available.
print("4. Calculando closeness centrality (ponderada por distancia si existe)...")
if weight_param is not None:
    closeness = nx.closeness_centrality(H, distance=weight_param)
else:
    closeness = nx.closeness_centrality(H)
print("   Closeness centrality completada.")

# Compute betweenness centrality.
#
# Exact computation is used for smaller graphs, while
# approximation via node sampling is used for larger networks
# to reduce computational cost.
print("5. Calculando betweenness centrality...")
if H.number_of_nodes() < 5000:
    print("   Grafo pequeño (<5000 nodos), se usará cálculo exacto.")
    betweenness = nx.betweenness_centrality(H, weight=weight_param, normalized=True)
else:
    k_sample = 1000
    print(f"   Grafo grande, se usará muestreo con k={k_sample} nodos fuente.")
    betweenness = nx.betweenness_centrality(H, k=k_sample, weight=weight_param, normalized=True)
print("   Betweenness centrality completada.")

# Load ingredient-derived betweenness values previously
# propagated to herb nodes.
print("6. Cargando CSV con betweenness de ingredientes...")
df_bt = pd.read_csv(HERB_BT_CSV)
print(f"   Registros cargados: {len(df_bt)}")

# Create DataFrame with results
df = pd.DataFrame()
df['herb_id'] = herbs
df['degree'] = [degree.get(h, 0) for h in herbs]
df['closeness'] = [closeness.get(h, 0) for h in herbs]
df['betweenness'] = [betweenness.get(h, 0) for h in herbs]

# Unite with the betweenness of ingredients
df = df.merge(df_bt, left_on='herb_id', right_on='herb_id', how='left')
df.fillna({'max_ingredient_betweenness': 0, 'sum_ingredient_betweenness': 0}, inplace=True)

# Define upper group between the two (90th percentile)
threshold = df['max_ingredient_betweenness'].quantile(TOP_PERCENTILE/100)
df['high_bt'] = df['max_ingredient_betweenness'] >= threshold

print(f"\n7. Umbral para alto betweenness (percentil {TOP_PERCENTILE}): {threshold:.6f}")
print(f"   Hierbas con alto betweenness: {df['high_bt'].sum()} de {len(df)}")

# Compare network centrality distributions between herbs
# with high and low ingredient-derived betweenness.
#
# The Mann–Whitney U test is used because centrality
# distributions are typically non-normal.
metrics = ['degree', 'closeness', 'betweenness']
print("\n8. Prueba U de Mann-Whitney (comparación entre grupos alto/bajo):")
for m in metrics:
    high = df[df['high_bt']][m]
    low = df[~df['high_bt']][m]
    stat, p = mannwhitneyu(high, low, alternative='two-sided')
    print(f"   {m}: p={p:.4e}, mediana high={high.median():.6f}, low={low.median():.6f}")

# Evaluate monotonic associations between ingredient-derived
# betweenness and network centrality measures.
#
# Spearman's rank correlation is preferred because centrality
# values are often skewed and non-linear.
print("\n9. Correlación de Spearman (max_ingredient_bt vs métrica):")
for m in metrics:
    corr, p = spearmanr(df['max_ingredient_betweenness'], df[m])
    print(f"   {m}: rho={corr:.4f}, p={p:.4e}")

# Save the complete analysis table for downstream processing.
df.to_csv(OUTPUT_CSV, index=False)
print(f"\n10. Datos completos guardados en {OUTPUT_CSV}")

# Visualize centrality distributions for herbs with high
# versus low ingredient-derived betweenness.
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for i, m in enumerate(metrics):
    sns.boxplot(data=df, x='high_bt', y=m, ax=axes[i], palette='Set2')
    axes[i].set_title(f'{m.capitalize()} por grupo')
    axes[i].set_xlabel('Alto betweenness de ingredientes')
    axes[i].set_ylabel(m.capitalize())
plt.tight_layout()
plt.savefig(OUTPUT_PLOT, dpi=150)
print(f"11. Gráfico guardado en {OUTPUT_PLOT}")
plt.show()

# Visualize the relationship between propagated ingredient
# betweenness and betweenness centrality in the projected
# Herb–Disease network.
plt.figure(figsize=(6,6))
sns.scatterplot(data=df, x='max_ingredient_betweenness', y='betweenness', hue='high_bt', alpha=0.6)
plt.xscale('log')
plt.yscale('log')
plt.xlabel('Max ingredient betweenness (propagado)')
plt.ylabel('Betweenness en red hierba-enfermedad')
plt.title('Relación entre ambas medidas de centralidad')
plt.savefig('scatter_bt_comparison.png', dpi=150)
plt.show()
print("12. Análisis completado.")