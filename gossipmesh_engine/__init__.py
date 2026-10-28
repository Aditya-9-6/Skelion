"""GossipMesh package wrapper for Skelion integration.
Exports the FastAPI app as `gossipmesh_app`.
"""

from .api.main import app as gossipmesh_app

__all__ = ["gossipmesh_app"]
