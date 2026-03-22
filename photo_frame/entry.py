"""
Console-script entry point (used by pyproject.toml).

The application modules (config, scanner, layout, …) use flat imports,
so we add the package directory to sys.path before importing main.
"""
import os
import sys


def main() -> None:
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)
    from main import main as _main  # noqa: PLC0415
    _main()
