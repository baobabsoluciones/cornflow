try:
    from ._generated_version import __version__
except ImportError:
    __version__ = "dev"
