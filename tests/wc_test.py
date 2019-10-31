# coding utf-8
import pytest

from ladybug_comfort.wc import windchill_index
from ladybug_comfort.wc import windchill_index_effect_category
from ladybug_comfort.wc import windchill_temp
from ladybug_comfort.wc import windchill_temp_effect_category


def test_windchill_index():
    """Test the windchill_index function"""
    assert windchill_index(32, 85) == pytest.approx(20.5216, rel=1e-3)
    assert windchill_index(20, 50) == pytest.approx(471.1182, rel=1e-3)


def test_windchill_index_effect_category():
    """Test the windchill_index_effect_category function"""
    assert windchill_index_effect_category(2350) == -4
    assert windchill_index_effect_category(1700) == -3
    assert windchill_index_effect_category(1000) == -2
    assert windchill_index_effect_category(600) == -1
    assert windchill_index_effect_category(400) == 0
    assert windchill_index_effect_category(150) == 1
    assert windchill_index_effect_category(90) == 2
    assert windchill_index_effect_category(30) == 3


def test_windchill_temp():
    """Test the windchill_temp function"""
    assert windchill_temp(32, 85) == pytest.approx(36.3012, rel=1e-3)
    assert windchill_temp(20, 50) == pytest.approx(17.6540, rel=1e-3)


def test_windchill_temp_effect_category():
    """Test the windchill_index_effect_category function"""
    assert windchill_temp_effect_category(10) == 0
    assert windchill_temp_effect_category(-5) == -1
    assert windchill_temp_effect_category(-15) == -2
    assert windchill_temp_effect_category(-31) == -3
    assert windchill_temp_effect_category(-45) == -4
    assert windchill_temp_effect_category(-50) == -5
    assert windchill_temp_effect_category(-60) == -6
