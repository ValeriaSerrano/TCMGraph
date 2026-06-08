# TCMGraph

TCMGraph is a data collection and network analysis pipeline for studying
relationships contained in the TCMBank database.

The project allows users to:

- Crawl entity relationships from the TCMBank API.
- Store and manage raw JSON responses.
- Build heterogeneous biological networks containing:
  - Herbs
  - Ingredients
  - Targets
  - Diseases
- Detect and merge duplicate entities.
- Export graphs in GraphML format.
- Generate projected Herb–Disease networks.
- Compute ingredient and herb centrality measures.
- Analyze the relationship between ingredient importance and herb importance.
- Extract and export connected components for large-scale network analysis.

---

## Requirements

- Python 3.8+

## Dependencies

Install required packages with:

```bash
pip install requests networkx pandas matplotlib seaborn scipy tqdm
```

### Standard Library Modules Used

No installation required:

- json
- os
- csv
- time
- random
- pathlib
- collections
- concurrent.futures
- fcntl (Unix only)

---

## Project Workflow

### 1. Crawl TCMBank data

```bash
python tcm_crawler.py
```

Features:

- Starts from seed nodes.
- Retrieves related entities from the TCMBank API.
- Stores raw JSON responses in the data directory.
- Maintains a visited list to support interrupted executions.
- Can resume previous crawling sessions.

Outputs:

- `data/*.json`
- `visited.json`

---

### 2. Clean the visited list

```bash
python tcm_filter_visited_list.py
```

Removes identifiers that do not correspond to downloaded JSON files and
creates a backup of the original visited list.

Outputs:

- `visited_backup.json`
- Updated `visited.json`

---

### 3. Build a GraphML network

```bash
python tcm_subgraph.py
```

Creates a heterogeneous graph from downloaded TCMBank records.

Node types include:

- Herbs
- Ingredients
- Targets
- Diseases

Outputs:

- `tcm_subgraph.graphml`

---

### 4. Merge duplicate entities

```bash
python tcm_fusion.py
```

Identifies nodes sharing the same name and type and merges them into a
single representative node.

Outputs:

- `tcm_subgraph_clean.graphml`

---

### 5. Detect duplicate entities (optional)

```bash
python tcm_report.py
```

Reports groups of nodes with identical names and types.

Outputs:

- Console report of duplicate groups.

---

### 6. Generate collapsed projections

#### Generic node collapsing

```bash
python tcm_collapse_ingredient_target.py
```

Removes intermediary node types (e.g., Ingredients and Targets) while
preserving connectivity between relevant entities.

Outputs:

- Connected-component GraphML files.
- Component metadata CSV.

#### Herb–Disease projection

```bash
python tcm_collapse_herb_to_disease_only.py
```

Creates a Herb–Disease network by connecting herbs and diseases through
short paths involving intermediary biological entities.

Outputs:

- `tcm_herb_disease_paths_collapsed.graphml`

---

### 7. Compute ingredient betweenness centrality

```bash
python tcm_betweenness_for_ingredients.py
```

Calculates betweenness centrality for Ingredients considering shortest
paths between Targets.

Outputs:

- `ingredients_betweenness.csv`

---

### 8. Propagate ingredient centrality to herbs

```bash
python tcm_betweenness_propagation_to_herbs.py
```

Computes:

- Maximum ingredient betweenness per herb.
- Sum of ingredient betweenness per herb.

Outputs:

- `herbs_propagated_betweenness.csv`

---

### 9. Analyze herb centrality

```bash
python tcm_centralities.py
```

Computes:

- Degree centrality
- Closeness centrality
- Betweenness centrality

and compares them with propagated ingredient betweenness.

Statistical analyses:

- Mann–Whitney U test
- Spearman correlation

Outputs:

- `herb_centrality_analysis.csv`
- `herb_centrality_comparison.png`
- `scatter_bt_comparison.png`

---

## Data Model

The network is heterogeneous and may contain the following node types:

| Node Type | Description |
|------------|------------|
| Herbs | Traditional Chinese medicine herbs |
| Ingredients | Chemical compounds contained in herbs |
| Targets | Molecular targets associated with compounds |
| Diseases | Diseases linked to targets |

Typical biological pathway:

```text
Herb → Ingredient → Target → Disease
```

---

## Output Formats

### GraphML

Used for graph storage and interoperability with:

- NetworkX
- Gephi

### CSV

Used for:

- Centrality metrics
- Component metadata
- Statistical analysis results

---

## Example Analysis Pipeline

---

This pipeline produces a cleaned Herb–Disease network together with
centrality-based analyses of herbs and ingredients.
