"""Spectral index unit tests."""

import numpy as np

from backend.processing.indices import compute_nbr, compute_ndvi, compute_ndwi, classify_band


def test_classify_band():
    assert classify_band("B04") == "red"
    assert classify_band("B08") == "nir"
    assert classify_band("B11") == "swir"


def test_ndvi_range():
    red = np.array([[0.1, 0.2], [0.1, 0.2]], dtype=np.float32)
    nir = np.array([[0.5, 0.6], [0.5, 0.6]], dtype=np.float32)
    ndvi = compute_ndvi(red, nir)
    assert float(np.nanmax(ndvi)) <= 1.0
    assert float(np.nanmin(ndvi)) >= -1.0


def test_ndwi_and_nbr_finite():
    a = np.full((4, 4), 0.3, dtype=np.float32)
    b = np.full((4, 4), 0.5, dtype=np.float32)
    assert np.isfinite(compute_ndwi(a, b)).all()
    assert np.isfinite(compute_nbr(b, a)).all()
