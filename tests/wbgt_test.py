# coding utf-8
import pytest

from ladybug_comfort.wbgt import wet_bulb_globe_temperature, wbgt_warning_category


def test_apparent_temperature():
    """Test the WBGT function."""
    assert wet_bulb_globe_temperature(32, 30, 10, 75) == pytest.approx(25.6377, rel=1e-3)
    assert wet_bulb_globe_temperature(30, 28, 0.1, 37) == pytest.approx(22.803, rel=1e-3)

    assert wbgt_warning_category(33) == 4
    assert wbgt_warning_category(32) == 3
    assert wbgt_warning_category(30) == 2
    assert wbgt_warning_category(29) == 1
    assert wbgt_warning_category(26) == 0
