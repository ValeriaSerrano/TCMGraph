"""
Validate and clean a TCMBank visited ID list.

This script compares the identifiers stored in ``visited.json`` against
the JSON files currently available in the dataset directory. Any identifier
that does not correspond to an existing JSON file is removed from the
visited list.

Before modifying the file, a backup copy of the original visited list is
created. The script reports the number of identifiers preserved and removed.

Input:
    - Dataset directory containing TCMBank JSON files.
    - A visited.json file containing a list of previously processed IDs.

Output:
    - A cleaned version of visited.json.
    - A backup of the original visited.json file.
    - Summary statistics about the cleaning process.
"""
import json
from pathlib import Path


DATA_FOLDER = "data/data" # Folder where the JSON are
VISITED_FILE = "visited.json" # File with the list of IDs
BACKUP_FILE = "visited_backup.json" # Backup


def get_existing_ids(data_folder):
    """
    Extract all valid entity identifiers from JSON filenames.

    The identifier is assumed to be the portion of the filename that
    appears before the first underscore character. If no underscore is
    present, the entire filename stem is used.

    Args:
        data_folder (str | Path): Directory containing JSON files.

    Returns:
        set[str]: Set of identifiers corresponding to existing JSON files.

    Notes:
        Filenames are expected to follow the TCMBank naming convention,
        for example:
            TCMBANKDI002896_Diseases.json
        where ``TCMBANKDI002896`` is the extracted identifier.
    """
    existing_ids = set()
    data_path = Path(data_folder)
    if not data_path.exists():
        print(f"La carpeta {data_folder} no existe.")
        return existing_ids
    for file_path in data_path.glob("*.json"):
        stem = file_path.stem
        # Example: "TCMBANKDI002896_Diseases" -> ID = "TCMBANKDI002896
        if '_' in stem:
            file_id = stem.split('_')[0]
            existing_ids.add(file_id)
        else:
            # If you don’t have '_', we use the full name
            existing_ids.add(stem)
    return existing_ids

def clean_visited(visited_path, existing_ids, backup_path):
    """
    Remove invalid identifiers from a visited ID list.

    The function loads a JSON file containing visited identifiers,
    retains only those identifiers that correspond to existing files,
    creates a backup of the original list, and saves the cleaned
    version back to disk.

    Args:
        visited_path (str | Path): Path to the visited.json file.
        existing_ids (set[str]): Set of valid identifiers currently
            present in the dataset.
        backup_path (str | Path): Path where the backup file will be
            written.

    Returns:
        list[str]: The filtered list of valid identifiers.

    Raises:
        FileNotFoundError: If the visited file does not exist.
        json.JSONDecodeError: If the visited file contains invalid JSON.

    Side Effects:
        - Creates a backup file containing the original ID list.
        - Overwrites the original visited.json file with the cleaned list.
        - Prints summary statistics to standard output.
    """
    # Read visited.json
    with open(visited_path, 'r', encoding='utf-8') as f:
        original_ids = json.load(f)
    
    # Original IDs (duplicates may be possible, we assume list)
    original_count = len(original_ids)
    
    # Filter
    cleaned_ids = [id_ for id_ in original_ids if id_ in existing_ids]
    removed_count = original_count - len(cleaned_ids)
    
    # Create backup
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(original_ids, f, indent=2)
    print(f"Backup guardado en {backup_path}")
    
    # Save clean version
    with open(visited_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_ids, f, indent=2)
    
    print(f"IDs originales: {original_count}")
    print(f"IDs eliminados: {removed_count}")
    print(f"IDs conservados: {len(cleaned_ids)}")
    if removed_count > 0:
        removed_set = set(original_ids) - existing_ids
        print("Ejemplo de IDs eliminados:", list(removed_set)[:10])
    return cleaned_ids

if __name__ == "__main__":
    # Scan the dataset directory and collect all identifiers
    # associated with existing JSON files.
    print("Buscando archivos JSON en:", DATA_FOLDER)
    existing = get_existing_ids(DATA_FOLDER)
    print(f"IDs encontrados en data: {len(existing)}")
    
    # Clean the visited ID list by removing identifiers that
    # no longer correspond to files in the dataset.
    if Path(VISITED_FILE).exists():
        clean_visited(VISITED_FILE, existing, BACKUP_FILE)
    else:
        print(f"No se encontró {VISITED_FILE} en el directorio actual.")