"""
Read-only client for Conway's Depot, the source for what a project is. Scope Manager keys its WBS
by Depot project id and lists Depot projects in its picker, so a project can get a WBS before it
has any scope items. Tolerant: None when the Depot can't be reached.
"""

import os

import httpx

DEPOT_API_URL = os.environ.get("DEPOT_API_URL", "http://localhost:8090").rstrip("/")


def fetch_projects() -> list[dict] | None:
    try:
        r = httpx.get(f"{DEPOT_API_URL}/api/projects", timeout=3.0)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError:
        return None
