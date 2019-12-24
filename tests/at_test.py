# coding utf-8
import pytest

from ladybug_comfort.at import apparent_temperature, apparent_temperature_warning_category


def test_apparent_temperature():
    """Test the apparent_temperature function."""
    assert apparent_temperature(32, 85, 10) == pytest.approx(34.290083, rel=1e-3)
    assert apparent_temperature(20, 50, 15) == pytest.approx(9.3482423, rel=1e-3)

    assert apparent_temperature_warning_category(60) == 4
    assert apparent_temperature_warning_category(40) == 3
    assert apparent_temperature_warning_category(35) == 2
    assert apparent_temperature_warning_category(26) == 1
    assert apparent_temperature_warning_category(25) == 0
    assert apparent_temperature_warning_category(16) == -1
    assert apparent_temperature_warning_category(11) == -2
    assert apparent_temperature_warning_category(6) == -3
    assert apparent_temperature_warning_category(5) == -4
    assert apparent_temperature_warning_category(0) == -5
    assert apparent_temperature_warning_category(-5) == -6
