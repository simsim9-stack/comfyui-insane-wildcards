"""
Insane Wildcards - A powerful hybrid wildcard processing node for ComfyUI.

Combines wildcard file reading, dynamic prompt generation,
and multi-line batch output into a single versatile node.
"""

import os
import threading

from .nodes.insane_wildcards_node import InsaneWildcards
from .wildcard_loader import wildcard_load, wildcards_path

# ---------------------------------------------------------------------------
# Node registration
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS = {
    "InsaneWildcards": InsaneWildcards,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "InsaneWildcards": "Insane Wildcards",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

# ---------------------------------------------------------------------------
# API endpoint for frontend wildcard list
# ---------------------------------------------------------------------------
try:
    from server import PromptServer
    from aiohttp import web

    @PromptServer.instance.routes.get("/insanewildcards/wildcards/list")
    async def list_wildcards(request):
        from .wildcard_loader import get_wildcard_list

        wildcards = get_wildcard_list()
        return web.json_response({"data": wildcards, "count": len(wildcards)})

except Exception:
    pass

# ---------------------------------------------------------------------------
# Auto-create wildcards directory with example on first load
# ---------------------------------------------------------------------------
if not os.path.exists(wildcards_path):
    os.makedirs(wildcards_path, exist_ok=True)

example_path = os.path.join(wildcards_path, "example.txt")
if not os.path.exists(example_path):
    with open(example_path, "w", encoding="utf-8") as f:
        f.write(
            "blue\nred\nyellow\ngreen\nbrown\npink\npurple\norange\nblack\nwhite"
        )

# ---------------------------------------------------------------------------
# Load wildcards in background thread
# ---------------------------------------------------------------------------
threading.Thread(target=wildcard_load, daemon=True).start()

# ---------------------------------------------------------------------------
# Frontend JS directory
# ---------------------------------------------------------------------------
WEB_DIRECTORY = "./js"
