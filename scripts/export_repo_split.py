from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "proposals" / "repo_split_manifest.json"


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def expand_patterns(root: Path, patterns: Iterable[str]) -> set[Path]:
    matched: set[Path] = set()
    for pattern in patterns:
        for candidate in root.glob(pattern):
            if candidate.is_dir():
                matched.update(
                    path
                    for path in candidate.rglob("*")
                    if path.is_file() and not should_skip_file(path)
                )
            else:
                if not should_skip_file(candidate):
                    matched.add(candidate)
    return matched


def should_skip_file(path: Path) -> bool:
    if any(part == "__pycache__" for part in path.parts):
        return True
    if path.suffix in {".pyc", ".pyo", ".pyd"}:
        return True
    return False


def relative_paths(paths: Iterable[Path], root: Path) -> set[Path]:
    return {path.relative_to(root) for path in paths}


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def export_repo(repo_name: str, config: dict, global_exclude: set[Path], output_root: Path) -> int:
    include = relative_paths(expand_patterns(REPO_ROOT, config.get("include", [])), REPO_ROOT)
    exclude = relative_paths(expand_patterns(REPO_ROOT, config.get("exclude", [])), REPO_ROOT)
    selected = sorted(path for path in include if path not in exclude and path not in global_exclude)

    target_root = output_root / repo_name
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True, exist_ok=True)

    for rel_path in selected:
        copy_file(REPO_ROOT / rel_path, target_root / rel_path)

    summary = {
        "repo": repo_name,
        "files_exported": len(selected)
    }
    (target_root / ".vrl-export.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8"
    )
    return len(selected)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export the VRL transitional monorepo into spec/sdk/registry/server repo folders."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to repo split manifest JSON."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPO_ROOT.parent / "vrl-split",
        help="Directory where the split repos will be written."
    )
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    global_exclude = relative_paths(
        expand_patterns(REPO_ROOT, manifest.get("global_exclude", [])),
        REPO_ROOT
    )

    exported: dict[str, int] = {}
    for repo_name, config in manifest.items():
        if repo_name == "global_exclude":
            continue
        exported[repo_name] = export_repo(repo_name, config, global_exclude, args.output_root)

    print(json.dumps({"output_root": str(args.output_root), "exported": exported}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
