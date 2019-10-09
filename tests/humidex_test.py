# coding utf-8
import pytest

from ladybug_comfort.humidex import humidex, humidex_degree_of_comfort


def test_humidex():
    """Test the humidex function."""
    assert humidex(22, 15) == pytest.approx(25.96900, rel=1e-3)
    assert humidex(20, 20) == pytest.approx(27.56977, rel=1e-3)
    assert humidex(28, 20) == pytest.approx(35.56977, rel=1e-3)
    assert humidex(28, 26) == pytest.approx(41.45899, rel=1e-3)
    assert humidex(34, 25) == pytest.approx(46.33840, rel=1e-3)


def test_humidex_degree_of_comfort():
    """Test the humidex degree of comfort thresholds"""
    assert humidex_degree_of_comfort(0.0) == 0
    assert humidex_degree_of_comfort(19.0) == 0
    assert humidex_degree_of_comfort(19.9) == 0
    assert humidex_degree_of_comfort(20.0) == 1
    assert humidex_degree_of_comfort(29.9) == 1
    assert humidex_degree_of_comfort(30.0) == 2
    assert humidex_degree_of_comfort(39.9) == 2
    assert humidex_degree_of_comfort(40.0) == 3
    assert humidex_degree_of_comfort(45.9) == 3
    assert humidex_degree_of_comfort(46.0) == 4
    assert humidex_degree_of_comfort(50.0) == 4
