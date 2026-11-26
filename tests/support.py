import shutil
import uuid
from pathlib import Path

from console.collector import UPLOADS, set_submission

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def use_fixture(name: str) -> Path:
    source = FIXTURES / name
    target = UPLOADS / f"fixture-{name}-{uuid.uuid4().hex}"
    shutil.copytree(source, target)
    set_submission(target)
    return target
