import os
import pathlib

pytest_plugins = "pytester"

# subprocess pytester runs need coverage started from this config
project_root = pathlib.Path(__file__).parent.parent
os.environ["COVERAGE_PROCESS_START"] = str(project_root / "pyproject.toml")
os.environ["COVERAGE_FILE"] = str(project_root / ".coverage")
