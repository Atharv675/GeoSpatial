"""
Feature engineering and anomaly analysis orchestrator (Phase 4).

Computes NDVI, NDWI, NBR, temporal differences, integrates SAR disturbance,
and produces explainable rule-based anomaly scores.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from backend.ingestion.aoi import get_aoi
from backend.processing.bands import (
    AcquisitionGroup,
    group_optical_acquisitions,
    normalized_path_for_item,
)
from backend.processing.indices import compute_nbr, compute_ndvi, compute_ndwi
from backend.processing.io import read_band, raster_mean_valid, write_feature_raster
from backend.processing.models import AnalysisResult, AnalysisStatus, AOIAnomalyReport, FeatureResult
from backend.processing.sar_features import register_sar_disturbance
from backend.processing.scoring import (
    SignalInput,
    build_composite_score_raster,
    score_aoi_anomaly,
)
from backend.processing.temporal import temporal_difference
from backend.shared.config import get_settings
from backend.shared.logging import get_logger
from backend.storage.registry import MetadataRegistry

logger = get_logger(__name__)

STATE_FILENAME = "analysis_state.json"
COLLECTION_S2 = "sentinel-2-l2a"
COLLECTION_S1 = "sentinel-1-grd"


def _state_path() -> Path:
    return get_settings().resolve_data_path("processed") / STATE_FILENAME


def _features_root(aoi_id: str) -> Path:
    return get_settings().resolve_data_path(f"processed/features/{aoi_id}")


def _anomalies_root(aoi_id: str) -> Path:
    return get_settings().resolve_data_path(f"processed/anomalies/{aoi_id}")


def _rel(path: Path) -> str:
    return str(path.relative_to(get_settings().data_root)).replace("\\", "/")


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


def _compute_indices_for_group(group: AcquisitionGroup) -> list[FeatureResult]:
    """Compute available spectral indices for one acquisition."""
    settings = get_settings()
    results: list[FeatureResult] = []
    out_dir = _features_root(group.aoi_id) / group.date_key

    red_obs = group.band_array("red")
    nir_obs = group.band_array("nir")
    green_obs = group.band_array("green")
    swir_obs = group.band_array("swir")

    # Curated fallback: use red as green proxy when green absent (documented in metadata)
    green_proxy = green_obs or red_obs

    if red_obs and nir_obs:
        try:
            red, profile = read_band(red_obs.normalized_path)
            nir, _ = read_band(nir_obs.normalized_path)
            if red.shape == nir.shape:
                ndvi = compute_ndvi(red, nir)
                out = out_dir / "ndvi.tif"
                write_feature_raster(out, ndvi, profile)
                results.append(
                    FeatureResult(
                        feature="ndvi",
                        aoi_id=group.aoi_id,
                        status=AnalysisStatus.OK,
                        output_path=_rel(out),
                        metadata={"date": group.date_key, "mean": raster_mean_valid(ndvi)},
                    )
                )
        except Exception as exc:
            results.append(
                FeatureResult(
                    feature="ndvi",
                    aoi_id=group.aoi_id,
                    status=AnalysisStatus.FAILED,
                    message=str(exc)[:300],
                )
            )

    if green_proxy and nir_obs:
        try:
            green, profile = read_band(green_proxy.normalized_path)
            nir, _ = read_band(nir_obs.normalized_path)
            if green.shape == nir.shape:
                ndwi = compute_ndwi(green, nir)
                out = out_dir / "ndwi.tif"
                write_feature_raster(out, ndwi, profile)
                results.append(
                    FeatureResult(
                        feature="ndwi",
                        aoi_id=group.aoi_id,
                        status=AnalysisStatus.OK,
                        output_path=_rel(out),
                        metadata={
                            "date": group.date_key,
                            "green_proxy": green_obs is None,
                            "mean": raster_mean_valid(ndwi),
                        },
                    )
                )
        except Exception as exc:
            results.append(
                FeatureResult(
                    feature="ndwi",
                    aoi_id=group.aoi_id,
                    status=AnalysisStatus.FAILED,
                    message=str(exc)[:300],
                )
            )

    if nir_obs and swir_obs:
        try:
            nir, profile = read_band(nir_obs.normalized_path)
            swir, _ = read_band(swir_obs.normalized_path)
            if nir.shape == swir.shape:
                nbr = compute_nbr(nir, swir)
                out = out_dir / "nbr.tif"
                write_feature_raster(out, nbr, profile)
                results.append(
                    FeatureResult(
                        feature="nbr",
                        aoi_id=group.aoi_id,
                        status=AnalysisStatus.OK,
                        output_path=_rel(out),
                        metadata={"date": group.date_key, "mean": raster_mean_valid(nbr)},
                    )
                )
        except Exception as exc:
            results.append(
                FeatureResult(
                    feature="nbr",
                    aoi_id=group.aoi_id,
                    status=AnalysisStatus.FAILED,
                    message=str(exc)[:300],
                )
            )
    elif nir_obs and red_obs:
        # Curated SWIR proxy: B04 as SWIR stand-in for burn demo when SWIR band missing
        try:
            nir, profile = read_band(nir_obs.normalized_path)
            swir_proxy, _ = read_band(red_obs.normalized_path)
            if nir.shape == swir_proxy.shape:
                nbr = compute_nbr(nir, swir_proxy)
                out = out_dir / "nbr.tif"
                write_feature_raster(out, nbr, profile)
                results.append(
                    FeatureResult(
                        feature="nbr",
                        aoi_id=group.aoi_id,
                        status=AnalysisStatus.OK,
                        output_path=_rel(out),
                        metadata={
                            "date": group.date_key,
                            "swir_proxy": True,
                            "mean": raster_mean_valid(nbr),
                        },
                    )
                )
        except Exception as exc:
            results.append(
                FeatureResult(
                    feature="nbr",
                    aoi_id=group.aoi_id,
                    status=AnalysisStatus.FAILED,
                    message=str(exc)[:300],
                )
            )

    if not results:
        results.append(
            FeatureResult(
                feature="indices",
                aoi_id=group.aoi_id,
                status=AnalysisStatus.SKIPPED,
                message="Insufficient bands for NDVI/NDWI/NBR",
            )
        )
    return results


def _temporal_diffs_for_aoi(
    aoi_id: str,
    index_name: str,
    date_paths: list[tuple[str, Path]],
) -> list[FeatureResult]:
    """Compute consecutive temporal differences for an index time series."""
    results: list[FeatureResult] = []
    if len(date_paths) < 2:
        return results

    date_paths.sort(key=lambda x: x[0])
    for i in range(1, len(date_paths)):
        prev_date, prev_path = date_paths[i - 1]
        curr_date, curr_path = date_paths[i]
        out = _features_root(aoi_id) / "temporal" / f"{index_name}_{prev_date}_to_{curr_date}_diff.tif"
        try:
            temporal_difference(prev_path, curr_path, out)
            diff_data, _ = read_band(out)
            results.append(
                FeatureResult(
                    feature=f"temporal_{index_name}",
                    aoi_id=aoi_id,
                    status=AnalysisStatus.OK,
                    output_path=_rel(out),
                    metadata={
                        "previous": prev_date,
                        "current": curr_date,
                        "mean_abs_delta": raster_mean_valid(np.abs(diff_data)),
                    },
                )
            )
        except Exception as exc:
            results.append(
                FeatureResult(
                    feature=f"temporal_{index_name}",
                    aoi_id=aoi_id,
                    status=AnalysisStatus.FAILED,
                    message=str(exc)[:300],
                )
            )
    return results


def _integrate_sar_disturbances() -> list[FeatureResult]:
    """Register SAR disturbance rasters from preprocessing."""
    settings = get_settings()
    results: list[FeatureResult] = []
    sar_root = settings.resolve_data_path(f"processed/{COLLECTION_S1}")
    if not sar_root.exists():
        return results

    for aoi_dir in sar_root.iterdir():
        if not aoi_dir.is_dir():
            continue
        disturbance_dir = aoi_dir / "disturbance"
        if not disturbance_dir.exists():
            continue
        for diff_file in disturbance_dir.glob("*_diff.tif"):
            out = _features_root(aoi_dir.name) / "sar" / diff_file.name
            try:
                register_sar_disturbance(diff_file, out)
                data, _ = read_band(out)
                results.append(
                    FeatureResult(
                        feature="sar_disturbance",
                        aoi_id=aoi_dir.name,
                        status=AnalysisStatus.OK,
                        output_path=_rel(out),
                        metadata={"mean_abs": raster_mean_valid(np.abs(data))},
                    )
                )
            except Exception as exc:
                results.append(
                    FeatureResult(
                        feature="sar_disturbance",
                        aoi_id=aoi_dir.name,
                        status=AnalysisStatus.FAILED,
                        message=str(exc)[:300],
                    )
                )
    return results


def _score_aoi(
    aoi_id: str,
    latest_date: str,
    feature_paths: dict[str, Path],
) -> AOIAnomalyReport:
    """Apply rule-based scoring for one AOI."""
    settings = get_settings()
    evidence: dict[str, str] = {k: _rel(v) for k, v in feature_paths.items()}

    signal_inputs: list[SignalInput] = []
    score_rasters: dict[str, np.ndarray] = {}
    shape = None

    mapping = {
        "temporal_ndvi": ("vegetation_change", settings.anomaly_ndvi_threshold, 0.35),
        "temporal_ndwi": ("water_change", settings.anomaly_ndwi_threshold, 0.25),
        "temporal_nbr": ("burn_anomaly", settings.anomaly_nbr_threshold, 0.20),
        "sar_disturbance": ("surface_disturbance", settings.anomaly_sar_threshold, 0.20),
    }

    for key, path in feature_paths.items():
        if key not in mapping and not key.startswith("temporal_"):
            continue
        name, threshold, weight = mapping.get(
            key,
            ("optical_change", settings.anomaly_temporal_threshold, 0.15),
        )
        if not path.exists():
            continue
        data, _ = read_band(path)
        mean_abs = raster_mean_valid(np.abs(data))
        signal_inputs.append(
            SignalInput(
                name=name,
                weight=weight,
                mean_abs=mean_abs,
                threshold=threshold,
                description=f"Rule: |{key}| mean >= {threshold}",
            )
        )
        score_rasters[name] = data
        shape = data.shape

    report = score_aoi_anomaly(aoi_id, latest_date, signal_inputs, evidence)

    if score_rasters and shape:
        weights = {s.name: s.weight for s in signal_inputs}
        thresholds = {s.name: s.threshold for s in signal_inputs}
        composite = build_composite_score_raster(score_rasters, weights, thresholds)
        comp_path = _anomalies_root(aoi_id) / f"anomaly_score_{latest_date}.tif"
        _, profile = read_band(next(iter(feature_paths.values())))
        write_feature_raster(comp_path, composite, profile)
        evidence["composite_score"] = _rel(comp_path)

    report_path = _anomalies_root(aoi_id) / f"report_{latest_date}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_dict = report.model_dump()
    report_dict["evidence_paths"] = evidence
    report_path.write_text(json.dumps(report_dict, indent=2), encoding="utf-8")
    evidence["report"] = _rel(report_path)
    report.evidence_paths = evidence
    return report


def run_analysis(run_id: str | None = None) -> AnalysisResult:
    """Run full feature engineering and anomaly scoring."""
    settings = get_settings()
    started = datetime.now(timezone.utc)
    run_id = run_id or started.strftime("%Y%m%dT%H%M%SZ")

    reg = MetadataRegistry()
    items = reg.list_items()
    logger.info("analysis_start", run_id=run_id, items=len(items))

    feature_results: list[FeatureResult] = []
    groups = group_optical_acquisitions(items)

    index_series: dict[str, dict[str, list[tuple[str, Path]]]] = {
        "ndvi": {},
        "ndwi": {},
        "nbr": {},
    }

    for group in groups:
        feature_results.extend(_compute_indices_for_group(group))
        for index_name in index_series:
            feat_path = _features_root(group.aoi_id) / group.date_key / f"{index_name}.tif"
            if feat_path.exists():
                index_series[index_name].setdefault(group.aoi_id, []).append(
                    (group.date_key, feat_path)
                )

    for index_name, by_aoi in index_series.items():
        for aoi_id, series in by_aoi.items():
            feature_results.extend(_temporal_diffs_for_aoi(aoi_id, index_name, series))

    feature_results.extend(_integrate_sar_disturbances())

    reports: list[AOIAnomalyReport] = []
    aoi_ids = {g.aoi_id for g in groups} | {r.aoi_id for r in feature_results}

    for aoi_id in sorted(aoi_ids):
        if not get_aoi(aoi_id):
            continue
        feature_paths: dict[str, Path] = {}
        aoi_dates = [g.date_key for g in groups if g.aoi_id == aoi_id]
        latest_date = max(aoi_dates) if aoi_dates else "unknown"

        temporal_dir = _features_root(aoi_id) / "temporal"
        if temporal_dir.exists():
            for diff in sorted(temporal_dir.glob("*_diff.tif")):
                name = diff.stem
                if "ndvi" in name:
                    feature_paths["temporal_ndvi"] = diff
                elif "ndwi" in name:
                    feature_paths["temporal_ndwi"] = diff
                elif "nbr" in name:
                    feature_paths["temporal_nbr"] = diff

        sar_dir = _features_root(aoi_id) / "sar"
        if sar_dir.exists():
            sar_files = sorted(sar_dir.glob("*_diff.tif"))
            if sar_files:
                feature_paths["sar_disturbance"] = sar_files[-1]

        if feature_paths:
            reports.append(_score_aoi(aoi_id, latest_date, feature_paths))

    completed = datetime.now(timezone.utc)
    ok = {AnalysisStatus.OK, AnalysisStatus.SKIPPED}
    features_ok = sum(1 for r in feature_results if r.status in ok)
    features_failed = sum(1 for r in feature_results if r.status == AnalysisStatus.FAILED)
    anomalies_detected = sum(1 for r in reports if r.is_anomaly)

    result = AnalysisResult(
        run_id=run_id,
        started_at=started,
        completed_at=completed,
        features_ok=features_ok,
        features_failed=features_failed,
        anomalies_detected=anomalies_detected,
        feature_results=feature_results,
        reports=reports,
        metadata={
            "thresholds": {
                "ndvi": settings.anomaly_ndvi_threshold,
                "ndwi": settings.anomaly_ndwi_threshold,
                "nbr": settings.anomaly_nbr_threshold,
                "sar": settings.anomaly_sar_threshold,
                "composite": settings.anomaly_composite_threshold,
            }
        },
    )

    state = _load_state()
    state.setdefault("runs", []).append(
        {
            "run_id": run_id,
            "features_ok": features_ok,
            "anomalies_detected": anomalies_detected,
        }
    )
    state["last_run"] = result.model_dump(mode="json")
    _save_state(state)

    logger.info(
        "analysis_complete",
        run_id=run_id,
        features_ok=features_ok,
        anomalies=anomalies_detected,
    )
    return result
