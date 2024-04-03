import importlib
import logging
import sys
from pathlib import Path
from typing import Final

from invoke.collection import Collection

from tasks import standard

logging.basicConfig(level=logging.INFO)

TASKS_ROOT: Final = Path(__file__).parent.absolute()
PROJECT_ROOT: Final = TASKS_ROOT.parent
DEPLOY_ROOT: Final = PROJECT_ROOT / "deploy"
TESTS_ROOT: Final = PROJECT_ROOT / "tests"
PREFECT_FLOWS_ROOT: Final = PROJECT_ROOT / "prefect-flows"

SECRETS_REGION: Final = "us-east-1"

sys.path.insert(0, str(PROJECT_ROOT))

ns = Collection.from_module(standard)
for entry in TASKS_ROOT.iterdir():
    fn = entry.name

    if not entry.is_file() or not fn.endswith(".py") or fn.startswith("_") or fn == "standard.py":
        continue  # Not a collection of tasks.

    mod_name = "tasks." + fn[:-3]
    try:
        mod = importlib.import_module(name=mod_name)
        ns.add_collection(Collection.from_module(mod, name=fn[:-3]))
    except ImportError as e:
        logging.warning("Failed to load collection %s because: %s", mod_name, e)
