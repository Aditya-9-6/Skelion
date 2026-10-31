# skelion-python package export
try:
    from skelion.skelion import SkelionMiddleware
except ImportError:
    try:
        from .skelion import SkelionMiddleware
    except ImportError:
        from src.sdk.python.skelion import SkelionMiddleware

__version__ = "1.0.0"
__all__ = ["SkelionMiddleware"]
