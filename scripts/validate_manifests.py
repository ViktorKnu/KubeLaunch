"""Validate YAML files that are part of the declarative platform."""

from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_ROOTS = (REPOSITORY_ROOT / "platform", REPOSITORY_ROOT / "apps")


def manifest_files() -> list[Path]:
    """Return platform YAML files in stable path order."""
    return sorted(
        path
        for root in MANIFEST_ROOTS
        for pattern in ("*.yaml", "*.yml")
        for path in root.rglob(pattern)
    )


def validate_manifest(path: Path) -> int:
    """Validate all YAML documents in a file and return their count."""
    documents = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
    if not documents or all(document is None for document in documents):
        raise ValueError(f"{path.relative_to(REPOSITORY_ROOT)} is empty")

    for document in documents:
        if not isinstance(document, dict):
            raise ValueError(
                f"{path.relative_to(REPOSITORY_ROOT)} is not a YAML object"
            )
        if not document.get("apiVersion") or not document.get("kind"):
            raise ValueError(
                f"{path.relative_to(REPOSITORY_ROOT)} needs apiVersion and kind"
            )
    return len(documents)


def main() -> None:
    files = manifest_files()
    document_count = sum(validate_manifest(path) for path in files)
    print(f"Validated {document_count} YAML documents in {len(files)} files.")


if __name__ == "__main__":
    main()
