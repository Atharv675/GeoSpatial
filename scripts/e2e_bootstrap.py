#!/usr/bin/env python3
"""
End-to-end demo bootstrap: seed curated data, OSINT demo, run full pipeline.

Writes data/.e2e_bootstrap_complete when successful. Set FORCE_E2E_BOOTSTRAP=1 to re-run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = ROOT / "data" / ".e2e_bootstrap_complete"


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(ROOT))
    env.setdefault("DATA_ROOT", str(ROOT / "data"))
    env.setdefault("REGISTRY_PATH", str(ROOT / "data" / "registry"))
    return env


def _run_script(name: str) -> None:
    path = ROOT / "scripts" / name
    print(f"\n==> {name}")
    subprocess.run([sys.executable, str(path)], check=True, cwd=ROOT, env=_env())


def run_e2e_bootstrap(*, force: bool = False) -> int:
    """Seed data and run pipeline. Returns process exit code."""
    if MARKER.exists() and not force and os.getenv("FORCE_E2E_BOOTSTRAP", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        print(f"Bootstrap already complete ({MARKER}). Set FORCE_E2E_BOOTSTRAP=1 to re-run.")
        return 0

    print("GeoSentinel E2E bootstrap")
    try:
        _run_script("init_registry.py")
        _run_script("seed_curated_data.py")
        _run_script("seed_osint_demo.py")
    except subprocess.CalledProcessError as exc:
        print(f"Seed step failed: {exc}", file=sys.stderr)
        return exc.returncode or 1

    print("\n==> backend.pipeline.run_pipeline")
    from backend.pipeline.run_pipeline import run_pipeline

    code = run_pipeline()
    if code != 0:
        print(f"Pipeline exited with code {code}", file=sys.stderr)
        return code

    manifest = ROOT / "data" / "explainability" / "aoi-levant"
    if manifest.exists():
        runs = sorted([d for d in manifest.iterdir() if d.is_dir()])
        run_id = runs[-1].name if runs else "unknown"
    else:
        run_id = "unknown"

    MARKER.write_text(
        json.dumps(
            {
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "pipeline_exit_code": code,
                "sample_run_id": run_id,
                "aoi_with_explainability": "aoi-levant",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nBootstrap complete. Marker: {MARKER}")
    return 0


def main() -> int:
    force = "--force" in sys.argv
    return run_e2e_bootstrap(force=force)


if __name__ == "__main__":
    sys.exit(main())
