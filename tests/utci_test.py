# coding utf-8
import pytest

from ladybug_comfort.collection.utci import UTCI
from ladybug_comfort.parameter.utci import UTCIParameter

from ladybug_comfort.utci import universal_thermal_climate_index, calc_missing_utci_input

from ladybug.analysisperiod import AnalysisPeriod
from ladybug.header import Header
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.epw import EPW

from ladybug.datatype.temperature import Temperature
from ladybug.datatype.fraction import RelativeHumidity
from ladybug.datatype.speed import AirSpeed


def test_utci():
    """Test the utci function"""
    assert universal_thermal_climate_index(20, 20, 3, 50) == \
        pytest.approx(16.24224, rel=1e-2)
    assert universal_thermal_climate_index(30, 30, 0.5, 90) == \
        pytest.approx(35.511294, rel=1e-2)


def test_calc_missing_utci_input():
    """Test the calc_missing_utci_input function"""
    input_1 = {'ta': None, 'tr': 20, 'vel': 0.5, 'rh': 50}
    input_2 = {'ta': 20, 'tr': None, 'vel': 0.5, 'rh': 50}
    input_3 = {'ta': 22, 'tr': 22, 'vel': None, 'rh': 50}
    input_4 = {'ta': 20, 'tr': 20, 'vel': 0.5, 'rh': None}
    input_5 = {'ta': None, 'tr': None, 'vel': 5, 'rh': 50}
    updated_input_1 = calc_missing_utci_input(25, input_1)
    updated_input_2 = calc_missing_utci_input(25, input_2)
    updated_input_3 = calc_missing_utci_input(15, input_3, up_bound=1)
    updated_input_4 = calc_missing_utci_input(22, input_4)
    updated_input_5 = calc_missing_utci_input(22, input_5)
    assert updated_input_1['ta'] == pytest.approx(26.9827, rel=1e-2)
    assert updated_input_2['tr'] == pytest.approx(36.3803, rel=1e-2)
    assert updated_input_3['vel'] == pytest.approx(5.77514, rel=1e-2)
    assert updated_input_4['rh'] == pytest.approx(90.388989, rel=1e-2)
    assert updated_input_5['ta'] == pytest.approx(26.413594, rel=1e-2)
    assert updated_input_5['ta'] == updated_input_5['tr']


def test_utci_parameters():
    """Test UTCI Parameters."""
    cold_thresh = 8
    heat_thresh = 27
    extreme_cold_thresh = -41
    very_strong_cold_thresh = -28
    strong_cold_thresh = -14
    moderate_cold_thresh = -1
    moderate_heat_thresh = 29
    strong_heat_thresh = 33
    very_strong_heat_thresh = 39
    extreme_heat_thresh = 47

    utci_comf = UTCIParameter(
        cold_thresh, heat_thresh, extreme_cold_thresh, very_strong_cold_thresh,
        strong_cold_thresh, moderate_cold_thresh, moderate_heat_thresh,
        strong_heat_thresh, very_strong_heat_thresh, extreme_heat_thresh)

    assert utci_comf.cold_thresh == cold_thresh
    assert utci_comf.heat_thresh == heat_thresh
    assert utci_comf.extreme_cold_thresh == extreme_cold_thresh
    assert utci_comf.very_strong_cold_thresh == very_strong_cold_thresh
    assert utci_comf.strong_cold_thresh == strong_cold_thresh
    assert utci_comf.moderate_cold_thresh == moderate_cold_thresh
    assert utci_comf.moderate_heat_thresh == moderate_heat_thresh
    assert utci_comf.strong_heat_thresh == strong_heat_thresh
    assert utci_comf.very_strong_heat_thresh == very_strong_heat_thresh
    assert utci_comf.extreme_heat_thresh == extreme_heat_thresh


def test_utci_parameters_invalid():
    """Test UTCI Parameters for invalid inputs."""
    cold_thresh = 30
    heat_thresh = 8

    with pytest.raises(AssertionError):
        UTCIParameter(cold_thresh=cold_thresh)
    with pytest.raises(AssertionError):
        UTCIParameter(heat_thresh=heat_thresh)


def test_comfort_check():
    """Test comfort check on UTCI Parameters."""
    utci_comf = UTCIParameter()
    comf_test = utci_comf.is_comfortable(5)
    assert comf_test == 0
    comf_test = utci_comf.is_comfortable(22)
    assert comf_test == 1


def test_thermal_condition_check():
    """Test the thermal condition check on UTCI Parameters."""
    utci_comf = UTCIParameter()
    condition_test = utci_comf.thermal_condition(5)
    assert condition_test == -1
    condition_test = utci_comf.thermal_condition(22)
    assert condition_test == 0
    condition_test = utci_comf.thermal_condition(32)
    assert condition_test == 1


def test_thermal_condition_five_point_check():
    """Test the thermal condition check on UTCI Parameters."""
    utci_comf = UTCIParameter()
    condition_test = utci_comf.thermal_condition_five_point(-15)
    assert condition_test == -2
    condition_test = utci_comf.thermal_condition_five_point(5)
    assert condition_test == -1
    condition_test = utci_comf.thermal_condition_five_point(22)
    assert condition_test == 0
    condition_test = utci_comf.thermal_condition_five_point(30)
    assert condition_test == 1
    condition_test = utci_comf.thermal_condition_five_point(36)
    assert condition_test == 2


def test_thermal_condition_seven_point_check():
    """Test the thermal condition check on UTCI Parameters."""
    utci_comf = UTCIParameter()
    condition_test = utci_comf.thermal_condition_seven_point(-30)
    assert condition_test == -3
    condition_test = utci_comf.thermal_condition_seven_point(-15)
    assert condition_test == -2
    condition_test = utci_comf.thermal_condition_seven_point(5)
    assert condition_test == -1
    condition_test = utci_comf.thermal_condition_seven_point(22)
    assert condition_test == 0
    condition_test = utci_comf.thermal_condition_seven_point(30)
    assert condition_test == 1
    condition_test = utci_comf.thermal_condition_seven_point(36)
    assert condition_test == 2
    condition_test = utci_comf.thermal_condition_seven_point(40)
    assert condition_test == 3


def test_thermal_condition_none_point_check():
    """Test the thermal condition check on UTCI Parameters."""
    utci_comf = UTCIParameter()
    condition_test = utci_comf.thermal_condition_nine_point(-30)
    assert condition_test == -4
    condition_test = utci_comf.thermal_condition_nine_point(-18)
    assert condition_test == -3
    condition_test = utci_comf.thermal_condition_nine_point(-8)
    assert condition_test == -2
    condition_test = utci_comf.thermal_condition_nine_point(5)
    assert condition_test == -1
    condition_test = utci_comf.thermal_condition_nine_point(22)
    assert condition_test == 0
    condition_test = utci_comf.thermal_condition_nine_point(27)
    assert condition_test == 1
    condition_test = utci_comf.thermal_condition_nine_point(30)
    assert condition_test == 2
    condition_test = utci_comf.thermal_condition_nine_point(36)
    assert condition_test == 3
    condition_test = utci_comf.thermal_condition_nine_point(40)
    assert condition_test == 4


def test_thermal_condition_eleven_point_check():
    """Test the thermal condition check on UTCI Parameters."""
    utci_comf = UTCIParameter()
    condition_test = utci_comf.thermal_condition_eleven_point(-50)
    assert condition_test == -5
    condition_test = utci_comf.thermal_condition_eleven_point(-30)
    assert condition_test == -4
    condition_test = utci_comf.thermal_condition_eleven_point(-18)
    assert condition_test == -3
    condition_test = utci_comf.thermal_condition_eleven_point(-8)
    assert condition_test == -2
    condition_test = utci_comf.thermal_condition_eleven_point(5)
    assert condition_test == -1
    condition_test = utci_comf.thermal_condition_eleven_point(22)
    assert condition_test == 0
    condition_test = utci_comf.thermal_condition_eleven_point(27)
    assert condition_test == 1
    condition_test = utci_comf.thermal_condition_eleven_point(30)
    assert condition_test == 2
    condition_test = utci_comf.thermal_condition_eleven_point(36)
    assert condition_test == 3
    condition_test = utci_comf.thermal_condition_eleven_point(40)
    assert condition_test == 4
    condition_test = utci_comf.thermal_condition_eleven_point(50)
    assert condition_test == 5


def test_original_utci_category():
    """Test the thermal condition check on UTCI Parameters."""
    utci_comf = UTCIParameter()
    condition_test = utci_comf.original_utci_category(-50)
    assert condition_test == 0
    condition_test = utci_comf.original_utci_category(-30)
    assert condition_test == 1
    condition_test = utci_comf.original_utci_category(-18)
    assert condition_test == 2
    condition_test = utci_comf.original_utci_category(-8)
    assert condition_test == 3
    condition_test = utci_comf.original_utci_category(5)
    assert condition_test == 4
    condition_test = utci_comf.original_utci_category(22)
    assert condition_test == 5
    condition_test = utci_comf.original_utci_category(30)
    assert condition_test == 6
    condition_test = utci_comf.original_utci_category(36)
    assert condition_test == 7
    condition_test = utci_comf.original_utci_category(40)
    assert condition_test == 8
    condition_test = utci_comf.original_utci_category(50)
    assert condition_test == 9


def test_init_utci_collection():
    """Test the initialization of the UTCI collection and basic outputs."""
    calc_length = 24
    air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
    utci_obj = UTCI(air_temp, 50)

    assert utci_obj.comfort_model == 'Universal Thermal Climate Index'
    assert utci_obj.calc_length == calc_length
    str(utci_obj)  # test that the string representaiton is ok

    assert isinstance(utci_obj.air_temperature, HourlyContinuousCollection)
    assert len(utci_obj.air_temperature.values) == calc_length
    assert utci_obj.air_temperature[0] == 24
    assert isinstance(utci_obj.rel_humidity, HourlyContinuousCollection)
    assert len(utci_obj.rel_humidity.values) == calc_length
    assert utci_obj.rel_humidity[0] == 50

    assert isinstance(utci_obj.universal_thermal_climate_index, HourlyContinuousCollection)
    assert len(utci_obj.universal_thermal_climate_index.values) == calc_length
    assert utci_obj.universal_thermal_climate_index[0] == pytest.approx(23.8110341, rel=1e-3)


def test_utci_collection_defaults():
    """Test the default inputs assigned to the UTCI collection."""
    calc_length = 24
    air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
    utci_obj = UTCI(air_temp, 50)

    assert isinstance(utci_obj.rad_temperature, HourlyContinuousCollection)
    assert len(utci_obj.rad_temperature.values) == calc_length
    assert utci_obj.rad_temperature[0] == utci_obj.air_temperature[0]

    assert isinstance(utci_obj.wind_speed, HourlyContinuousCollection)
    assert len(utci_obj.wind_speed.values) == calc_length
    assert utci_obj.wind_speed[0] == 0.1

    assert isinstance(utci_obj.comfort_parameter, UTCIParameter)
    default_par = UTCIParameter()
    assert utci_obj.comfort_parameter.cold_thresh == default_par.cold_thresh
    assert utci_obj.comfort_parameter.heat_thresh == default_par.heat_thresh
    assert utci_obj.comfort_parameter.extreme_cold_thresh == default_par.extreme_cold_thresh
    assert utci_obj.comfort_parameter.very_strong_cold_thresh == default_par.very_strong_cold_thresh
    assert utci_obj.comfort_parameter.strong_cold_thresh == default_par.strong_cold_thresh
    assert utci_obj.comfort_parameter.moderate_cold_thresh == default_par.moderate_cold_thresh
    assert utci_obj.comfort_parameter.moderate_heat_thresh == default_par.moderate_heat_thresh
    assert utci_obj.comfort_parameter.strong_heat_thresh == default_par.strong_heat_thresh
    assert utci_obj.comfort_parameter.very_strong_heat_thresh == default_par.very_strong_heat_thresh
    assert utci_obj.comfort_parameter.extreme_heat_thresh == default_par.extreme_heat_thresh


def test_utci_collection_comfort_outputs():
    """Test the is_comfortable and thermal_condition outputs of the UTCI collection."""
    calc_length = 24
    air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    air_temp = HourlyContinuousCollection(air_temp_header, range(5, 5 + calc_length))
    utci_obj = UTCI(air_temp, 50)

    assert isinstance(utci_obj.is_comfortable, HourlyContinuousCollection)
    assert len(utci_obj.is_comfortable.values) == calc_length
    assert utci_obj.is_comfortable[0] == 0
    assert utci_obj.is_comfortable[12] == 1
    assert utci_obj.is_comfortable[23] == 0

    assert isinstance(utci_obj.thermal_condition, HourlyContinuousCollection)
    assert len(utci_obj.thermal_condition.values) == calc_length
    assert utci_obj.thermal_condition[0] == -1
    assert utci_obj.thermal_condition[12] == 0
    assert utci_obj.thermal_condition[23] == 1

    assert isinstance(utci_obj.thermal_condition_five_point, HourlyContinuousCollection)
    assert len(utci_obj.thermal_condition_five_point.values) == calc_length
    assert utci_obj.thermal_condition_five_point[0] == -1
    assert utci_obj.thermal_condition_five_point[12] == 0
    assert utci_obj.thermal_condition_five_point[23] == 1

    assert isinstance(utci_obj.thermal_condition_seven_point, HourlyContinuousCollection)
    assert len(utci_obj.thermal_condition_seven_point.values) == calc_length
    assert utci_obj.thermal_condition_seven_point[0] == -1
    assert utci_obj.thermal_condition_seven_point[12] == 0
    assert utci_obj.thermal_condition_seven_point[23] == 1

    assert isinstance(utci_obj.thermal_condition_nine_point, HourlyContinuousCollection)
    assert len(utci_obj.thermal_condition_nine_point.values) == calc_length
    assert utci_obj.thermal_condition_nine_point[0] == -1
    assert utci_obj.thermal_condition_nine_point[12] == 0
    assert utci_obj.thermal_condition_nine_point[22] == 1
    assert utci_obj.thermal_condition_nine_point[23] == 2

    assert isinstance(utci_obj.thermal_condition_eleven_point, HourlyContinuousCollection)
    assert len(utci_obj.thermal_condition_eleven_point.values) == calc_length
    assert utci_obj.thermal_condition_eleven_point[0] == -1
    assert utci_obj.thermal_condition_eleven_point[12] == 0
    assert utci_obj.thermal_condition_eleven_point[22] == 1
    assert utci_obj.thermal_condition_eleven_point[23] == 2

    assert isinstance(utci_obj.original_utci_category, HourlyContinuousCollection)
    assert len(utci_obj.original_utci_category.values) == calc_length
    assert utci_obj.original_utci_category[0] == 4
    assert utci_obj.original_utci_category[12] == 5
    assert utci_obj.original_utci_category[23] == 6


def test_utci_collection_immutability():
    """Test that the UTCI collection is immutable."""
    calc_length = 24
    air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
    utci_obj = UTCI(air_temp, 50)

    # check that editing the original collection does not mutate the object
    air_temp[0] = 26
    assert utci_obj.air_temperature[0] == 24

    # check that editing collection properties does not mutate the object
    with pytest.raises(Exception):
        utci_obj.air_temperature[0] = 26
    with pytest.raises(Exception):
        utci_obj.air_temperature.values = [26] * calc_length
    with pytest.raises(Exception):
        utci_obj.air_temperature = air_temp
    with pytest.raises(Exception):
        utci_obj.universal_thermal_climate_index[0] = 20
    with pytest.raises(Exception):
        utci_obj.universal_thermal_climate_index.values = [20] * calc_length

    # check that properties cannot be edited directly
    with pytest.raises(Exception):
        utci_obj.universal_thermal_climate_index = air_temp
    with pytest.raises(Exception):
        utci_obj.comfort_parameter = UTCIParameter()


def test_init_utci_collection_full_input():
    """Test the initialization of the UTCI collection will all inputs."""
    calc_length = 24
    air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
    custom_par = UTCIParameter(8, 25, -41, -28, -14, -1, 27, 31, 37, 45)
    utci_obj = UTCI(air_temp, 50, 22, 0.5, custom_par)

    assert utci_obj.air_temperature[0] == 24
    assert utci_obj.rel_humidity[0] == 50
    assert utci_obj.rad_temperature[0] == 22
    assert utci_obj.wind_speed[0] == 0.5
    assert utci_obj.comfort_parameter.cold_thresh == 8
    assert utci_obj.comfort_parameter.heat_thresh == 25
    assert utci_obj.comfort_parameter.extreme_cold_thresh == -41
    assert utci_obj.comfort_parameter.very_strong_cold_thresh == -28
    assert utci_obj.comfort_parameter.strong_cold_thresh == -14
    assert utci_obj.comfort_parameter.moderate_cold_thresh == -1
    assert utci_obj.comfort_parameter.moderate_heat_thresh == 27
    assert utci_obj.comfort_parameter.strong_heat_thresh == 31
    assert utci_obj.comfort_parameter.very_strong_heat_thresh == 37
    assert utci_obj.comfort_parameter.extreme_heat_thresh == 45


def test_init_utci_collection_full_collection_input():
    """Test initialization of the UTCI collection will all inputs as collections."""
    calc_length = 24
    air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
    rel_humid_header = Header(RelativeHumidity(), '%', AnalysisPeriod(end_month=1, end_day=1))
    rel_humid = HourlyContinuousCollection(rel_humid_header, [50] * calc_length)
    rad_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    rad_temp = HourlyContinuousCollection(rad_temp_header, [22] * calc_length)
    wind_speed_header = Header(AirSpeed(), 'm/s', AnalysisPeriod(end_month=1, end_day=1))
    wind_speed = HourlyContinuousCollection(wind_speed_header, [0.5] * calc_length)

    utci_obj = UTCI(air_temp, rel_humid, rad_temp, wind_speed)

    assert utci_obj.air_temperature[0] == 24
    assert utci_obj.rel_humidity[0] == 50
    assert utci_obj.rad_temperature[0] == 22
    assert utci_obj.wind_speed[0] == 0.5


def test_init_utci_collection_epw():
    """Test the initialization of the UTCI collection with EPW input."""
    calc_length = 8760
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    utci_obj = UTCI(epw.dry_bulb_temperature, epw.relative_humidity)

    assert len(utci_obj.air_temperature.values) == calc_length
    assert utci_obj.air_temperature[0] == -6.1
    assert len(utci_obj.rel_humidity.values) == calc_length
    assert utci_obj.rel_humidity[0] == 81

    assert len(utci_obj.universal_thermal_climate_index.values) == calc_length
    assert utci_obj.universal_thermal_climate_index[0] == pytest.approx(-5.367017, rel=1e-3)
    assert len(utci_obj.thermal_condition_eleven_point.values) == calc_length
    assert utci_obj.thermal_condition_eleven_point[0] == -2


def test_utci_collection_comfort_percent_outputs():
    """Test the is_comfortable and percent outputs of the UTCI collection."""
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    utci_obj = UTCI(epw.dry_bulb_temperature, epw.relative_humidity, wind_speed=epw.wind_speed)

    assert utci_obj.percent_comfortable == pytest.approx(35.6849315, rel=1e-3)
    assert utci_obj.percent_uncomfortable == pytest.approx(64.31506849, rel=1e-3)
    assert utci_obj.percent_neutral == pytest.approx(35.6849315, rel=1e-3)
    assert utci_obj.percent_hot == pytest.approx(3.3447488, rel=1e-3)
    assert utci_obj.percent_cold == pytest.approx(60.970319, rel=1e-3)

    assert utci_obj.percent_extreme_cold_stress == pytest.approx(0.35388127, rel=1e-3)
    assert utci_obj.percent_very_strong_cold_stress == pytest.approx(4.37214611, rel=1e-3)
    assert utci_obj.percent_strong_cold_stress == pytest.approx(16.541095, rel=1e-3)
    assert utci_obj.percent_moderate_cold_stress == pytest.approx(23.8356164, rel=1e-3)
    assert utci_obj.percent_slight_cold_stress == pytest.approx(15.8675799, rel=1e-3)

    assert utci_obj.percent_slight_heat_stress == pytest.approx(1.826484, rel=1e-3)
    assert utci_obj.percent_moderate_heat_stress == pytest.approx(1.312785, rel=1e-3)
    assert utci_obj.percent_strong_heat_stress == pytest.approx(0.2054794, rel=1e-3)
    assert utci_obj.percent_very_strong_heat_stress == 0.0
    assert utci_obj.percent_extreme_heat_stress == 0.0
