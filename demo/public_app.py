"""Zero-secret, fixture-only entrypoint for the R1A public research demo."""

import sys
from importlib import import_module
from pathlib import Path

# Streamlit Community Cloud launches a nested entrypoint with ``demo/`` at sys.path[0].
# Add the immutable repository root derived from this file so absolute project imports resolve.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
project_root_text = str(PROJECT_ROOT)
if project_root_text not in sys.path:
    sys.path.insert(0, project_root_text)

render = import_module("demo.app").render

render(public_release=True)
