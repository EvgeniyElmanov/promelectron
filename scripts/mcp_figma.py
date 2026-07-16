#!/usr/bin/env python3
"""
MCP server for Figma — stdio transport.

Reads Figma REST API and exposes design data as MCP tools:
- get_file
- get_variables
- get_styles
- get_components
- get_design_tokens

Auth: FIGMA_ACCESS_TOKEN env var.

Usage:
    FIGMA_ACCESS_TOKEN=xxx python scripts/mcp_figma.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

FIGMA_API_BASE = "https://api.figma.com/v1"


def _figma_token() -> str | None:
    return os.environ.get("FIGMA_ACCESS_TOKEN")


def _figma_request(path: str) -> dict[str, Any]:
    token = _figma_token()
    if not token:
        return {"error": "FIGMA_ACCESS_TOKEN is not set"}
    url = f"{FIGMA_API_BASE}{path}"
    req = urllib.request.Request(
        url,
        headers={"X-Figma-Token": token, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {exc.code}", "body": body}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def handle_initialize(_params: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "promelectron-figma-mcp", "version": "0.1.0"},
    }


def handle_tools_list(_params: dict[str, Any]) -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": "get_file",
                "description": "Get Figma file metadata and document tree (top-level nodes only).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string", "description": "Figma file key from URL"},
                        "node_id": {"type": "string", "description": "Optional node id to scope the document"},
                    },
                    "required": ["file_key"],
                },
            },
            {
                "name": "get_variables",
                "description": "Get variable collections for a Figma file (colors, text, spacing tokens).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string"},
                    },
                    "required": ["file_key"],
                },
            },
            {
                "name": "get_styles",
                "description": "Get published styles for a Figma file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string"},
                    },
                    "required": ["file_key"],
                },
            },
            {
                "name": "get_components",
                "description": "Get components and component sets for a Figma file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string"},
                    },
                    "required": ["file_key"],
                },
            },
            {
                "name": "get_design_tokens",
                "description": "Extract design tokens summary: colors, typography, spacing from variables and styles.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string"},
                    },
                    "required": ["file_key"],
                },
            },
        ]
    }


def _extract_design_tokens(variables: dict[str, Any], styles: dict[str, Any]) -> dict[str, Any]:
    tokens: dict[str, Any] = {"colors": [], "typography": [], "spacing": [], "raw": {}}
    raw_vars = variables.get("variables") or {}
    for var_id, var in raw_vars.items():
        if not isinstance(var, dict):
            continue
        name = var.get("name", var_id)
        resolved_type = var.get("resolvedType", "")
        values = var.get("valuesByMode", {})
        sample = next(iter(values.values())) if values else None
        if resolved_type == "COLOR" and sample:
            tokens["colors"].append({"name": name, "value": sample})
        elif resolved_type == "FLOAT" and sample:
            tokens["spacing"].append({"name": name, "value": sample})
        elif resolved_type == "STRING" and sample:
            tokens["typography"].append({"name": name, "value": sample})
    for style in (styles.get("meta", {}).get("styles") or []):
        tokens["typography"].append({"name": style.get("name"), "type": style.get("styleType")})
    tokens["raw"]["variable_count"] = len(raw_vars)
    tokens["raw"]["style_count"] = len(styles.get("meta", {}).get("styles", []))
    return tokens


def handle_tool_call(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    arguments = params.get("arguments", {})
    file_key = arguments.get("file_key", "")
    if not file_key:
        return {"content": [{"type": "text", "text": "file_key is required"}]}

    if name == "get_file":
        node = arguments.get("node_id")
        path = f"/files/{file_key}" + (f"?node-id={node}" if node else "")
        result = _figma_request(path)
    elif name == "get_variables":
        result = _figma_request(f"/files/{file_key}/variables/local")
    elif name == "get_styles":
        result = _figma_request(f"/files/{file_key}/styles")
    elif name == "get_components":
        result = _figma_request(f"/files/{file_key}/components")
    elif name == "get_design_tokens":
        variables = _figma_request(f"/files/{file_key}/variables/local")
        styles = _figma_request(f"/files/{file_key}/styles")
        if "error" in variables:
            result = variables
        elif "error" in styles:
            result = styles
        else:
            result = _extract_design_tokens(variables, styles)
    else:
        return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}]}

    text = json.dumps(result, ensure_ascii=False, indent=2)
    # MCP content must not be huge; cap at ~100K chars to avoid breaking transport.
    if len(text) > 100_000:
        text = text[:100_000] + "\n\n[truncated]"
    return {"content": [{"type": "text", "text": text}]}


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
        params = message.get("params", {})

        if method == "initialize":
            result = handle_initialize(params)
        elif method == "tools/list":
            result = handle_tools_list(params)
        elif method == "tools/call":
            result = handle_tool_call(params)
        else:
            result = {"error": f"Method not supported: {method}"}

        response = {"jsonrpc": "2.0", "id": msg_id, "result": result}
        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
