"""GossipMesh package wrapper for Skelion integration.
Exports the FastAPI app as `gossipmesh_app`.
"""

try:
    from .api.main import app as gossipmesh_app
except ImportError:
    gossipmesh_app = None

__all__ = ["gossipmesh_app"]
