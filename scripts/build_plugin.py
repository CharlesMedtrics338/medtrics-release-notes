#!/usr/bin/env python3
"""
build_plugin.py — bundle the plugin directory into a versioned .plugin file.

Reads the version from .claude-plugin/plugin.json and produces
medtrics-release-notes-<version>.plugin in the repo root, excluding:

  - .git, .gitignore, .gitattributes
  - .mypy_cache, .ruff_cache, .pytest_cache, __pycache__
  - .DS_Store, *.pyc
  - tests/                       (not shipped in the plugin)
  - requirements*.txt            (dev-side; ip_guard.py is stdlib-only)
  - CONTRIBUTING.md              (dev-side)
  - any *.plugin (previous build outputs)

Usage:
    python3 scripts/build_plugin.py
    python3 scripts/build_plugin.py --output-dir /path/to/out
    python3 scripts/build_plugin.py --include-tests   # for QA bundles only
"""

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path


EXCLUDE_DIRS_DEFAULT = {
    ".git", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "__pycache__", "tests",
}
EXCLUDE_DIRS_INCLUDE_TESTS = {
    ".git", ".mypy_cache", ".ruff_cache", ".pytest_cache", "__pycache__",
}
EXCLUDE_FILES = {
    ".DS_Store", ".gitignore", ".gitattributes",
    "requirements.txt", "requirements-dev.txt", "CONTRIBUTING.md",
}
EXCLUDE_SUFFIXES = {".pyc", ".plugin"}


def repo_root() -> Path:
    """The plugin root. This script lives at <root>/scripts/build_plugin.py."""
    return Path(__file__).resolve().parent.parent


def read_version(root: Path) -> str:
    manifest = root / ".claude-plugin" / "plugin.json"
    if not manifest.exists():
        sys.exit(f"ERROR: manifest not found at {manifest}")
    return json.loads(manifest.read_text())["version"]


def _write_dir_entry(zf: zipfile.ZipFile, arcname: str) -> None:
    """Write an explicit directory entry into the zip.

    Some plugin validators (including the Cowork plugin loader) require
    explicit directory records, not just inferred-from-file-paths directories.
    The entry is a 0-byte record with the directory bit set in external_attr.
    """
    if not arcname.endswith("/"):
        arcname = arcname + "/"
    info = zipfile.ZipInfo(arcname)
    # 0o40755 = directory mode with rwxr-xr-x. Bit shift into the high 16
    # bits of external_attr per the zip spec.
    info.external_attr = (0o40755 << 16) | 0x10  # 0x10 = MS-DOS directory flag
    zf.writestr(info, b"")


def build(root: Path, out_dir: Path, include_tests: bool = False) -> Path:
    version = read_version(root)
    out_path = out_dir / f"medtrics-release-notes-{version}.plugin"
    excludes = EXCLUDE_DIRS_INCLUDE_TESTS if include_tests else EXCLUDE_DIRS_DEFAULT

    files_added = 0
    dirs_added = 0
    written_dirs: set[str] = set()

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for current_root, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in excludes)
            rel_root = Path(current_root).relative_to(root)

            # Write a directory entry for every subdir (skip the plugin root).
            if str(rel_root) != ".":
                arc = rel_root.as_posix() + "/"
                if arc not in written_dirs:
                    _write_dir_entry(zf, arc)
                    written_dirs.add(arc)
                    dirs_added += 1

            for f in sorted(files):
                if f in EXCLUDE_FILES:
                    continue
                if any(f.endswith(suffix) for suffix in EXCLUDE_SUFFIXES):
                    continue
                full = Path(current_root) / f
                rel = full.relative_to(root)
                zf.write(full, rel.as_posix())
                files_added += 1

    size = out_path.stat().st_size

    # Post-build self-check. The Cowork plugin loader rejects a bundle that
    # is missing either the explicit .claude-plugin/ directory entry or the
    # plugin.json file inside it. Catch the regression here, not at install.
    _verify_bundle(out_path)

    print(f"wrote {out_path}")
    print(f"  version: {version}")
    print(f"  dirs:    {dirs_added}")
    print(f"  files:   {files_added}")
    print(f"  size:    {size:,} bytes")
    return out_path


def _verify_bundle(plugin_path: Path) -> None:
    """Raise SystemExit if the freshly-built .plugin is missing required entries."""
    required_dir = ".claude-plugin/"
    required_file = ".claude-plugin/plugin.json"
    with zipfile.ZipFile(plugin_path) as zf:
        names = set(zf.namelist())
        # plugin.json must be present and parseable
        if required_file not in names:
            sys.exit(f"BUILD FAILED: bundle is missing {required_file}")
        # explicit directory entry must be present (some validators require it)
        if required_dir not in names:
            sys.exit(f"BUILD FAILED: bundle is missing explicit dir entry {required_dir}")
        # plugin.json must contain version + name + description
        try:
            manifest = json.loads(zf.read(required_file).decode("utf-8"))
        except json.JSONDecodeError as e:
            sys.exit(f"BUILD FAILED: {required_file} is not valid JSON: {e}")
        for key in ("name", "version", "description"):
            if key not in manifest:
                sys.exit(f"BUILD FAILED: {required_file} missing required key: {key}")
        # description length cap (matches the loader's strict cap)
        if len(manifest["description"]) > 256:
            sys.exit(
                f"BUILD FAILED: plugin.json description is "
                f"{len(manifest['description'])} chars; cap is 256."
            )


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--output-dir", default=None,
                    help="Where to write the .plugin file (default: repo root)")
    ap.add_argument("--include-tests", action="store_true",
                    help="Include tests/ in the bundle (for QA validation builds)")
    args = ap.parse_args()

    root = repo_root()
    out_dir = Path(args.output_dir) if args.output_dir else root
    out_dir.mkdir(parents=True, exist_ok=True)

    build(root, out_dir, include_tests=args.include_tests)
    return 0


if __name__ == "__main__":
    sys.exit(main())
