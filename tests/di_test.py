
# coding utf-8
import pytest

from ladybug_comfort.di import discomfort_index, discomfort_index_effect_category


def test_discomfort_index():
    """Test the discomfort_index function."""
    assert discomfort_index(32, 85) == pytest.approx(30.55625, rel=1e-3)
    assert discomfort_index(20, 50) == pytest.approx(18.4875, rel=1e-3)

    assert discomfort_index_effect_category(35) == 3
    assert discomfort_index_effect_category(28) == 2
    assert discomfort_index_effect_category(25) == 1
    assert discomfort_index_effect_category(18) == 0
    assert discomfort_index_effect_category(14) == -1
    assert discomfort_index_effect_category(10) == -2
    assert discomfort_index_effect_category(-5) == -3
    assert discomfort_index_effect_category(-15) == -4
    assert discomfort_index_effect_category(-21) == -5
    assert discomfort_index_effect_category(-45) == -6
