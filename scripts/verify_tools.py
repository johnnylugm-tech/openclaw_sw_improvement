#!/opt/homebrew/bin/python3.12
"""
Verify Tools: Check if required quality dimension tools are installed.

Usage:
    python3 scripts/verify_tools.py              # check all
    python3 scripts/verify_tools.py linting      # check specific tool
    python3 scripts/verify_tools.py --list       # show required tools
    python3 scripts/verify_tools.py --install    # show install commands

Exit codes:
    0 = all required tools available
    1 = some tools missing
    2 = error
"""

import shutil
import sys
import json

# Tools required per dimension (matches evaluate_dimension.md)
# Note: type_safety uses pyright, mutation_testing uses pytest-gremlins (pytest plugin)
REQUIRED_TOOLS = {
    "linting":            {"cmd": "pylint",         "package": "pylint",                      "install": "pip install pylint"},
    "type_safety":        {"cmd": "pyright",         "package": "pyright",                     "install": "pip install pyright"},
    "test_coverage":      {"cmd": "pytest",           "package": "pytest pytest-cov",           "install": "pip install pytest pytest-cov"},
    "security":           {"cmd": "bandit",           "package": "bandit",                      "install": "pip install bandit"},
    "readability":        {"cmd": "radon",            "package": "radon",                       "install": "pip install radon"},
    "secrets_scanning":   {"cmd": "gitleaks",         "package": "gitleaks",                    "install": "brew install gitleaks"},
    "license_compliance": {"cmd": "scancode",         "package": "scancode-toolkit",            "install": "pip install scancode-toolkit"},
    "mutation_testing":   {"cmd": "__pytest_gremlins__", "package": "pytest-gremlins", "install": "pip install pytest-gremlins"},
}

ALL_TOOLS = {
    "python":    {"cmd": "python3",        "package": None,                               "install": None},
    "git":      {"cmd": "git",            "package": None,                               "install": None},
    "pylint":   {"cmd": "pylint",         "package": "pylint",                           "install": "pip install pylint"},
    "pyright":  {"cmd": "pyright",         "package": "pyright",                          "install": "pip install pyright"},
    "mypy":     {"cmd": "mypy",            "package": "mypy",                             "install": "pip install mypy"},
    "pytest":   {"cmd": "pytest",           "package": "pytest pytest-cov",                "install": "pip install pytest pytest-cov"},
    "pytest_gremlins": {"cmd": "__pytest_gremlins__", "package": "pytest-gremlins", "install": "pip install pytest-gremlins"},
    "bandit":   {"cmd": "bandit",           "package": "bandit",                          "install": "pip install bandit"},
    "radon":    {"cmd": "radon",            "package": "radon",                            "install": "pip install radon"},
    "gitleaks": {"cmd": "gitleaks",         "package": "gitleaks",                        "install": "brew install gitleaks"},
    "scancode": {"cmd": "scancode",         "package": "scancode-toolkit",                 "install": "pip install scancode-toolkit"},
}


def check_tool(tool_key: str) -> dict:
    """Check if a single tool is available."""
    info = ALL_TOOLS.get(tool_key, {})
    cmd = info.get("cmd", tool_key)

    # pytest-gremlins is a pytest plugin, check via python import
    if cmd == "__pytest_gremlins__":
        try:
            import importlib.util
            spec = importlib.util.find_spec("pytest_gremlins")
            available = spec is not None
        except Exception:
            available = False
    else:
        available = shutil.which(cmd) is not None

    return {
        "tool": tool_key,
        "cmd": cmd,
        "available": available,
        "install": info.get("install"),
        "dimension": next((k for k, v in REQUIRED_TOOLS.items() if v["cmd"] == cmd), None),
    }


def check_all() -> dict:
    """Check all tools and return results."""
    results = {key: check_tool(key) for key in ALL_TOOLS}
    required_results = {dim: check_tool(info["cmd"]) for dim, info in REQUIRED_TOOLS.items()}
    all_available = all(r["available"] for r in required_results.values())
    return {
        "all_required_available": all_available,
        "required_tools": required_results,
        "optional_tools": {k: v for k, v in results.items()
                          if k not in REQUIRED_TOOLS and v["available"]},
    }


def main():
    if len(sys.argv) < 2:
        # Check all
        result = check_all()
        available = [k for k, v in result["required_tools"].items() if v["available"]]
        missing = [k for k, v in result["required_tools"].items() if not v["available"]]
        print(f"Available: {', '.join(available) if available else '(none)'}")
        print(f"Missing:   {', '.join(missing) if missing else '(none)'}")
        if result["all_required_available"]:
            print("\nAll required tools available.")
            sys.exit(0)
        else:
            print("\nSome required tools are missing. Run with --install to see commands.")
            sys.exit(1)

    arg = sys.argv[1]

    if arg == "--list":
        print("Required tools per dimension:")
        for dim, info in REQUIRED_TOOLS.items():
            status = "✓" if check_tool(info["cmd"])["available"] else "✗"
            print(f"  {status} {dim}: {info['cmd']}")
        print("\nOptional tools:")
        for key in ["python", "git", "mypy"]:
            status = "✓" if shutil.which(ALL_TOOLS[key]["cmd"]) else "✗"
            print(f"  {status} {key}: {ALL_TOOLS[key]['cmd']}")
        return

    if arg == "--install":
        result = check_all()
        print("# Install missing tools:")
        for dim, info in result["required_tools"].items():
            if not info["available"] and info["install"]:
                print(f"# {dim} ({info['cmd']})")
                print(f"{info['install']}")
                print()
        return

    # Check specific tool
    if arg in ALL_TOOLS:
        r = check_tool(arg)
        if r["available"]:
            print(f"✓ {arg} found")
            sys.exit(0)
        else:
            install = r["install"] or "(no install command)"
            print(f"✗ {arg} not found. Install: {install}")
            sys.exit(1)

    print(f"Unknown tool: {arg}", file=sys.stderr)
    print(f"Available: {', '.join(ALL_TOOLS.keys())}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
