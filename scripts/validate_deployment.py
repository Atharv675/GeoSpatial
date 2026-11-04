#!/usr/bin/env python3
"""
HTTP validation for GeoSentinel deployment (Phase 8).

Usage:
  python scripts/validate_deployment.py
  python scripts/validate_deployment.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def _get(url: str, timeout: float = 30.0) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {"detail": body[:200]}
        return exc.code, data


def validate(base_url: str, frontend_url: str | None) -> int:
    api = base_url.rstrip("/") + "/api/v1"
    failures: list[str] = []

    checks: list[tuple[str, str, callable]] = [
        ("health", f"{api}/health", lambda d: d.get("status") == "ok"),
        ("ready", f"{api}/ready", lambda d: d.get("status") in ("ready", "degraded")),
        ("aois", f"{api}/aois", lambda d: d.get("count", 0) >= 1),
        (
            "explainability_status",
            f"{api}/explainability/status",
            lambda d: d.get("has_run") is True,
        ),
        (
            "manifest_levant",
            f"{api}/explainability/aoi-levant/manifest",
            lambda d: len(d.get("artifacts", [])) >= 1,
        ),
        ("alerts_status", f"{api}/alerts/status", lambda d: "has_run" in d),
        (
            "osint_correlations",
            f"{api}/osint/correlations/aoi-levant",
            lambda d: d.get("count", 0) >= 0,
        ),
    ]

    print(f"Validating API at {api}\n")
    for name, url, predicate in checks:
        status, data = _get(url)
        ok = status == 200 and predicate(data)
        symbol = "OK" if ok else "FAIL"
        print(f"  [{symbol}] {name} ({status})")
        if not ok:
            failures.append(f"{name}: HTTP {status} — {data}")
        elif name == "manifest_levant":
            print(f"       artifacts={len(data.get('artifacts', []))} run={data.get('run_id')}")

    if frontend_url:
        fe = frontend_url.rstrip("/") + "/"
        try:
            req = urllib.request.Request(fe, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read(500).decode("utf-8", errors="replace")
                ok = resp.status == 200 and ("GeoSentinel" in html or "root" in html)
            print(f"  [{'OK' if ok else 'FAIL'}] frontend ({resp.status})")
            if not ok:
                failures.append("frontend: unexpected response")
        except urllib.error.URLError as exc:
            print(f"  [FAIL] frontend — {exc}")
            failures.append(f"frontend: {exc}")

    print()
    if failures:
        print("Validation failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All checks passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate GeoSentinel deployment")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API origin (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--frontend-url",
        default="http://localhost:5173",
        help="Frontend origin (default: http://localhost:5173)",
    )
    parser.add_argument("--skip-frontend", action="store_true")
    args = parser.parse_args()
    return validate(
        args.base_url,
        None if args.skip_frontend else args.frontend_url,
    )


if __name__ == "__main__":
    sys.exit(main())
