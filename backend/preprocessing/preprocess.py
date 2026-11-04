"""
Preprocessing orchestrator — deterministic raster pipeline.

Per item: validate → reproject → clip → [cloud mask S2] → normalize → tile
Per AOI S1 pair: SAR temporal difference
Per AOI+collection: xarray temporal stack
"""

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.ingestion.aoi import get_aoi
from backend.preprocessing.clip import clip_raster_to_geometry
from backend.preprocessing.mask import apply_cloud_mask_raster
from backend.preprocessing.models import (
    ItemPreprocessResult,
    PreprocessResult,
    PreprocessStatus,
    SarDiffResult,
    StackResult,
)
from backend.preprocessing.normalize import normalize_raster
from backend.preprocessing.reproject import reproject_raster
from backend.preprocessing.sar_diff import compute_sar_disturbance
from backend.preprocessing.stack import build_temporal_stack
from backend.preprocessing.tile import generate_tiles
from backend.preprocessing.validate import validate_raster
from backend.shared.config import get_settings
from backend.shared.exceptions import ValidationError
from backend.shared.logging import get_logger
from backend.storage.registry import MetadataRegistry

logger = get_logger(__name__)

STATE_FILENAME = "preprocess_state.json"
COLLECTION_S1 = "sentinel-1-grd"
COLLECTION_S2 = "sentinel-2-l2a"


def _state_path() -> Path:
    return get_settings().resolve_data_path("processed") / STATE_FILENAME


def _load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {"runs": []}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _save_state(state: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _item_output_dir(collection: str, aoi_id: str, item_id: str) -> Path:
    rel = f"processed/{collection}/{aoi_id}/{item_id}"
    return get_settings().resolve_data_path(rel)


def _rel_path(path: Path) -> str:
    return str(path.relative_to(get_settings().data_root)).replace("\\", "/")


def preprocess_registry_item(item: dict[str, Any]) -> ItemPreprocessResult:
    """Run full preprocessing chain for one STAC registry item."""
    item_id = item["id"]
    collection = item.get("collection", item.get("properties", {}).get("gs:collection", ""))
    props = item.get("properties", {})
    aoi_id = props.get("gs:aoi_id", "")
    platform = props.get("platform", "")

    try:
        reg = MetadataRegistry()
        src_path = reg.item_asset_path(item_id, "data")
        validate_raster(src_path)

        aoi = get_aoi(aoi_id)
        if not aoi:
            raise ValidationError(f"Unknown AOI: {aoi_id}")

        out_dir = _item_output_dir(collection, aoi_id, item_id)
        out_dir.mkdir(parents=True, exist_ok=True)

        reprojected = out_dir / "reprojected.tif"
        clipped = out_dir / "clipped.tif"
        masked = out_dir / "masked.tif"
        normalized = out_dir / "normalized.tif"
        mask_file = out_dir / "cloud_mask.tif"
        tiles_dir = out_dir / "tiles"

        if normalized.exists():
            try:
                validate_raster(normalized)
                return ItemPreprocessResult(
                    item_id=item_id,
                    status=PreprocessStatus.SKIPPED,
                    message="Already processed",
                    outputs={"normalized": _rel_path(normalized)},
                )
            except ValidationError:
                pass

        reproject_raster(src_path, reprojected)
        clip_raster_to_geometry(reprojected, clipped, aoi.geometry)

        if platform == "sentinel-2" or collection == COLLECTION_S2:
            cloud_cover = float(props.get("eo:cloud_cover", 0))
            apply_cloud_mask_raster(clipped, masked, cloud_cover, mask_file)
            normalize_raster(masked, normalized)
        else:
            normalize_raster(clipped, normalized)

        tile_names = generate_tiles(normalized, tiles_dir)

        outputs = {
            "reprojected": _rel_path(reprojected),
            "clipped": _rel_path(clipped),
            "normalized": _rel_path(normalized),
            "tiles_dir": _rel_path(tiles_dir),
            "tile_count": str(len(tile_names)),
        }
        if masked.exists():
            outputs["masked"] = _rel_path(masked)
        if mask_file.exists():
            outputs["cloud_mask"] = _rel_path(mask_file)

        return ItemPreprocessResult(
            item_id=item_id,
            status=PreprocessStatus.OK,
            outputs=outputs,
        )
    except Exception as exc:
        logger.error("preprocess_item_failed", item_id=item_id, error=type(exc).__name__)
        return ItemPreprocessResult(
            item_id=item_id,
            status=PreprocessStatus.FAILED,
            message=str(exc)[:500],
        )


def _run_sar_differencing(
    item_results: list[ItemPreprocessResult],
    registry_items: list[dict[str, Any]],
) -> list[SarDiffResult]:
    """Compute SAR disturbance for consecutive normalized pairs per AOI."""
    settings = get_settings()
    by_aoi: dict[str, list[tuple[datetime, str, Path]]] = defaultdict(list)
    item_index = {i["id"]: i for i in registry_items}

    for result in item_results:
        if result.status not in (PreprocessStatus.OK, PreprocessStatus.SKIPPED):
            continue
        norm_rel = result.outputs.get("normalized")
        if not norm_rel:
            continue
        item = item_index.get(result.item_id)
        if not item:
            continue
        coll = item.get("collection", "")
        if coll != COLLECTION_S1:
            continue
        aoi_id = item["properties"].get("gs:aoi_id", "")
        dt_str = item["properties"].get("datetime", "")
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        by_aoi[aoi_id].append((dt, result.item_id, settings.resolve_data_path(norm_rel)))

    diff_results: list[SarDiffResult] = []
    for aoi_id, entries in by_aoi.items():
        entries.sort(key=lambda x: x[0])
        for i in range(1, len(entries)):
            prev_dt, prev_id, prev_path = entries[i - 1]
            curr_dt, curr_id, curr_path = entries[i]
            out_rel = f"processed/{COLLECTION_S1}/{aoi_id}/disturbance/{prev_id}_to_{curr_id}_diff.tif"
            out_path = settings.resolve_data_path(out_rel)
            try:
                compute_sar_disturbance(prev_path, curr_path, out_path)
                diff_results.append(
                    SarDiffResult(
                        aoi_id=aoi_id,
                        previous_item_id=prev_id,
                        current_item_id=curr_id,
                        status=PreprocessStatus.OK,
                        output_path=out_rel,
                    )
                )
            except Exception as exc:
                diff_results.append(
                    SarDiffResult(
                        aoi_id=aoi_id,
                        previous_item_id=prev_id,
                        current_item_id=curr_id,
                        status=PreprocessStatus.FAILED,
                        message=str(exc)[:500],
                    )
                )
    return diff_results


def _run_temporal_stacks(
    item_results: list[ItemPreprocessResult],
    registry_items: list[dict[str, Any]],
) -> list[StackResult]:
    """Build xarray NetCDF stacks per AOI and collection."""
    settings = get_settings()
    grouped: dict[tuple[str, str], list[tuple[str, Path]]] = defaultdict(list)
    item_index = {i["id"]: i for i in registry_items}

    for result in item_results:
        if result.status not in (PreprocessStatus.OK, PreprocessStatus.SKIPPED):
            continue
        norm_rel = result.outputs.get("normalized")
        if not norm_rel:
            continue
        item = item_index.get(result.item_id)
        if not item:
            continue
        coll = item.get("collection", item.get("properties", {}).get("gs:collection", ""))
        aoi_id = item["properties"].get("gs:aoi_id", "")
        dt_str = item["properties"].get("datetime", "")
        grouped[(aoi_id, coll)].append((dt_str, settings.resolve_data_path(norm_rel)))

    stack_results: list[StackResult] = []
    for (aoi_id, collection), entries in grouped.items():
        if len(entries) < 2:
            stack_results.append(
                StackResult(
                    aoi_id=aoi_id,
                    collection=collection,
                    status=PreprocessStatus.SKIPPED,
                    message="Need at least 2 time steps",
                    time_steps=len(entries),
                )
            )
            continue
        entries.sort(key=lambda x: x[0])
        out_rel = f"processed/stacks/{aoi_id}/{collection}_temporal.nc"
        out_path = settings.resolve_data_path(out_rel)
        try:
            build_temporal_stack(entries, out_path)
            stack_results.append(
                StackResult(
                    aoi_id=aoi_id,
                    collection=collection,
                    status=PreprocessStatus.OK,
                    output_path=out_rel,
                    time_steps=len(entries),
                )
            )
        except Exception as exc:
            stack_results.append(
                StackResult(
                    aoi_id=aoi_id,
                    collection=collection,
                    status=PreprocessStatus.FAILED,
                    message=str(exc)[:500],
                    time_steps=len(entries),
                )
            )
    return stack_results


def run_preprocessing(run_id: str | None = None) -> PreprocessResult:
    """Run preprocessing for all registry items."""
    started = datetime.now(timezone.utc)
    run_id = run_id or started.strftime("%Y%m%dT%H%M%SZ")

    reg = MetadataRegistry()
    items = reg.list_items()
    if not items:
        logger.warning("preprocess_no_items")
        completed = datetime.now(timezone.utc)
        return PreprocessResult(
            run_id=run_id,
            started_at=started,
            completed_at=completed,
            items_total=0,
            items_ok=0,
            items_failed=0,
            item_results=[],
        )

    logger.info("preprocess_start", run_id=run_id, items=len(items))
    item_results = [preprocess_registry_item(item) for item in items]
    sar_diffs = _run_sar_differencing(item_results, items)
    stacks = _run_temporal_stacks(item_results, items)

    completed = datetime.now(timezone.utc)
    ok = {PreprocessStatus.OK, PreprocessStatus.SKIPPED}
    items_ok = sum(1 for r in item_results if r.status in ok)
    items_failed = sum(1 for r in item_results if r.status == PreprocessStatus.FAILED)

    result = PreprocessResult(
        run_id=run_id,
        started_at=started,
        completed_at=completed,
        items_total=len(items),
        items_ok=items_ok,
        items_failed=items_failed,
        item_results=item_results,
        sar_diffs=sar_diffs,
        stacks=stacks,
        metadata={"target_crs_epsg": get_settings().target_crs_epsg},
    )

    state = _load_state()
    state.setdefault("runs", []).append(
        {
            "run_id": run_id,
            "items_ok": items_ok,
            "items_failed": items_failed,
            "sar_diffs": len(sar_diffs),
            "stacks": len(stacks),
        }
    )
    state["last_run"] = result.model_dump(mode="json")
    _save_state(state)

    logger.info(
        "preprocess_complete",
        run_id=run_id,
        ok=items_ok,
        failed=items_failed,
        sar_diffs=len(sar_diffs),
    )
    return result
