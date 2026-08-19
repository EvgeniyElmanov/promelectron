#!/usr/bin/env python3
"""
MCP server for Atlassian (Jira + Confluence) — stdio transport.

Exposes tools:
- jira_get_issue
- jira_search_issues
- confluence_get_page
- confluence_search_pages

Auth: ATLASSIAN_URL, ATLASSIAN_USERNAME, ATLASSIAN_API_TOKEN env vars.
API token is created at https://id.atlassian.com/manage-profile/security/api-tokens

Usage:
    ATLASSIAN_URL=https://your-domain.atlassian.net \
    ATLASSIAN_USERNAME=email@example.com \
    ATLASSIAN_API_TOKEN=xxx \
    python scripts/mcp_atlassian.py
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def _env(name: str) -> str | None:
    return os.environ.get(name)


def _basic_auth() -> str:
    user = _env("ATLASSIAN_USERNAME") or ""
    token = _env("ATLASSIAN_API_TOKEN") or ""
    creds = base64.b64encode(f"{user}:{token}".encode("utf-8")).decode("ascii")
    return f"Basic {creds}"


def _base_url() -> str | None:
    url = _env("ATLASSIAN_URL")
    if not url:
        return None
    return url.rstrip("/")


def _request(path: str) -> dict[str, Any]:
    base = _base_url()
    if not base:
        return {"error": "ATLASSIAN_URL is not set"}
    if not _env("ATLASSIAN_USERNAME") or not _env("ATLASSIAN_API_TOKEN"):
        return {"error": "ATLASSIAN_USERNAME and ATLASSIAN_API_TOKEN must be set"}

    url = f"{base}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": _basic_auth(),
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {exc.code}", "body": body, "url": url}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "url": url}


def handle_initialize(_params: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "promelectron-atlassian-mcp", "version": "0.1.0"},
    }


def handle_tools_list(_params: dict[str, Any]) -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": "jira_get_issue",
                "description": "Get Jira issue details by key (e.g. PROJ-123).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "issue_key": {"type": "string"},
                    },
                    "required": ["issue_key"],
                },
            },
            {
                "name": "jira_search_issues",
                "description": "Search Jira issues using JQL. Max 50 results.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "jql": {"type": "string", "description": "JQL query string"},
                        "max_results": {"type": "integer", "default": 50},
                    },
                    "required": ["jql"],
                },
            },
            {
                "name": "confluence_get_page",
                "description": "Get Confluence page content by page ID.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "page_id": {"type": "string"},
                    },
                    "required": ["page_id"],
                },
            },
            {
                "name": "confluence_search_pages",
                "description": "Search Confluence pages by CQL. Max 50 results.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cql": {"type": "string", "description": "Confluence CQL query"},
                        "limit": {"type": "integer", "default": 20},
                    },
                    "required": ["cql"],
                },
            },
        ]
    }


def _truncate(text: str, limit: int = 100_000) -> str:
    if len(text) > limit:
        return text[:limit] + "\n\n[truncated]"
    return text


def handle_tool_call(params: dict[str, Any]) -> dict[str, Any] | None:
    name = params.get("name")
    arguments = params.get("arguments") or {}

    if name == "jira_get_issue":
        key = arguments.get("issue_key", "")
        result = _request(f"/rest/api/2/issue/{key}?fields=summary,description,status,labels,components,customfield_*")
    elif name == "jira_search_issues":
        jql = arguments.get("jql", "")
        max_results = min(arguments.get("max_results", 50), 100)
        query = urllib.parse.urlencode({"jql": jql, "maxResults": max_results})
        result = _request(f"/rest/api/2/search?{query}")
    elif name == "confluence_get_page":
        page_id = arguments.get("page_id", "")
        result = _request(f"/wiki/rest/api/content/{page_id}?expand=body.storage,space")
    elif name == "confluence_search_pages":
        cql = arguments.get("cql", "")
        limit = min(arguments.get("limit", 20), 50)
        query = urllib.parse.urlencode({"cql": cql, "limit": limit})
        result = _request(f"/wiki/rest/api/content/search?{query}")
    else:
        return None  # unknown tool

    text = json.dumps(result, ensure_ascii=False, indent=2)
    return {"content": [{"type": "text", "text": _truncate(text)}]}


def _method_not_found(msg_id: Any, message: str) -> None:
    response = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": message}}
    print(json.dumps(response, ensure_ascii=False), flush=True)


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params") or {}

        if msg_id is None:
            continue  # JSON-RPC notification — no response

        try:
            if method == "initialize":
                result = handle_initialize(params)
            elif method == "tools/list":
                result = handle_tools_list(params)
            elif method == "tools/call":
                result = handle_tool_call(params)
                if result is None:
                    _method_not_found(msg_id, f"Unknown tool: {params.get('name')}")
                    continue
            else:
                _method_not_found(msg_id, f"Method not supported: {method}")
                continue
        except Exception as exc:  # noqa: BLE001
            result = {"content": [{"type": "text", "text": f"Error: {exc}"}], "isError": True}

        response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
