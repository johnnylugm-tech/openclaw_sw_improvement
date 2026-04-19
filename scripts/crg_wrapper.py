#!/opt/homebrew/bin/python3.12
"""
CRG Wrapper: CLI interface for Code Review Graph functions.

Requires: code-review-graph installed, graph.py patched with RowWithGet.
(no longer needs sqlite3.Row patching in this file)

Commands: hub-nodes, bridge-nodes, communities, arch-overview, flows,
          dead-code, surprising, knowledge-gaps, stats, suggested-questions
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, "/opt/homebrew/lib/python3.12/site-packages")

from code_review_graph.graph import GraphStore
from code_review_graph.incremental import get_db_path
from code_review_graph.analysis import (
    find_hub_nodes, find_bridge_nodes, find_knowledge_gaps,
    find_surprising_connections, generate_suggested_questions,
)
from code_review_graph.communities import get_communities, get_architecture_overview
from code_review_graph.flows import get_flows
from code_review_graph.refactor import find_dead_code


def _store(repo_path):
    db_path = get_db_path(Path(repo_path))
    store = GraphStore(db_path)
    return store


def cmd_hub_nodes(repo_path, top_n=10):
    store = _store(repo_path)
    try:
        nodes = find_hub_nodes(store, top_n=top_n)
        return {"hub_nodes": nodes, "count": len(nodes)}
    finally:
        store.close()

def cmd_bridge_nodes(repo_path, top_n=10):
    store = _store(repo_path)
    try:
        nodes = find_bridge_nodes(store, top_n=top_n)
        return {"bridge_nodes": nodes, "count": len(nodes)}
    finally:
        store.close()

def cmd_communities(repo_path, min_size=3):
    store = _store(repo_path)
    try:
        comms = get_communities(store, sort_by="size", min_size=min_size)
        return {"communities": comms, "count": len(comms)}
    finally:
        store.close()

def cmd_arch_overview(repo_path):
    store = _store(repo_path)
    try:
        return get_architecture_overview(store)
    finally:
        store.close()

def cmd_flows(repo_path, limit=50):
    store = _store(repo_path)
    try:
        flows = get_flows(store, sort_by="criticality", limit=limit)
        return {"flows": flows, "count": len(flows)}
    finally:
        store.close()

def cmd_dead_code(repo_path):
    store = _store(repo_path)
    try:
        dead = find_dead_code(store)
        return {"dead_code": dead, "count": len(dead)}
    finally:
        store.close()

def cmd_surprising(repo_path, top_n=15):
    store = _store(repo_path)
    try:
        surp = find_surprising_connections(store, top_n=top_n)
        return {"surprising_connections": surp, "count": len(surp)}
    finally:
        store.close()

def cmd_knowledge_gaps(repo_path):
    store = _store(repo_path)
    try:
        gaps = find_knowledge_gaps(store)
        return {"knowledge_gaps": gaps, "count": len(gaps)}
    finally:
        store.close()

def cmd_suggested_questions(repo_path):
    store = _store(repo_path)
    try:
        qs = generate_suggested_questions(store)
        return {"questions": qs, "count": len(qs)}
    finally:
        store.close()

def cmd_stats(repo_path):
    db_path = get_db_path(Path(repo_path))
    if not db_path.exists():
        return {"available": False, "reason": "no graph DB found"}
    store = _store(repo_path)
    try:
        cur = store._conn.execute(
            "SELECT key, value FROM metadata "
            "WHERE key IN ('node_count','edge_count','file_count','schema_version')"
        )
        rows = cur.fetchall()
        stats = {str(r[0]): r[1] for r in rows}
        return {
            "available": True,
            "node_count": int(stats.get("node_count", 0)),
            "edge_count": int(stats.get("edge_count", 0)),
            "file_count": int(stats.get("file_count", 0)),
        }
    finally:
        store.close()


COMMANDS = {
    "hub-nodes":            (cmd_hub_nodes,            {"top_n"}),
    "bridge-nodes":         (cmd_bridge_nodes,          {"top_n"}),
    "communities":          (cmd_communities,          {"min_size"}),
    "arch-overview":         (cmd_arch_overview,         set()),
    "flows":                (cmd_flows,                {"limit"}),
    "dead-code":            (cmd_dead_code,              set()),
    "surprising":            (cmd_surprising,            {"top_n"}),
    "knowledge-gaps":       (cmd_knowledge_gaps,         set()),
    "suggested-questions":   (cmd_suggested_questions,    set()),
    "stats":                (cmd_stats,                 set()),
}

def main():
    parser = argparse.ArgumentParser(description="CRG Wrapper CLI")
    parser.add_argument("command", choices=list(COMMANDS.keys()))
    parser.add_argument("repo", help="Path to repository")
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--min-size", type=int, default=3)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    fn, opts = COMMANDS[args.command]
    kwargs = {}
    if "top_n" in opts:     kwargs["top_n"] = args.top_n
    if "min_size" in opts:  kwargs["min_size"] = args.min_size
    if "limit" in opts:     kwargs["limit"] = args.limit
    result = fn(args.repo, **kwargs)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
