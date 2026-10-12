"""M7 synthetic PDFs and truth files must be reproducible."""

import hashlib
from pathlib import Path

from scripts.make_m7_docs import generate_all


def _artifact_hashes(root: Path) -> dict[str, str]:
    files = sorted([*root.joinpath("inputs").glob("*.pdf"), *root.joinpath("truth").glob("*.json"), *root.joinpath("assets").glob("*.png")])
    return {f"{path.parent.name}/{path.name}": hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


def test_m7_generator_is_deterministic(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    generate_all(first)
    generate_all(second)
    assert _artifact_hashes(first) == _artifact_hashes(second)
