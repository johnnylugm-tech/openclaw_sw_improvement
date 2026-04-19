#!/bin/bash
# install_crg.sh — Install CRG with RowWithGet patch
# Run once per machine. Idempotent.

set -e

PYTHON="/opt/homebrew/bin/python3.12"
CRG_PY="/opt/homebrew/lib/python3.12/site-packages/code_review_graph/graph.py"

echo "[install_crg] Starting..."

# Step 1: Install/update CRG
echo "[install_crg] Installing code-review-graph..."
if ! pip3 install --break-system-packages --upgrade --force-reinstall code-review-graph 2>&1 | tail -3; then
    echo "[install_crg] ERROR: pip install failed"
    exit 1
fi

# Step 2: Apply RowWithGet patch if not already present
echo "[install_crg] Checking CRG patch..."
PATCHED=$(grep -c "class RowWithGet" "$CRG_PY" 2>/dev/null || echo 0)
if [ "$PATCHED" -gt 0 ]; then
    echo "[install_crg] Already patched. Skipping."
else
    echo "[install_crg] Patching graph.py..."
    python3 << PYEOF
import sqlite3
from pathlib import Path

graph_py = Path("$CRG_PY")
content = graph_py.read_text()

class_def = '''
# --- OpenClaw CRG patch: sqlite3.Row has no .get() in Python 3.12 ---
class RowWithGet(sqlite3.Row):
    def get(self, key, default=None):
        try:
            return sqlite3.Row.__getitem__(self, key)
        except (KeyError, IndexError, TypeError):
            return default

'''

# Inject after "import sqlite3\n"
if "import sqlite3" in content and "class RowWithGet" not in content:
    content = content.replace("import sqlite3\n", "import sqlite3\n" + class_def + "\n", 1)
    content = content.replace(
        "self._conn.row_factory = sqlite3.Row",
        "self._conn.row_factory = RowWithGet"
    )
    graph_py.write_text(content)
    print("[install_crg] graph.py patched successfully")
else:
    print("[install_crg] Patch not needed or already present")
PYEOF
fi

# Step 3: Verify
echo "[install_crg] Verifying..."
$PYTHON -c "
import sys; sys.path.insert(0, '/opt/homebrew/lib/python3.12/site-packages')
from code_review_graph.graph import GraphStore
from code_review_graph.analysis import find_knowledge_gaps
print('[install_crg] CRG import OK')
print('[install_crg] find_knowledge_gaps:', hasattr(find_knowledge_gaps, '__call__'))
"

echo "[install_crg] Done."
