import requests
import time
import json
import os
import sys
import fcntl
import random
from requests.exceptions import RequestException
from http.client import IncompleteRead
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
 
BASE_URL = "https://tcmbank.cn/api/relation"
 
VISITED_FILE    = "visited.json"
QUEUE_FILE      = "queue.json"
FAILED_FILE     = "failed.json"
FAIL_COUNTS_FILE = "fail_counts.json"
LOCK_FILE       = "crawler.lock"   # prevents concurrent executions
 
os.makedirs("data", exist_ok=True)
 
MAX_WORKERS  = 3
TIMEOUT      = 20
RETRIES      = 3
MAX_REQUEUES = 3
 
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})
 
 
# Lock
 
def acquire_lock():
    """
    Acquire an exclusive file lock to prevent concurrent crawler executions.

    If another instance is already running, the program exits silently.

    Returns:
        file object: Lock file descriptor (must be kept open).
    """
    lock = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Another instance is already running. Exiting.")
        sys.exit(0)
    return lock
 
def release_lock(lock):
    """
    Release the file lock and remove the lock file.

    Args:
        lock (file object): The lock file descriptor.
    """
    fcntl.flock(lock, fcntl.LOCK_UN)
    lock.close()
    try:
        os.remove(LOCK_FILE)
    except FileNotFoundError:
        pass
 
 
# State management
 
def load_state(seed_ids, retry_failed=False):
    """
    Load crawler state from disk.

    Includes:
        - visited nodes
        - queue
        - failure counts
        - permanently failed nodes

    Optionally requeues previously failed nodes.

    Args:
        seed_ids (list): Initial seed node IDs.
        retry_failed (bool): Whether to retry previously failed nodes.

    Returns:
        tuple: (visited, queue, fail_counts, failed)
    """
    visited = set(json.load(open(VISITED_FILE))) if os.path.exists(VISITED_FILE) else set()
    queue   = deque(json.load(open(QUEUE_FILE))) if os.path.exists(QUEUE_FILE)   else deque()
    fail_counts = json.load(open(FAIL_COUNTS_FILE)) if os.path.exists(FAIL_COUNTS_FILE) else {}
    failed  = set(json.load(open(FAILED_FILE)))  if os.path.exists(FAILED_FILE)  else set()
 
    if not queue:
        print("Queue is empty → reinitializing with seed nodes")
        for s in seed_ids:
            if s not in visited:
                queue.append(s)
            visited.add(s)
 
    if retry_failed and failed:
        print(f"Requeueing {len(failed)} previously failed nodes...")
        for node in failed:
            visited.discard(node)
            fail_counts.pop(node, None)
            queue.appendleft(node) 
        failed.clear()
 
    return visited, queue, fail_counts, failed
 
 
def save_state(visited, queue, fail_counts, failed):
    """
    Persist crawler state to disk.

    Args:
        visited (set): Visited node IDs.
        queue (deque): Pending nodes.
        fail_counts (dict): Failure counters per node.
        failed (set): Nodes that exceeded retry limit.
    """
    with open(VISITED_FILE,     "w") as f: json.dump(list(visited),     f)
    with open(QUEUE_FILE,       "w") as f: json.dump(list(queue),       f)
    with open(FAIL_COUNTS_FILE, "w") as f: json.dump(fail_counts,       f)
    with open(FAILED_FILE,      "w") as f: json.dump(list(failed),      f)
 
 
# Fetching
 
def fetch_relations(tcmbank_id, rel_type):
    """
    Fetch relations for a given TCMBank node.

    Retries the request on failure using exponential backoff with jitter.

    Args:
        tcmbank_id (str): Node ID.
        rel_type (str): Type of relation to query.

    Returns:
        tuple: (tcmbank_id, rel_type, json_data or None)
    """
    for attempt in range(RETRIES):
        try:
            response = session.get(
                BASE_URL,
                params={"tcmbank_id": tcmbank_id, "type": rel_type, "slice_length": ""},
                timeout=TIMEOUT
            )
            response.raise_for_status()
            return tcmbank_id, rel_type, response.json()
        except (RequestException, IncompleteRead) as e:
            print(f"Error for {tcmbank_id} ({rel_type}) attempt {attempt+1}: {e}")
            time.sleep(3 * (attempt + 1) + random.uniform(0, 2))
    return tcmbank_id, rel_type, None
 
 
def extract_ids(json_data):
    """
    Extract TCMBank IDs from API response.

    Args:
        json_data (dict): API response.

    Returns:
        set: Extracted node IDs.
    """
    ids = set()
    if not json_data:
        return ids
    for item in json_data.get("data", {}).get("chart_data", []):
        if "TCMBank_ID" in item:
            ids.add(item["TCMBank_ID"])
    return ids
 
 
def get_type_from_id(tcmbank_id):
    """
    Infer node type from its TCMBank ID prefix.

    Args:
        tcmbank_id (str): Node ID.

    Returns:
        str or None: Node type.
    """
    if tcmbank_id.startswith("TCMBANKHE"): return "Herbs"
    if tcmbank_id.startswith("TCMBANKDI"): return "Diseases"
    if tcmbank_id.startswith("TCMBANKIN"): return "Ingredients"
    if tcmbank_id.startswith("TCMBANKGE"): return "Targets"
    return None
 
 
def process_batch(batch):
    """
    Process a batch of node IDs concurrently.

    Args:
        batch (list): List of node IDs.

    Returns:
        list: Results from fetch_relations.
    """
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(fetch_relations, nid, get_type_from_id(nid))
            for nid in batch if get_type_from_id(nid)
        ]
        for future in as_completed(futures):
            results.append(future.result())
    return results
 
 
# Crawl
 
def crawl(seed_ids, max_steps=100, retry_failed=False):
    """
    Run the crawler starting from seed nodes.

    The crawler:
        - Expands nodes via API relations
        - Stores results to disk
        - Maintains persistent state
        - Handles retries and failures

    Args:
        seed_ids (list): Initial node IDs.
        max_steps (int): Maximum number of processed nodes.
        retry_failed (bool): Whether to retry failed nodes.
    """
    lock = acquire_lock()
 
    try:
        visited, queue, fail_counts, failed = load_state(seed_ids, retry_failed=retry_failed)
        steps = 0
 
        while queue and steps < max_steps:
            batch = [queue.popleft() for _ in range(min(len(queue), MAX_WORKERS))]
 
            print(f"[{steps}] Batch={len(batch)} | queue={len(queue)} visited={len(visited)} failed={len(failed)}")
 
            for current_id, rel_type, data in process_batch(batch):
                if not data:
                    fail_counts[current_id] = fail_counts.get(current_id, 0) + 1
                    if fail_counts[current_id] < MAX_REQUEUES:
                        print(f"Requeue {current_id} (failure {fail_counts[current_id]}/{MAX_REQUEUES})")
                        queue.append(current_id)
                    else:
                        print(f"Dropping {current_id} after {MAX_REQUEUES} retries")
                        failed.add(current_id)
                    continue
 
                filename = f"data/{current_id}_{rel_type}.json"
                if not os.path.exists(filename):
                    tmp = filename + ".tmp"
                    with open(tmp, "w") as f:
                        json.dump(data, f)
                    os.replace(tmp, filename)
 
                new_ids = extract_ids(data)
                print(f"{current_id} -> found {len(new_ids)} new ids")
 
                for nid in new_ids:
                    if nid not in visited:
                        visited.add(nid)
                        queue.append(nid)
 
            time.sleep(random.uniform(0.3, 0.7))
            steps += len(batch)
 
            if steps % 50 == 0:
                save_state(visited, queue, fail_counts, failed)
 
        save_state(visited, queue, fail_counts, failed)
 
        if failed:
            print(f"\n{len(failed)} nodes permanently failed:")
            for node in sorted(failed):
                print(f"  - {node}")
        else:
            print("\nAll nodes processed successfully")
 
    finally:
        release_lock(lock)
 
 
if __name__ == "__main__":
    seed = ["TCMBANKHE000001"]
 
    # retry_failed=True → requeues nodes from failed.json
    crawl(seed, retry_failed=True)
