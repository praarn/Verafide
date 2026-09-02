import pytest

from app.ml.inference import confidence_band


@pytest.mark.parametrize(
    "value, band",
    [
        (0.99, "high"),
        (0.85, "high"),
        (0.84, "moderate"),
        (0.65, "moderate"),
        (0.64, "low"),
        (0.50, "low"),
    ],
)
def test_confidence_band_thresholds(value, band):
    assert confidence_band(value) == band
