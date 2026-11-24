"""Writing Editor MCP: editorial guidance and revision review for research and technical prose."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("writing-editor-mcp")
except PackageNotFoundError:  # imported from a source tree that is not installed
    __version__ = "0.0.0"
