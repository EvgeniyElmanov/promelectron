#!/bin/bash
# Quick code review helper
# Usage: ./scripts/review.sh [--security-only] [--quick]

set -e

echo "=== Code Review ==="
echo "Branch: $(git branch --show-current)"
echo "Last commit: $(git log -1 --oneline)"
echo ""

echo "=== Git Status ==="
git status --short
echo ""

echo "=== Changed Files ==="
git diff --name-only
echo ""

if [[ "$1" == "--security-only" ]]; then
    echo "=== Security Check ==="
    # Check for common security issues
    git diff | grep -n "print(" || true
    git diff | grep -n "console.log" || true
    git diff | grep -n "SELECT.*f\"" || true
    git diff | grep -n "text(f\"" || true
    exit 0
fi

echo "=== Running Tests ==="
cd server && python -m pytest ../tests/ -q 2>&1 | tail -5 || true
cd ../client && npm test -- --run 2>&1 | tail -5 || true
echo ""

echo "=== Lint Check ==="
cd server && ruff check app --quiet 2>&1 || true
echo ""

echo "=== Review Complete ==="
