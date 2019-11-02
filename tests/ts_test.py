# coding utf-8
import pytest

from ladybug_comfort.ts import thermal_sensation
from ladybug_comfort.ts import thermal_sensation_effect_category


def test_thermal_sensation():
    """Test the thermal_sensation function."""
    assert thermal_sensation(40, 10, 15, 10, 11) == pytest.approx(2.9208,
                                                                  rel=1e-3)
    assert thermal_sensation(20, 50, 34, 48, 32) == pytest.approx(-12.1482,
                                                                  rel=1e-3)


def test_thermal_sensation_effect_category():
    """Test the thermal_sensation_effect_category function"""
    assert thermal_sensation_effect_category(7.5) == 3
    assert thermal_sensation_effect_category(6.4) == 2
    assert thermal_sensation_effect_category(5.2) == 1
    assert thermal_sensation_effect_category(4.8) == 0
    assert thermal_sensation_effect_category(3.7) == -1
    assert thermal_sensation_effect_category(2.5) == -2
    assert thermal_sensation_effect_category(-4) == -3
