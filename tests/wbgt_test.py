# coding utf-8
import pytest

from ladybug_comfort.wbgt import wbgt_outdoors, wbgt_indoors, wbgt_warning_category


def test_apparent_temperature():
    """Test the WBGT function."""
    assert wbgt_outdoors(32, 30, 10, 75) == pytest.approx(37.91974, rel=1e-3)
    assert wbgt_outdoors(30, 28, 10, 37) == pytest.approx(24.8535, rel=1e-3)

    assert wbgt_indoors(30, 28, 10) == pytest.approx(29.6639, rel=1e-3)
    assert wbgt_indoors(32, 26, 30) == pytest.approx(30.9779, rel=1e-3)

    assert wbgt_warning_category(33) == 4
    assert wbgt_warning_category(32) == 3
    assert wbgt_warning_category(30) == 2
    assert wbgt_warning_category(29) == 1
    assert wbgt_warning_category(26) == 0
