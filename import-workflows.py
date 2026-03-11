#!/usr/bin/env python3
"""
Import all n8n workflow JSON files into a running n8n instance.
Run this after the stack is up: python3 import-workflows.py
"""
import os
import json
import httpx
import sys

N8N_URL = os.environ.get("N8N_URL", "http://localhost:5678")
N8N_USER = os.environ.get("N8N_BASIC_AUTH_USER", "admin")
N8N_PASS = os.environ.get("N8N_BASIC_AUTH_PASSWORD", "changeme")

WORKFLOWS_DIR = os.path.join(os.path.dirname(__file__), "n8n-workflows")


def import_workflows():
    auth = (N8N_USER, N8N_PASS)
    files = [f for f in os.listdir(WORKFLOWS_DIR) if f.endswith(".json")]
    if not files:
        print("No workflow JSON files found.")
        return

    for filename in sorted(files):
        path = os.path.join(WORKFLOWS_DIR, filename)
        with open(path) as f:
            workflow = json.load(f)

        workflow.pop("id", None)

        try:
            resp = httpx.post(
                f"{N8N_URL}/api/v1/workflows",
                json=workflow,
                auth=auth,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                print(f"  Imported: {filename} -> id={data.get('id')}")
            else:
                print(f"  Failed:   {filename} -> {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            print(f"  Error:    {filename} -> {e}")


if __name__ == "__main__":
    print(f"Importing n8n workflows from {WORKFLOWS_DIR}")
    print(f"Target: {N8N_URL}")
    import_workflows()
    print("Done.")
