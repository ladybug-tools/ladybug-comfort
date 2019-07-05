# coding utf-8
import pytest

from ladybug_comfort.degreetime import heating_degree_time, cooling_degree_time

from ladybug.epw import EPW
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.datatype.temperaturetime import HeatingDegreeTime, CoolingDegreeTime


def test_heating_degree_time():
    """Test the heating_degree_time function."""
    temperature = 5
    base_temp = 18
    assert heating_degree_time(temperature, base_temp) == base_temp - temperature

    temperature = 20
    base_temp = 18
    assert heating_degree_time(temperature, base_temp) == 0


def test_heating_degree_time_collection():
    """Test the heating_degree_time function with Data Collections."""
    calc_length = 8760
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)

    hourly_heat = HourlyContinuousCollection.compute_function_aligned(
        heating_degree_time, [epw.dry_bulb_temperature, 18],
        HeatingDegreeTime(), 'degC-hours')
    hourly_heat.convert_to_unit('degC-days')

    assert isinstance(hourly_heat, HourlyContinuousCollection)
    assert len(hourly_heat.values) == calc_length
    assert hourly_heat[0] == pytest.approx(1.004166, rel=1e-3)


def test_cooling_degree_time():
    """Test the cooling_degree_time function."""
    temperature = 30
    base_temp = 23
    assert cooling_degree_time(temperature, base_temp) == temperature - base_temp

    temperature = 20
    base_temp = 23
    assert cooling_degree_time(temperature, base_temp) == 0


def test_cooling_degree_time_collection():
    """Test the cooling_degree_time function with Data Collections."""
    calc_length = 8760
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)

    hourly_cool = HourlyContinuousCollection.compute_function_aligned(
        cooling_degree_time, [epw.dry_bulb_temperature, 23],
        CoolingDegreeTime(), 'degC-hours')
    hourly_cool.convert_to_unit('degC-days')

    assert isinstance(hourly_cool, HourlyContinuousCollection)
    assert len(hourly_cool.values) == calc_length
    assert hourly_cool[4000] == pytest.approx(0.3375, rel=1e-3)
