# coding utf-8
import pytest

from ladybug_comfort.humidex import humidex


def test_humidex():
    """Test the humidex function."""
    assert humidex(22, 15) == pytest.approx(25.96900, rel=1e-3)
    assert humidex(20, 20) == pytest.approx(27.56977, rel=1e-3)
    assert humidex(28, 20) == pytest.approx(35.56977, rel=1e-3)
    assert humidex(28, 26) == pytest.approx(41.45899, rel=1e-3)
    assert humidex(34, 25) == pytest.approx(46.33840, rel=1e-3)
