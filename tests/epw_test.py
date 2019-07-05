# coding utf-8
import pytest

from ladybug_comfort.collection.utci import UTCI
from ladybug_comfort.collection.pmv import PMV

from ladybug.datacollection import HourlyContinuousCollection
from ladybug.epw import EPW


def test_get_universal_thermal_climate_index():
    """Test the get_universal_thermal_climate_index method."""
    calc_length = 8760
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    utci_obj = epw.get_universal_thermal_climate_index(False, False)

    assert isinstance(utci_obj, UTCI)
    assert isinstance(utci_obj.air_temperature, HourlyContinuousCollection)
    assert len(utci_obj.air_temperature.values) == calc_length
    assert utci_obj.air_temperature[0] == -6.1
    assert isinstance(utci_obj.rel_humidity, HourlyContinuousCollection)
    assert len(utci_obj.rel_humidity.values) == calc_length
    assert utci_obj.rel_humidity[0] == 81

    assert isinstance(utci_obj.universal_thermal_climate_index, HourlyContinuousCollection)
    assert len(utci_obj.universal_thermal_climate_index.values) == calc_length
    assert utci_obj.universal_thermal_climate_index[0] == pytest.approx(-5.367017, rel=1e-3)
    assert isinstance(utci_obj.thermal_condition_eleven_point, HourlyContinuousCollection)
    assert len(utci_obj.thermal_condition_eleven_point.values) == calc_length
    assert utci_obj.thermal_condition_eleven_point[0] == -2

    assert utci_obj.percent_neutral == pytest.approx(47.488584, rel=1e-3)
    assert utci_obj.percent_hot == pytest.approx(9.38356164, rel=1e-3)
    assert utci_obj.percent_cold == pytest.approx(43.1278538, rel=1e-3)


def test_get_universal_thermal_climate_index_with_wind():
    """Test the get_universal_thermal_climate_index method with wind."""
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    utci_obj = epw.get_universal_thermal_climate_index(True, False)

    assert utci_obj.percent_neutral == pytest.approx(35.6849315, rel=1e-3)
    assert utci_obj.percent_hot == pytest.approx(3.3447488, rel=1e-3)
    assert utci_obj.percent_cold == pytest.approx(60.970319, rel=1e-3)


def test_get_universal_thermal_climate_index_with_sun():
    """Test the get_universal_thermal_climate_index method with sun."""
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    utci_obj = epw.get_universal_thermal_climate_index(False, True)

    assert utci_obj.percent_neutral == pytest.approx(40.730593, rel=1e-3)
    assert utci_obj.percent_hot == pytest.approx(20.4223744, rel=1e-3)
    assert utci_obj.percent_cold == pytest.approx(38.8470319, rel=1e-3)


def test_get_universal_thermal_climate_index_with_sun_and_wind():
    """Test the get_universal_thermal_climate_index method with wind and sun."""
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    utci_obj = epw.get_universal_thermal_climate_index(True, True)

    assert utci_obj.percent_neutral == pytest.approx(31.4269406, rel=1e-3)
    assert utci_obj.percent_hot == pytest.approx(11.4611872, rel=1e-3)
    assert utci_obj.percent_cold == pytest.approx(57.111872, rel=1e-3)


def test_get_standard_effective_temperature():
    """Test the get_standard_effective_temperature method."""
    calc_length = 8760
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    set_obj = epw.get_standard_effective_temperature(False, False,
                                                     met_rate=2.4, clo_value=1.0)

    assert isinstance(set_obj, PMV)
    assert isinstance(set_obj.air_temperature, HourlyContinuousCollection)
    assert len(set_obj.air_temperature.values) == calc_length
    assert set_obj.air_temperature[0] == -6.1
    assert isinstance(set_obj.rel_humidity, HourlyContinuousCollection)
    assert len(set_obj.rel_humidity.values) == calc_length
    assert set_obj.rel_humidity[0] == 81

    assert isinstance(set_obj.standard_effective_temperature, HourlyContinuousCollection)
    assert len(set_obj.standard_effective_temperature.values) == calc_length
    assert set_obj.standard_effective_temperature[0] == pytest.approx(12.76, rel=1e-2)
    assert isinstance(set_obj.thermal_condition, HourlyContinuousCollection)
    assert len(set_obj.thermal_condition.values) == calc_length
    assert set_obj.thermal_condition[0] == -1

    assert set_obj.percent_neutral == pytest.approx(18.961187, rel=1e-3)
    assert set_obj.percent_hot == pytest.approx(38.6415525, rel=1e-3)
    assert set_obj.percent_cold == pytest.approx(42.39726, rel=1e-3)


def test_get_standard_effective_temperature_with_wind():
    """Test the get_standard_effective_temperature method with wind."""
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    set_obj = epw.get_standard_effective_temperature(True, False,
                                                     met_rate=2.4, clo_value=1.0)

    assert set_obj.percent_neutral == pytest.approx(19.82, rel=1e-2)
    assert set_obj.percent_hot == pytest.approx(15.56, rel=1e-2)
    assert set_obj.percent_cold == pytest.approx(64.61, rel=1e-2)


def test_get_standard_effective_temperature_with_sun():
    """Test the get_standard_effective_temperature method with sun."""
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    set_obj = epw.get_standard_effective_temperature(False, True,
                                                     met_rate=2.4, clo_value=1.0)

    assert set_obj.percent_neutral == pytest.approx(17.043378, rel=1e-3)
    assert set_obj.percent_hot == pytest.approx(44.56621, rel=1e-3)
    assert set_obj.percent_cold == pytest.approx(38.39041, rel=1e-3)


def test_get_standard_effective_temperature_with_sun_and_wind():
    """Test the get_standard_effective_temperature method with sun and wind."""
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    set_obj = epw.get_standard_effective_temperature(True, True,
                                                     met_rate=2.4, clo_value=1.0)

    assert set_obj.percent_neutral == pytest.approx(17.95, rel=1e-2)
    assert set_obj.percent_hot == pytest.approx(18.82, rel=1e-2)
    assert set_obj.percent_cold == pytest.approx(63.23, rel=1e-2)
