#!/opt/homebrew/bin/python3.12
"""
CRG Wrapper: CLI interface for Code Review Graph functions.

No monkey-patching of site-packages. All gap functions are computed locally.

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
    find_hub_nodes, find_bridge_nodes,
    find_surprising_connections,
)
from code_review_graph.communities import (
    get_communities, get_architecture_overview,
)
from code_review_graph.flows import get_flows
from code_review_graph.refactor import find_dead_code


def _store(repo_path):
    db_path = get_db_path(Path(repo_path))
    return GraphStore(db_path)


def _close(store):
    store.close()


def cmd_hub_nodes(repo_path, top_n=10):
    store = _store(repo_path)
    try:
        nodes = find_hub_nodes(store, top_n=top_n)
        return {"hub_nodes": nodes, "count": len(nodes)}
    finally:
        _close(store)


def cmd_bridge_nodes(repo_path, top_n=10):
    store = _store(repo_path)
    try:
        nodes = find_bridge_nodes(store, top_n=top_n)
        return {"bridge_nodes": nodes, "count": len(nodes)}
    finally:
        _close(store)


def cmd_communities(repo_path, min_size=3):
    store = _store(repo_path)
    try:
        comms = get_communities(store, sort_by="size", min_size=min_size)
        return {"communities": comms, "count": len(comms)}
    finally:
        _close(store)


def cmd_arch_overview(repo_path):
    store = _store(repo_path)
    try:
        return get_architecture_overview(store)
    finally:
        _close(store)


def cmd_flows(repo_path, limit=50):
    store = _store(repo_path)
    try:
        flows = get_flows(store, sort_by="criticality", limit=limit)
        return {"flows": flows, "count": len(flows)}
    finally:
        _close(store)


def cmd_dead_code(repo_path):
    store = _store(repo_path)
    try:
        dead = find_dead_code(store)
        return {"dead_code": dead, "count": len(dead)}
    finally:
        _close(store)


def cmd_surprising(repo_path, top_n=15):
    store = _store(repo_path)
    try:
        surp = find_surprising_connections(store, top_n=top_n)
        return {"surprising_connections": surp, "count": len(surp)}
    finally:
        _close(store)


# ---------------------------------------------------------------------------
# cmd_knowledge_gaps — computes all 4 gap types without find_knowledge_gaps
# ---------------------------------------------------------------------------
def _has_test_file(store, file_path):
    """Check if a test file exists for the given source file."""
    if not file_path:
        return False
    cur = store._conn.execute(
        "SELECT COUNT(*) FROM nodes WHERE file_path LIKE ? AND is_test = 1",
        (file_path.replace(".py", "_test.py").replace("/test_", "/"),)
    )
    return cur.fetchone()[0] > 0


def cmd_knowledge_gaps(repo_path):
    """
    Compute structural weaknesses using existing CRG functions.
    Covers:
      - thin_communities:    size < 3
      - single_file_communities: all members from one file
      - untested_hotspots:  hub nodes with no test coverage
      - isolated_nodes:      nodes with zero degree (no edges)
    """
    store = _store(repo_path)
    try:
        gaps = {}

        # 1. thin_communities — size < 3
        all_comms = get_communities(store, sort_by="size")
        gaps["thin_communities"] = [
            {"name": c["name"], "size": c["size"], "cohesion": c["cohesion"],
             "community_id": c["id"]}
            for c in all_comms
            if c.get("size", 0) < 3
        ]

        # 2. single_file_communities — members all from same file
        gaps["single_file_communities"] = []
        for c in all_comms:
            cid = c.get("id")
            if cid is None:
                continue
            cur = store._conn.execute(
                "SELECT DISTINCT file_path FROM nodes WHERE community_id = ? LIMIT 2",
                (cid,)
            )
            rows = cur.fetchall()
            if len(rows) == 1:
                gaps["single_file_communities"].append({
                    "name": c["name"],
                    "size": c["size"],
                    "file": rows[0][0] if rows else None,
                })

        # 3. untested_hotspots — hub nodes without test coverage
        hubs = find_hub_nodes(store, top_n=20)
        gaps["untested_hotspots"] = [
            {"name": h["name"], "file": h.get("file"), "total_degree": h.get("total_degree", 0)}
            for h in hubs
            if h.get("file") and not _has_test_file(store, h.get("file"))
        ]

        # 4. isolated_nodes — zero-degree (no incoming or outgoing edges)
        cur = store._conn.execute("""
            SELECT n.name, n.qualified_name, n.kind, n.file_path
            FROM nodes n
            LEFT JOIN edges e_src ON e_src.source_qualified = n.qualified_name
            LEFT JOIN edges e_dst ON e_dst.target_qualified = n.qualified_name
            WHERE e_src.id IS NULL AND e_dst.id IS NULL
              AND n.kind NOT IN ('File', 'Directory')
            LIMIT 100
        """)
        gaps["isolated_nodes"] = [
            {"name": r[0], "qualified_name": r[1], "kind": r[2], "file": r[3]}
            for r in cur.fetchall()
        ]

        total = sum(len(v) for v in gaps.values())
        return {
            "knowledge_gaps": gaps,
            "count": total,
            "summary": {
                "thin_communities": len(gaps["thin_communities"]),
                "single_file_communities": len(gaps["single_file_communities"]),
                "untested_hotspots": len(gaps["untested_hotspots"]),
                "isolated_nodes": len(gaps["isolated_nodes"]),
            }
        }
    finally:
        _close(store)


# ---------------------------------------------------------------------------
# cmd_suggested_questions — derives questions from computed gaps
# ---------------------------------------------------------------------------
def cmd_suggested_questions(repo_path):
    """
    Generate review questions from structural gaps.
    Questions are mapped to severity buckets:
      - bridge_needs_tests / untested_hubs  → high priority
      - thin_communities / god_modules       → medium priority
      - surprising_connections               → low priority
    """
    gaps_data = cmd_knowledge_gaps(repo_path)
    gaps = gaps_data["knowledge_gaps"]
    questions = []

    # untested_hotspots → "bridge_needs_tests"
    for h in gaps.get("untested_hotspots", []):
        questions.append({
            "category": "untested_hubs",
            "priority": "high",
            "text": f"Hub '{h['name']}' in {h.get('file', 'unknown')} has no test coverage",
            "file": h.get("file"),
            "dimension": "test_coverage",
        })

    # thin_communities → "thin_communities"
    for c in gaps.get("thin_communities", []):
        questions.append({
            "category": "thin_communities",
            "priority": "medium",
            "text": f"Community '{c['name']}' has only {c['size']} members — consider merging",
            "file": None,
            "dimension": "architecture",
        })

    # single_file_communities → "god_modules"
    for c in gaps.get("single_file_communities", []):
        if c.get("size", 0) > 10:
            questions.append({
                "category": "god_modules",
                "priority": "high",
                "text": f"Single-file community '{c['name']}' has {c['size']} nodes — possible god module",
                "file": c.get("file"),
                "dimension": "architecture",
            })

    # isolated_nodes → "dead_code"
    for n in gaps.get("isolated_nodes", [])[:10]:
        questions.append({
            "category": "dead_code",
            "priority": "low",
            "text": f"'{n['name']}' has no connections — possible dead code",
            "file": n.get("file"),
            "dimension": "architecture",
        })

    by_priority = {"high": 0, "medium": 0, "low": 0}
    for q in questions:
        p = q.get("priority", "low")
        if p in by_priority:
            by_priority[p] += 1

    return {
        "questions": questions,
        "count": len(questions),
        "by_priority": by_priority,
    }


def cmd_stats(repo_path):
    db_path = get_db_path(Path(repo_path))
    if not db_path.exists():
        return {"available": False, "reason": "no graph DB found"}
    store = _store(repo_path)
    try:
        node_count = store._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edge_count = store._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        file_count = store._conn.execute(
            "SELECT COUNT(DISTINCT file_path) FROM nodes WHERE kind = 'File'"
        ).fetchone()[0]
        return {
            "available": True,
            "node_count": node_count,
            "edge_count": edge_count,
            "file_count": file_count,
        }
    finally:
        _close(store)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
COMMANDS = {
    "hub-nodes":            (cmd_hub_nodes,            {"top_n"}),
    "bridge-nodes":         (cmd_bridge_nodes,           {"top_n"}),
    "communities":          (cmd_communities,           {"min_size"}),
    "arch-overview":         (cmd_arch_overview,          set()),
    "flows":                (cmd_flows,                 {"limit"}),
    "dead-code":            (cmd_dead_code,             set()),
    "surprising":            (cmd_surprising,            {"top_n"}),
    "knowledge-gaps":        (cmd_knowledge_gaps,          set()),
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
