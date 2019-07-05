# coding utf-8
import pytest

from ladybug_comfort.hi import heat_index, heat_index_warning_category

from ladybug.epw import EPW
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.datatype.temperature import Temperature
from ladybug.datatype.thermalcondition import ThermalCondition


def test_heating_degree_time():
    """Test the heat_index function."""
    assert heat_index(32, 85) == pytest.approx(46.582479, rel=1e-3)
    assert heat_index(20, 50) == pytest.approx(19.3611, rel=1e-3)

    assert heat_index_warning_category(20) == 0
    assert heat_index_warning_category(30) == 1
    assert heat_index_warning_category(38) == 2
    assert heat_index_warning_category(44) == 3
    assert heat_index_warning_category(56) == 4


def test_heating_degree_time_collection():
    """Test the heat_index function with Data Collections."""
    calc_length = 8760
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)

    hourly_hi = HourlyContinuousCollection.compute_function_aligned(
        heat_index, [epw.dry_bulb_temperature, epw.relative_humidity],
        Temperature(), 'C')

    assert isinstance(hourly_hi, HourlyContinuousCollection)
    assert len(hourly_hi.values) == calc_length
    assert hourly_hi[4000] == pytest.approx(30.89833, rel=1e-3)

    hourly_category = HourlyContinuousCollection.compute_function_aligned(
        heat_index_warning_category, [hourly_hi], ThermalCondition(), 'condition')
    assert isinstance(hourly_category, HourlyContinuousCollection)
    assert len(hourly_category.values) == calc_length
    assert hourly_category[4000] == 1
