#!/bin/bash
# Security audit helper
# Usage: ./scripts/security-check.sh

set -e

echo "=== Security Audit ==="

# Check for secrets in diff
echo "--- Checking for secrets in diff ---"
git diff | grep -iE "(password|secret|token|api_key)" | grep -v "test" | head -20 || true

# Check for raw SQL
echo "--- Checking for raw SQL ---"
git diff --name-only | grep "\.py$" | xargs grep -n "text(f\"" 2>/dev/null || true
git diff --name-only | grep "\.py$" | xargs grep -n "execute(f\"" 2>/dev/null || true

# Check for missing auth
echo "--- Checking new endpoints for auth ---"
git diff --name-only | grep "api/.*\.py$" | xargs grep -L "Depends(get_current" 2>/dev/null || true

# Check for console.log in frontend
echo "--- Checking for console.log ---"
git diff --name-only | grep "\.vue$\|\.js$" | xargs grep -n "console.log" 2>/dev/null || true

echo ""
echo "=== Security Audit Complete ==="
