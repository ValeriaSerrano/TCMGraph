# TCMGraph
This project builds and analyzes a graph from TCMBank data by:

1. Crawling relations from the TCMBank API
2. Storing raw JSON responses
3. Building a graph dataset (nodes and edges)
4. Visualizing a sampled subgraph

---

## Requirements

Python 3.8+

### Dependencies

Install with:

```bash
pip install requests networkx matplotlib
```

### Standard library modules used

No installation needed:

* `json`
* `os`
* `csv`
* `time`
* `random`
* `pathlib`
* `collections`
* `concurrent.futures`
* `fcntl` *(Unix only)*

---

## Usage

### 1. Run the crawler

```bash
python tcm_crawler.py
```

* Starts from seed nodes
* Stores results in `data/`
* Saves progress automatically (can resume)

---

### 2. Build the graph

```bash
python build_graph.py
```

* Reads JSON files from `data/`
* Generates:

  * `nodes.csv`
  * `edges.csv`

---

### 3. Visualize the graph

```bash
python visualize_graph.py
```

* Prints graph statistics
* Generates a visualization image:

  * `tcmbank_graph.png`

