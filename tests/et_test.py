# coding utf-8
import pytest
from ladybug_comfort.et import effective_temperature

def test_effective_temperature():
    """Test the effective_temperature function"""
    et_obj = effective_temperature(
        ta=13.7,
        ws=7.8,
        rh=74,
        sr=104,
        ac=318)

    assert et_obj[0] == 0.07758930406978726
    assert et_obj[1] == -4
   