#!/opt/homebrew/bin/python3.12
"""
CRG Wrapper: CLI interface for Code Review Graph functions.

Directly imports CRG functions and exposes them as CLI commands.
Handles the sqlite3.Row bug in find_knowledge_gaps via a patch.

Commands:
  hub-nodes, bridge-nodes, communities, arch-overview, flows,
  dead-code, surprising, knowledge-gaps, stats
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, "/opt/homebrew/lib/python3.12/site-packages")

from code_review_graph.graph import GraphStore
from code_review_graph.incremental import get_db_path
from code_review_graph.analysis import (
    find_hub_nodes,
    find_bridge_nodes,
    find_knowledge_gaps,
    find_surprising_connections,
)
from code_review_graph.communities import (
    get_communities,
    get_architecture_overview,
)
from code_review_graph.flows import get_flows
from code_review_graph.refactor import find_dead_code


def _patch_knowledge_gaps_result(rows):
    """Patch sqlite3.Row bug: Row has no .get() method."""
    return [{**dict(r)} for r in rows]


def cmd_stats(repo_path: str) -> dict:
    """Return graph statistics."""
    db_path = get_db_path(Path(repo_path))
    if not Path(db_path).exists():
        return {"available": False, "reason": "Graph not built"}
    store = GraphStore(str(db_path))
    nodes = store.count_nodes()
    edges = store.count_edges()
    files = store.count_files()
    return {
        "available": True,
        "node_count": nodes,
        "edge_count": edges,
        "file_count": files,
    }


def cmd_hub_nodes(repo_path: str, top_n: int = 10) -> dict:
    """Find most connected hub nodes."""
    db_path = get_db_path(Path(repo_path))
    if not Path(db_path).exists():
        return {"available": False, "reason": "Graph not built"}
    store = GraphStore(str(db_path))
    hubs = find_hub_nodes(store, top_n=top_n)
    return {"hubs": hubs, "count": len(hubs)}


def cmd_bridge_nodes(repo_path: str, top_n: int = 10) -> dict:
    """Find structural chokepoints (bridge nodes)."""
    db_path = get_db_path(Path(repo_path))
    if not Path(db_path).exists():
        return {"available": False, "reason": "Graph not built"}
    store = GraphStore(str(db_path))
    bridges = find_bridge_nodes(store, top_n=top_n)
    return {"bridges": bridges, "count": len(bridges)}


def cmd_communities(repo_path: str, min_size: int = 3) -> dict:
    """List code communities."""
    db_path = get_db_path(Path(repo_path))
    if not Path(db_path).exists():
        return {"available": False, "reason": "Graph not built"}
    store = GraphStore(str(db_path))
    comms = get_communities(store, min_size=min_size)
    return {"communities": comms, "count": len(comms)}


def cmd_arch_overview(repo_path: str) -> dict:
    """Generate architecture overview."""
    db_path = get_db_path(Path(repo_path))
    if not Path(db_path).exists():
        return {"available": False, "reason": "Graph not built"}
    store = GraphStore(str(db_path))
    overview = get_architecture_overview(store)
    return overview


def cmd_flows(repo_path: str, limit: int = 50) -> dict:
    """List execution flows."""
    db_path = get_db_path(Path(repo_path))
    if not Path(db_path).exists():
        return {"available": False, "reason": "Graph not built"}
    store = GraphStore(str(db_path))
    flows = get_flows(store, limit=limit)
    return {"flows": flows, "count": len(flows)}


def cmd_dead_code(repo_path: str) -> dict:
    """Find unreferenced functions/classes."""
    db_path = get_db_path(Path(repo_path))
    if not Path(db_path).exists():
        return {"available": False, "reason": "Graph not built"}
    store = GraphStore(str(db_path))
    dead = find_dead_code(store)
    return {"dead_code": dead, "count": len(dead)}


def cmd_surprising(repo_path: str, top_n: int = 15) -> dict:
    """Find unexpected architectural couplings."""
    db_path = get_db_path(Path(repo_path))
    if not Path(db_path).exists():
        return {"available": False, "reason": "Graph not built"}
    store = GraphStore(str(db_path))
    surprising = find_surprising_connections(store, top_n=top_n)
    return {"surprising_connections": surprising, "count": len(surprising)}


def cmd_knowledge_gaps(repo_path: str) -> dict:
    """Find structural weaknesses (untested hotspots)."""
    db_path = get_db_path(Path(repo_path))
    if not Path(db_path).exists():
        return {"available": False, "reason": "Graph not built"}
    store = GraphStore(str(db_path))
    gaps = find_knowledge_gaps(store)
    # Patch sqlite3.Row bug
    gaps_patched = _patch_knowledge_gaps_result(gaps)
    return {"knowledge_gaps": gaps_patched, "count": len(gaps_patched)}


def main():
    parser = argparse.ArgumentParser(
        description="CRG Wrapper CLI — access Code Review Graph functions"
    )
    parser.add_argument("command", choices=[
        "hub-nodes", "bridge-nodes", "communities", "arch-overview",
        "flows", "dead-code", "surprising", "knowledge-gaps", "stats"
    ])
    parser.add_argument("repo_path", help="Path to repository")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--min-size", type=int, default=3)
    parser.add_argument("--limit", type=int, default=50)

    args = parser.parse_args()

    if args.command == "stats":
        result = cmd_stats(args.repo_path)
    elif args.command == "hub-nodes":
        result = cmd_hub_nodes(args.repo_path, top_n=args.top_n)
    elif args.command == "bridge-nodes":
        result = cmd_bridge_nodes(args.repo_path, top_n=args.top_n)
    elif args.command == "communities":
        result = cmd_communities(args.repo_path, min_size=args.min_size)
    elif args.command == "arch-overview":
        result = cmd_arch_overview(args.repo_path)
    elif args.command == "flows":
        result = cmd_flows(args.repo_path, limit=args.limit)
    elif args.command == "dead-code":
        result = cmd_dead_code(args.repo_path)
    elif args.command == "surprising":
        result = cmd_surprising(args.repo_path, top_n=args.top_n)
    elif args.command == "knowledge-gaps":
        result = cmd_knowledge_gaps(args.repo_path)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
