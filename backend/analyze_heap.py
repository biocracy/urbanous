import json
import sys
import os

# Updated to new snapshot
if len(sys.argv) > 1:
    SNAPSHOT_FILE = sys.argv[1]
else:
    SNAPSHOT_FILE = "Heap.heapsnapshot"

def analyze_heap(filepath):
    print(f"Loading snapshot: {filepath} (This may take a minute)...", flush=True)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load snapshot: {e}", flush=True)
        return

    print("Snapshot loaded. Analyzing...", flush=True)

    snapshot = data.get('snapshot', {})
    nodes = data.get('nodes', [])
    strings = data.get('strings', [])
    
    meta = snapshot.get('meta', {})
    node_fields = meta.get('node_fields', [])
    node_types = meta.get('node_types', [])
    
    try:
        type_idx = node_fields.index('type')
        name_idx = node_fields.index('name')
        self_size_idx = node_fields.index('self_size')
    except ValueError:
        print("Could not find required fields in meta metadata")
        return

    node_stride = len(node_fields)
    node_count = int(len(nodes) / node_stride)
    
    print(f"Total Nodes: {node_count}")
    print(f"Total Strings: {len(strings)}")

    # Analyze Node Types & Frequent Names
    type_counts = {}
    name_counts = {}
    
    actual_node_types = node_types[0] if isinstance(node_types[0], list) else node_types

    print(f"Node Types Definitions: {actual_node_types}")

    for i in range(0, len(nodes), node_stride):
        t_idx = nodes[i + type_idx]
        if t_idx < len(actual_node_types):
            t_name = actual_node_types[t_idx]
        else:
            t_name = "unknown"
            
        type_counts[t_name] = type_counts.get(t_name, 0) + 1
        
        if t_name in ['object', 'native', 'k', 'closure', 'code']: 
            name_offset = nodes[i + name_idx]
            if name_offset < len(strings):
                node_name = strings[name_offset]
                if node_name:
                    name_counts[node_name] = name_counts.get(node_name, 0) + 1

    print("\n--- Node Type Distribution ---")
    for k, v in sorted(type_counts.items(), key=lambda item: item[1], reverse=True):
        print(f"{k}: {v}")

    print("\n--- Top 50 Most Frequent Object Names ---")
    sorted_names = sorted(name_counts.items(), key=lambda item: item[1], reverse=True)
    for k, v in sorted_names[:50]:
        print(f"{k}: {v}")

    print("\n--- Keyword Scan in Top Names ---")
    keywords = ["Mesh", "Geometry", "Buffer", "Texture", "Canvas", "Detached", "react", "Fiber", "Node", "Text"]
    for k, v in sorted_names[:500]:
        for kw in keywords:
            if kw.lower() in k.lower():
                print(f"Found {kw} variant: {k}: {v}")
