"""
Builds a TCMBank subgraph from a subset of downloaded JSON files.

The script loads a list of visited TCMBank identifiers, selects the first
N identifiers, locates the corresponding JSON files, constructs a NetworkX
graph from the extracted entities and relationships, and exports the
resulting graph to GraphML format.
"""
import json
from pathlib import Path
import networkx as nx
from tqdm import tqdm

DATA_FOLDER = "data/data"
VISITED_FILE = "visited_backup.json" # File with list of IDs
N_FIRST = 1000 # Change to the desired number (e.g. 100, 5000, etc.)

def load_visited_ids(visited_path, n):
    """
    Load the first `n` identifiers from a JSON file.

    Args:
        visited_path (str | Path): Path to the JSON file containing a list
            of visited identifiers.
        n (int): Maximum number of identifiers to load.

    Returns:
        list: A list containing the first `n` identifiers from the file.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
        json.JSONDecodeError: If the file content is not valid JSON.
    """
    with open(visited_path, 'r', encoding='utf-8') as f:
        all_ids = json.load(f)
    return all_ids[:n]

def find_json_files_for_ids(folder, ids):
    """
    Find JSON files whose filename prefix matches one of the provided IDs.

    The function scans all JSON files in the specified folder and extracts
    the identifier located before the first underscore in each filename.
    Files with matching identifiers are returned.

    Args:
        folder (str | Path): Directory containing JSON files.
        ids (set | list): Collection of identifiers to search for.

    Returns:
        list[Path]: Paths to matching JSON files.
    """
    json_files = []
    for file_path in Path(folder).glob("*.json"):
        # The file name without extension, e.g., "TCMBANKDI002896_Diseases"
        stem = file_path.stem
        # We extract the part before the first '_' (the ID)
        file_id = stem.split('_')[0]
        if file_id in ids:
            json_files.append(file_path)
    return json_files

def load_json_files(file_paths):
    """
    Load and validate data from a collection of JSON files.

    Only files containing both the ``status`` and ``data`` fields are
    considered valid. The value of the ``data`` field is extracted and
    stored in the returned list.

    Args:
        file_paths (list[Path]): List of JSON file paths to load.

    Returns:
        list[dict]: List of valid data objects extracted from the files.

    Notes:
        Invalid files are skipped and the corresponding error is printed.
    """
    data_list = []
    for file_path in tqdm(file_paths, desc="Cargando JSONs"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("status") and data.get("data"):
                    data_list.append(data["data"])
        except Exception as e:
            print(f"Error en {file_path}: {e}")
    return data_list

def build_graph(data_list):
    """
    Build an undirected graph from TCMBank relationship data.

    Nodes are created from the ``chart_data`` field and edges are created
    from the ``data_links`` field. Node attributes include the entity name
    and record type.

    Args:
        data_list (list[dict]): Collection of parsed TCMBank data objects.

    Returns:
        networkx.Graph: Graph containing all nodes and relationships found
        in the input data.
    """
    G = nx.Graph()
    for data in tqdm(data_list, desc="Procesando nodos y aristas"):
        chart_data = data.get("chart_data", [])
        data_links = data.get("data_links", [])
        # Add nodes
        for node_info in chart_data:
            node_id = node_info["TCMBank_ID"]
            node_name = node_info["name"]
            node_type = node_info["record_type"]
            if not G.has_node(node_id):
                G.add_node(node_id, name=node_name, type=node_type)
        # Add edges
        for link in data_links:
            src_idx = link["source"]
            tgt_idx = link["target"]
            if src_idx < len(chart_data) and tgt_idx < len(chart_data):
                src_id = chart_data[src_idx]["TCMBank_ID"]
                tgt_id = chart_data[tgt_idx]["TCMBank_ID"]
                G.add_edge(src_id, tgt_id)
    return G

def clean_attributes(G):
    """
    Sanitize graph attributes for GraphML export.

    GraphML supports only a limited set of attribute types. This function
    replaces ``None`` values with empty strings and converts unsupported
    attribute types to strings.

    Args:
        G (networkx.Graph): Graph whose node and edge attributes will be
            cleaned.

    Returns:
        networkx.Graph: The cleaned graph.
    """
    for node, attrs in G.nodes(data=True):
        for key, value in list(attrs.items()):
            if value is None:
                attrs[key] = ""
            elif not isinstance(value, (str, int, float, bool)):
                attrs[key] = str(value)
    for u, v, attrs in G.edges(data=True):
        for key, value in list(attrs.items()):
            if value is None:
                attrs[key] = ""
            elif not isinstance(value, (str, int, float, bool)):
                attrs[key] = str(value)
    return G

def export_to_graphml(G, output_file="tcm_subgraph.graphml"):
    """
    Export a graph to GraphML format.

    A copy of the graph is first sanitized to ensure all attributes are
    compatible with GraphML serialization.

    Args:
        G (networkx.Graph): Graph to export.
        output_file (str, optional): Destination GraphML file path.
            Defaults to ``tcm_subgraph.graphml``.

    Returns:
        None
    """
    G_clean = clean_attributes(G.copy())
    nx.write_graphml(G_clean, output_file)
    print(f"Grafo exportado a {output_file}")

if __name__ == "__main__":
    # Upload first N IDs from visited.json
    print(f"Cargando primeros {N_FIRST} IDs desde {VISITED_FILE}...")
    selected_ids = set(load_visited_ids(VISITED_FILE, N_FIRST))
    print(f"IDs seleccionados: {len(selected_ids)}")

    # Find matching JSON files
    print("Buscando archivos JSON...")
    json_paths = find_json_files_for_ids(DATA_FOLDER, selected_ids)
    print(f"Se encontraron {len(json_paths)} archivos.")

    # Upload data from those files
    all_data = load_json_files(json_paths)
    print(f"Se cargaron {len(all_data)} conjuntos de datos válidos.")

    # Construct graph
    print("Construyendo grafo...")
    G = build_graph(all_data)
    print(f"Grafo final: {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas.")

    # Export to GraphML
    export_to_graphml(G, "tcm_subgraph.graphml")