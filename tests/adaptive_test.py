# coding utf-8
import pytest

from ladybug_comfort.collection.adaptive import Adaptive, PrevailingTemperature
from ladybug_comfort.parameter.adaptive import AdaptiveParameter

from ladybug_comfort.adaptive import adaptive_comfort_ashrae55, \
    adaptive_comfort_en15251, adaptive_comfort_conditioned, \
    cooling_effect_ashrae55, cooling_effect_en15251, t_operative, \
    ashrae55_neutral_offset_from_ppd, en15251_neutral_offset_from_comfort_class, \
    weighted_running_mean_hourly, weighted_running_mean_daily, \
    check_prevailing_temperatures_ashrae55, check_prevailing_temperatures_en15251

from ladybug.analysisperiod import AnalysisPeriod
from ladybug.header import Header
from ladybug.datacollection import HourlyContinuousCollection, DailyCollection, \
    MonthlyCollection, MonthlyPerHourCollection
from ladybug.epw import EPW

from ladybug.datatype.temperature import Temperature, PrevailingOutdoorTemperature
from ladybug.datatype.speed import AirSpeed


def test_t_operative():
    """Test the t_operative function"""
    op_temp = t_operative(22, 28)
    assert op_temp == 25


def test_adaptive_comfort_ashrae55():
    """Test the adaptive_comfort_ashrae55 function"""
    # test typical condition
    comf_result = adaptive_comfort_ashrae55(22, 25)
    assert comf_result['to'] == 25
    assert comf_result['t_comf'] == pytest.approx(24.62, rel=1e-2)
    assert comf_result['deg_comf'] == pytest.approx(0.3799, rel=1e-2)
    assert comf_result['deg_comf'] == comf_result['to'] - comf_result['t_comf']

    # test a cooler outdoor case
    comf_result = adaptive_comfort_ashrae55(16, 25)
    assert comf_result['to'] == 25
    assert comf_result['t_comf'] == pytest.approx(22.76, rel=1e-2)
    assert comf_result['deg_comf'] == pytest.approx(2.23999, rel=1e-2)
    assert comf_result['deg_comf'] == comf_result['to'] - comf_result['t_comf']

    # test a very cold outdoor case
    comf_result = adaptive_comfort_ashrae55(5, 23)
    assert comf_result['to'] == 23
    assert comf_result['t_comf'] == pytest.approx(20.900, rel=1e-2)
    assert comf_result['deg_comf'] == pytest.approx(2.0999, rel=1e-2)

    # testa a very hot outdoor case
    comf_result = adaptive_comfort_ashrae55(35, 28)
    assert comf_result['to'] == 28
    assert comf_result['t_comf'] == pytest.approx(28.185, rel=1e-2)
    assert comf_result['deg_comf'] == pytest.approx(-0.185, rel=1e-2)

    # test a fully conditioned case
    comf_result = adaptive_comfort_conditioned(24, 23, 1, 'ASHRAE-55')
    assert comf_result['to'] == 23
    assert comf_result['t_comf'] == pytest.approx(24.76, rel=1e-2)
    assert comf_result['deg_comf'] == pytest.approx(-1.76, rel=1e-2)

    # test a partially conditioned case
    comf_result = adaptive_comfort_conditioned(24, 23, 0.5, 'ASHRAE-55')
    assert comf_result['to'] == 23
    assert comf_result['t_comf'] == pytest.approx(25.0, rel=1e-2)
    assert comf_result['deg_comf'] == pytest.approx(-2.0, rel=1e-2)

    # test a air speed cooling effect function
    assert cooling_effect_ashrae55(1.5, 26) == 2.2
    assert cooling_effect_ashrae55(1.0, 26) == 1.8
    assert cooling_effect_ashrae55(0.7, 26) == 1.2


def test_adaptive_comfort_en15251():
    """Test the adaptive_comfort_en15251 function"""
    # test typical condition
    comf_result = adaptive_comfort_en15251(22, 25)
    assert comf_result['to'] == 25
    assert comf_result['t_comf'] == pytest.approx(26.06, rel=1e-2)
    assert comf_result['deg_comf'] == pytest.approx(-1.06, rel=1e-2)
    assert comf_result['deg_comf'] == comf_result['to'] - comf_result['t_comf']

    # test a slightly cool case
    comf_result = adaptive_comfort_en15251(16, 25)
    assert comf_result['to'] == 25
    assert comf_result['t_comf'] == pytest.approx(24.08, rel=1e-2)
    assert comf_result['deg_comf'] == pytest.approx(0.9199, rel=1e-2)
    assert comf_result['deg_comf'] == comf_result['to'] - comf_result['t_comf']

    # test a very cold outdoor case
    comf_result = adaptive_comfort_en15251(5, 23)
    assert comf_result['to'] == 23
    assert comf_result['t_comf'] == pytest.approx(22.1, rel=1e-2)
    assert comf_result['deg_comf'] == pytest.approx(0.8999, rel=1e-2)

    # testa a very hot outdoor case
    comf_result = adaptive_comfort_en15251(35, 28)
    assert comf_result['to'] == 28
    assert comf_result['t_comf'] == pytest.approx(28.7, rel=1e-2)
    assert comf_result['deg_comf'] == pytest.approx(-0.7, rel=1e-2)

    # test a fully conditioned case
    comf_result = adaptive_comfort_conditioned(24, 23, 1, 'EN-15251')
    assert comf_result['to'] == 23
    assert comf_result['t_comf'] == pytest.approx(24.76, rel=1e-2)
    assert comf_result['deg_comf'] == pytest.approx(-1.76, rel=1e-2)

    # test a partially conditioned case
    comf_result = adaptive_comfort_conditioned(24, 23, 0.5, 'EN-15251')
    assert comf_result['to'] == 23
    assert comf_result['t_comf'] == pytest.approx(25.74, rel=1e-2)
    assert comf_result['deg_comf'] == pytest.approx(-2.74, rel=1e-2)

    # test a air speed cooling effect function
    assert cooling_effect_en15251(1.5, 26) == pytest.approx(3.707498, rel=1e-2)
    assert cooling_effect_en15251(1.0, 26) == pytest.approx(2.9835, rel=1e-2)
    assert cooling_effect_en15251(0.7, 26) == pytest.approx(2.34662122, rel=1e-2)


def test_ashrae55_neutral_offset_from_ppd():
    """Test the ashrae55_neutral_offset_from_ppd function."""
    assert ashrae55_neutral_offset_from_ppd(90) == 2.5
    assert ashrae55_neutral_offset_from_ppd(80) == 3.5
    with pytest.raises(Exception):
        ashrae55_neutral_offset_from_ppd(110)
    with pytest.raises(Exception):
        ashrae55_neutral_offset_from_ppd(-10)


def test_en15251_neutral_offset_from_comfort_class():
    """Test the ashrae55_neutral_offset_from_ppd function."""
    assert en15251_neutral_offset_from_comfort_class(1) == 2
    assert en15251_neutral_offset_from_comfort_class(2) == 3
    assert en15251_neutral_offset_from_comfort_class(3) == 4
    with pytest.raises(Exception):
        en15251_neutral_offset_from_comfort_class(0)
    with pytest.raises(Exception):
        en15251_neutral_offset_from_comfort_class(4)


def test_weighted_running_mean_hourly():
    """Test the weighted_running_mean_hourly function."""
    # Test with typical values
    outdoor = list(range(24)) * 365
    prevailing = weighted_running_mean_hourly(outdoor)
    for temp in prevailing[:24]:
        assert temp == prevailing[0]
    assert prevailing[0] == pytest.approx(11.5, rel=1e-2)

    # test with a number of values not divisible by 24
    outdoor = list(range(25)) * 7
    prevailing = weighted_running_mean_hourly(outdoor)
    for temp in prevailing[:24]:
        assert temp == prevailing[0]
    assert prevailing[0] == pytest.approx(12.42215, rel=1e-2)

    # test that an exception is thrown when values are less than a week.
    outdoor = list(range(24)) * 5
    with pytest.raises(Exception):
        prevailing = weighted_running_mean_hourly(outdoor)


def test_weighted_running_mean_daily():
    """Test the weighted_running_mean_daily function."""
    # Test with typical values
    outdoor = list(range(365))
    prevailing = weighted_running_mean_daily(outdoor)
    assert prevailing[0] == pytest.approx(362.1316, rel=1e-2)

    # test that an exception is thrown when values are less than a week.
    outdoor = list(range(5))
    with pytest.raises(Exception):
        prevailing = weighted_running_mean_daily(outdoor)


def test_check_prevailing_temperatures_ashrae55():
    """Test the check_prevailing_temperatures_ashrae55 function."""
    prev_temps = [22] * 24
    all_in_range, msg = check_prevailing_temperatures_ashrae55(prev_temps)
    assert all_in_range is True
    assert msg.startswith('All')

    prev_temps = range(30)
    all_in_range, msg = check_prevailing_temperatures_ashrae55(prev_temps)
    assert all_in_range is False
    assert msg.startswith('10')

    prev_temps = range(18, 40)
    all_in_range, msg = check_prevailing_temperatures_ashrae55(prev_temps)
    assert all_in_range is False
    assert msg.startswith('6')

    prev_temps = range(50)
    all_in_range, msg = check_prevailing_temperatures_ashrae55(prev_temps)
    assert all_in_range is False
    assert msg.startswith('10')


def test_check_prevailing_temperatures_en15251():
    """Test the check_prevailing_temperatures_ashrae55 function."""
    prev_temps = [22] * 24
    all_in_range, msg = check_prevailing_temperatures_en15251(prev_temps)
    assert all_in_range is True
    assert msg.startswith('All')

    prev_temps = range(30)
    all_in_range, msg = check_prevailing_temperatures_en15251(prev_temps)
    assert all_in_range is False
    assert msg.startswith('10')

    prev_temps = range(18, 38)
    all_in_range, msg = check_prevailing_temperatures_en15251(prev_temps)
    assert all_in_range is False
    assert msg.startswith('7')

    prev_temps = range(50)
    all_in_range, msg = check_prevailing_temperatures_en15251(prev_temps)
    assert all_in_range is False
    assert msg.startswith('10')


def test_adaptive_parameter_init():
    """Test the initialization of the AdaptiveParameter object."""
    ashrae55_or_en15251 = False
    neutral_offset = 2
    avg_month_or_run = True
    discr_or_cont = True
    cold_prevail_temp_limit = 18
    conditioning = 0.5
    adaptive_par = AdaptiveParameter(ashrae55_or_en15251=ashrae55_or_en15251,
                                     neutral_offset=neutral_offset,
                                     avg_month_or_running_mean=avg_month_or_run,
                                     discrete_or_continuous_air_speed=discr_or_cont,
                                     cold_prevail_temp_limit=cold_prevail_temp_limit,
                                     conditioning=conditioning)
    assert adaptive_par.ashrae55_or_en15251 == ashrae55_or_en15251
    assert adaptive_par.neutral_offset == neutral_offset
    assert adaptive_par.avg_month_or_running_mean is avg_month_or_run
    assert adaptive_par.discrete_or_continuous_air_speed == discr_or_cont
    assert adaptive_par.cold_prevail_temp_limit == cold_prevail_temp_limit
    assert adaptive_par.conditioning == conditioning


def test_adaptive_parameter_default_ahsrae55():
    """Test the default AdaptiveParameter properties."""
    adaptive_par = AdaptiveParameter()
    str(adaptive_par)  # test casting the parameters to a string
    assert adaptive_par.ashrae55_or_en15251 is True
    assert adaptive_par.neutral_offset == 2.5
    assert adaptive_par.avg_month_or_running_mean is True
    assert adaptive_par.discrete_or_continuous_air_speed is True
    assert adaptive_par.cold_prevail_temp_limit == 10
    assert adaptive_par.conditioning == 0
    assert adaptive_par.standard == 'ASHRAE-55'
    assert adaptive_par.prevailing_temperature_method == 'Averaged Monthly'
    assert adaptive_par.air_speed_method == 'Discrete'
    assert adaptive_par.minimum_operative == pytest.approx(18.4, rel=1e-2)

    adaptive_par.set_neutral_offset_from_ppd(80)
    assert adaptive_par.neutral_offset == 3.5


def test_adaptive_parameter_default_en15251():
    """Test the default AdaptiveParameter properties."""
    adaptive_par = AdaptiveParameter(False)
    str(adaptive_par)  # test casting the parameters to a string
    assert adaptive_par.ashrae55_or_en15251 is False
    assert adaptive_par.neutral_offset == 3
    assert adaptive_par.avg_month_or_running_mean is False
    assert adaptive_par.discrete_or_continuous_air_speed is False
    assert adaptive_par.cold_prevail_temp_limit == 15
    assert adaptive_par.conditioning == 0
    assert adaptive_par.standard == 'EN-15251'
    assert adaptive_par.prevailing_temperature_method == 'Running Mean'
    assert adaptive_par.air_speed_method == 'Continuous'
    assert adaptive_par.minimum_operative == pytest.approx(20.75, rel=1e-2)

    adaptive_par.set_neutral_offset_from_comfort_class(1)
    assert adaptive_par.neutral_offset == 2


def test_adaptive_parameter_incorrect():
    """Test incorrect AdaptiveParameter properties."""
    with pytest.raises(Exception):
        AdaptiveParameter(neutral_offset=-2)
    with pytest.raises(Exception):
        AdaptiveParameter(neutral_offset=12)
    with pytest.raises(Exception):
        AdaptiveParameter(cold_prevail_temp_limit=5)
    with pytest.raises(Exception):
        AdaptiveParameter(cold_prevail_temp_limit=30)
    with pytest.raises(Exception):
        AdaptiveParameter(conditioning=50)


def test_comfort_check():
    """Test comfort check on AdaptiveParameter."""
    comf_result = adaptive_comfort_ashrae55(24, 28)
    adaptive_par = AdaptiveParameter()
    comf_test = adaptive_par.is_comfortable(comf_result)
    assert comf_test == 0

    comf_result = adaptive_comfort_ashrae55(24, 28)
    adaptive_par = AdaptiveParameter()
    comf_test = adaptive_par.is_comfortable(comf_result, 3)
    assert comf_test == 1


def test_thermal_condition_check():
    """Test the thermal condition check on AdaptiveParameter."""
    comf_result = adaptive_comfort_ashrae55(24, 28)
    adaptive_par = AdaptiveParameter()
    condition_test = adaptive_par.thermal_condition(comf_result)
    assert condition_test == 1

    comf_result = adaptive_comfort_ashrae55(24, 28)
    adaptive_par = AdaptiveParameter()
    condition_test = adaptive_par.thermal_condition(comf_result, 3)
    assert condition_test == 0


def test_init_adaptive_collection():
    """Test the initialization of the Adaptive collection and basic outputs."""
    calc_length = 24
    prevail_header = Header(PrevailingOutdoorTemperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    prevail_temp = HourlyContinuousCollection(prevail_header, [22] * calc_length)
    op_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    op_temp = HourlyContinuousCollection(op_temp_header, [26] * calc_length)
    adapt_obj = Adaptive(prevail_temp, op_temp)

    assert adapt_obj.comfort_model == 'Adaptive'
    assert adapt_obj.calc_length == calc_length
    str(adapt_obj)  # test that the string representaiton is ok

    assert isinstance(adapt_obj.prevailing_outdoor_temperature, HourlyContinuousCollection)
    assert len(adapt_obj.prevailing_outdoor_temperature.values) == calc_length
    assert adapt_obj.prevailing_outdoor_temperature[0] == 22
    assert isinstance(adapt_obj.operative_temperature, HourlyContinuousCollection)
    assert len(adapt_obj.operative_temperature.values) == calc_length
    assert adapt_obj.operative_temperature[0] == 26

    assert isinstance(adapt_obj.neutral_temperature, HourlyContinuousCollection)
    assert len(adapt_obj.neutral_temperature.values) == calc_length
    assert adapt_obj.neutral_temperature[0] == pytest.approx(24.62, rel=1e-3)
    assert isinstance(adapt_obj.degrees_from_neutral, HourlyContinuousCollection)
    assert len(adapt_obj.degrees_from_neutral.values) == calc_length
    assert adapt_obj.degrees_from_neutral[0] == pytest.approx(1.3799, rel=1e-3)


def test_init_adaptive_collection_mrt():
    """Test the initialization of the Adaptive collection with MRT."""
    calc_length = 24
    prevail_header = Header(PrevailingOutdoorTemperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    prevail_temp = HourlyContinuousCollection(prevail_header, [22] * calc_length)
    air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
    adapt_obj = Adaptive.from_air_and_rad_temp(prevail_temp, air_temp, 28)

    assert adapt_obj.comfort_model == 'Adaptive'
    assert adapt_obj.calc_length == calc_length
    str(adapt_obj)  # test that the string representaiton is ok

    assert isinstance(adapt_obj.prevailing_outdoor_temperature, HourlyContinuousCollection)
    assert len(adapt_obj.prevailing_outdoor_temperature.values) == calc_length
    assert adapt_obj.prevailing_outdoor_temperature[0] == 22
    assert isinstance(adapt_obj.operative_temperature, HourlyContinuousCollection)
    assert len(adapt_obj.operative_temperature.values) == calc_length
    assert adapt_obj.operative_temperature[0] == 26

    assert isinstance(adapt_obj.neutral_temperature, HourlyContinuousCollection)
    assert len(adapt_obj.neutral_temperature.values) == calc_length
    assert adapt_obj.neutral_temperature[0] == pytest.approx(24.62, rel=1e-3)
    assert isinstance(adapt_obj.degrees_from_neutral, HourlyContinuousCollection)
    assert len(adapt_obj.degrees_from_neutral.values) == calc_length
    assert adapt_obj.degrees_from_neutral[0] == pytest.approx(1.3799, rel=1e-3)


def test_adaptive_collection_defaults():
    """Test the default inputs assigned to the Adaptive collection."""
    calc_length = 24
    prevail_header = Header(PrevailingOutdoorTemperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    prevail_temp = HourlyContinuousCollection(prevail_header, [22] * calc_length)
    op_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    op_temp = HourlyContinuousCollection(op_temp_header, [26] * calc_length)
    adapt_obj = Adaptive(prevail_temp, op_temp)

    assert isinstance(adapt_obj.air_speed, HourlyContinuousCollection)
    assert len(adapt_obj.air_speed.values) == calc_length
    assert adapt_obj.air_speed[0] == 0.1

    assert isinstance(adapt_obj.comfort_parameter, AdaptiveParameter)
    default_par = AdaptiveParameter()
    assert adapt_obj.comfort_parameter.ashrae55_or_en15251 == default_par.ashrae55_or_en15251
    assert adapt_obj.comfort_parameter.neutral_offset == default_par.neutral_offset
    assert adapt_obj.comfort_parameter.avg_month_or_running_mean == default_par.avg_month_or_running_mean
    assert adapt_obj.comfort_parameter.discrete_or_continuous_air_speed == default_par.discrete_or_continuous_air_speed
    assert adapt_obj.comfort_parameter.cold_prevail_temp_limit == default_par.cold_prevail_temp_limit
    assert adapt_obj.comfort_parameter.conditioning == default_par.conditioning


def test_adaptive_collection_comfort_outputs():
    """Test the is_comfortable and thermal_condition outputs of the collection."""
    calc_length = 24
    prevail_header = Header(PrevailingOutdoorTemperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    prevail_temp = HourlyContinuousCollection(prevail_header, [22] * calc_length)
    op_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    op_temp = HourlyContinuousCollection(op_temp_header, range(20, 20 + calc_length))
    adapt_obj = Adaptive(prevail_temp, op_temp)

    assert isinstance(adapt_obj.is_comfortable, HourlyContinuousCollection)
    assert len(adapt_obj.is_comfortable.values) == calc_length
    assert adapt_obj.is_comfortable[0] == 0
    assert adapt_obj.is_comfortable[5] == 1
    assert adapt_obj.is_comfortable[10] == 0

    assert isinstance(adapt_obj.thermal_condition, HourlyContinuousCollection)
    assert len(adapt_obj.thermal_condition.values) == calc_length
    assert adapt_obj.thermal_condition[0] == -1
    assert adapt_obj.thermal_condition[5] == 0
    assert adapt_obj.thermal_condition[10] == 1


def test_adaptive_collection_cooling_effect_output():
    """Test the cooling effect output of the Adaptive collection."""
    calc_length = 24
    prevail_header = Header(PrevailingOutdoorTemperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    prevail_temp = HourlyContinuousCollection(prevail_header, [22] * calc_length)
    op_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    op_temp = HourlyContinuousCollection(op_temp_header, [26] * calc_length)
    adapt_obj = Adaptive(prevail_temp, op_temp, air_speed=0.7)

    assert isinstance(adapt_obj.cooling_effect, HourlyContinuousCollection)
    assert len(adapt_obj.cooling_effect.values) == calc_length
    assert adapt_obj.cooling_effect[0] == 1.2


def test_adaptive_collection_immutability():
    """Test that the Adaptive collection is immutable."""
    calc_length = 24
    prevail_header = Header(PrevailingOutdoorTemperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    prevail_temp = HourlyContinuousCollection(prevail_header, [22] * calc_length)
    op_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    op_temp = HourlyContinuousCollection(op_temp_header, [26] * calc_length)
    adapt_obj = Adaptive(prevail_temp, op_temp)

    # check that editing the original collection does not mutate the object
    op_temp[0] = 28
    assert adapt_obj.operative_temperature[0] == 26

    # check that editing collection properties does not mutate the object
    with pytest.raises(Exception):
        adapt_obj.operative_temperature[0] = 28
    with pytest.raises(Exception):
        adapt_obj.operative_temperature.values = [28] * calc_length
    with pytest.raises(Exception):
        adapt_obj.degrees_from_neutral[0] = 0.5
    with pytest.raises(Exception):
        adapt_obj.degrees_from_neutral.values = [0.5] * calc_length

    # check that properties cannot be edited directly
    with pytest.raises(Exception):
        adapt_obj.operative_temperature = op_temp
    with pytest.raises(Exception):
        adapt_obj.degrees_from_neutral = op_temp
    with pytest.raises(Exception):
        adapt_obj.comfort_parameter = AdaptiveParameter(False)


def test_init_adaptive_collection_full_input():
    """Test the initialization of the Adaptive collection will all inputs."""
    calc_length = 24
    prevail_header = Header(PrevailingOutdoorTemperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    prevail_temp = HourlyContinuousCollection(prevail_header, [22] * calc_length)
    op_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    op_temp = HourlyContinuousCollection(op_temp_header, [26] * calc_length)
    custom_par = AdaptiveParameter(True, 2, False, False, 15, 0.25)
    adapt_obj = Adaptive(prevail_temp, op_temp, 0.7, custom_par)

    assert adapt_obj.operative_temperature[0] == 26
    assert adapt_obj.air_speed[0] == 0.7
    assert adapt_obj.comfort_parameter.ashrae55_or_en15251 is True
    assert adapt_obj.comfort_parameter.neutral_offset == 2
    assert adapt_obj.comfort_parameter.avg_month_or_running_mean is False
    assert adapt_obj.comfort_parameter.discrete_or_continuous_air_speed is False
    assert adapt_obj.comfort_parameter.cold_prevail_temp_limit == 15
    assert adapt_obj.comfort_parameter.conditioning == 0.25


def test_init_adaptive_collection_full_collection_input():
    """Test initialization of the Adaptive collection with inputs as collections."""
    calc_length = 24
    prevail_header = Header(PrevailingOutdoorTemperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    prevail_temp = HourlyContinuousCollection(prevail_header, [22] * calc_length)
    op_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    op_temp = HourlyContinuousCollection(op_temp_header, [26] * calc_length)
    air_speed_header = Header(AirSpeed(), 'm/s', AnalysisPeriod(end_month=1, end_day=1))
    air_speed = HourlyContinuousCollection(air_speed_header, [0.7] * calc_length)
    adapt_obj = Adaptive(prevail_temp, op_temp, air_speed)

    assert adapt_obj.operative_temperature[0] == 26
    assert adapt_obj.air_speed[0] == 0.7


def test_init_adaptive_collection_epw():
    """Test the initialization of the Adaptive collection with EPW input."""
    calc_length = 8760
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    adapt_obj = Adaptive(epw.dry_bulb_temperature, epw.dry_bulb_temperature)

    assert len(adapt_obj.prevailing_outdoor_temperature.values) == calc_length
    assert adapt_obj.prevailing_outdoor_temperature[0] == pytest.approx(-4.648456, rel=1e-3)
    assert len(adapt_obj.operative_temperature.values) == calc_length
    assert adapt_obj.operative_temperature[0] == -6.1

    assert len(adapt_obj.neutral_temperature.values) == calc_length
    assert adapt_obj.neutral_temperature[0] == pytest.approx(20.9, rel=1e-3)
    assert len(adapt_obj.degrees_from_neutral.values) == calc_length
    assert adapt_obj.degrees_from_neutral[0] == pytest.approx(-27.0, rel=1e-1)


def test_adaptive_collection_comfort_percent_outputs():
    """Test the percent outputs of the Adaptive collection."""
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    adapt_obj = Adaptive(epw.dry_bulb_temperature, epw.dry_bulb_temperature)

    assert adapt_obj.percent_comfortable == pytest.approx(12.95662, rel=1e-3)
    assert adapt_obj.percent_uncomfortable == pytest.approx(87.043378, rel=1e-3)
    assert adapt_obj.percent_neutral == pytest.approx(12.95662, rel=1e-3)
    assert adapt_obj.percent_hot == pytest.approx(6.4726027, rel=1e-3)
    assert adapt_obj.percent_cold == pytest.approx(80.570776, rel=1e-3)


def test_adaptive_collection_epw_prevailing():
    """Test the percent outputs of the Adaptive collection."""
    calc_length = 24
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)
    op_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
    op_temp = HourlyContinuousCollection(op_temp_header, [26] * calc_length)
    adapt_obj = Adaptive(epw.dry_bulb_temperature, op_temp)

    assert isinstance(adapt_obj.prevailing_outdoor_temperature, HourlyContinuousCollection)
    assert len(adapt_obj.prevailing_outdoor_temperature.values) == calc_length
    assert adapt_obj.prevailing_outdoor_temperature[0] == pytest.approx(-4.64845637, rel=1e-3)
    assert isinstance(adapt_obj.operative_temperature, HourlyContinuousCollection)
    assert len(adapt_obj.operative_temperature.values) == calc_length
    assert adapt_obj.operative_temperature[0] == 26

    assert isinstance(adapt_obj.neutral_temperature, HourlyContinuousCollection)
    assert len(adapt_obj.neutral_temperature.values) == calc_length
    assert adapt_obj.neutral_temperature[0] == pytest.approx(20.9, rel=1e-3)
    assert isinstance(adapt_obj.degrees_from_neutral, HourlyContinuousCollection)
    assert len(adapt_obj.degrees_from_neutral.values) == calc_length
    assert adapt_obj.degrees_from_neutral[0] == pytest.approx(5.099999, rel=1e-3)


def test_init_prevailing_temperature_hourly():
    """Test the PrevailingTemperature object with hourly inputs."""
    relative_path = './tests/epw/chicago.epw'
    epw = EPW(relative_path)

    prevail_obj = PrevailingTemperature(epw.dry_bulb_temperature, True)
    assert isinstance(prevail_obj.hourly_prevailing_temperature, HourlyContinuousCollection)
    assert len(prevail_obj.hourly_prevailing_temperature.values) == 8760
    assert isinstance(prevail_obj.daily_prevailing_temperature, DailyCollection)
    assert len(prevail_obj.daily_prevailing_temperature.values) == 365
    assert isinstance(prevail_obj.monthly_prevailing_temperature, MonthlyCollection)
    assert len(prevail_obj.monthly_prevailing_temperature.values) == 12
    assert isinstance(prevail_obj.monthly_per_hour_prevailing_temperature, MonthlyPerHourCollection)
    assert len(prevail_obj.monthly_per_hour_prevailing_temperature.values) == 288

    prevail_obj = PrevailingTemperature(epw.dry_bulb_temperature, False)
    assert isinstance(prevail_obj.hourly_prevailing_temperature, HourlyContinuousCollection)
    assert len(prevail_obj.hourly_prevailing_temperature.values) == 8760
    assert isinstance(prevail_obj.daily_prevailing_temperature, DailyCollection)
    assert len(prevail_obj.daily_prevailing_temperature.values) == 365
    assert isinstance(prevail_obj.monthly_prevailing_temperature, MonthlyCollection)
    assert len(prevail_obj.monthly_prevailing_temperature.values) == 12
    assert isinstance(prevail_obj.monthly_per_hour_prevailing_temperature, MonthlyPerHourCollection)
    assert len(prevail_obj.monthly_per_hour_prevailing_temperature.values) == 288


def test_init_prevailing_temperature_daily():
    """Test the PrevailingTemperature object with daily inputs."""
    outdoor_header = Header(Temperature(), 'C', AnalysisPeriod())
    outdoor_temp = DailyCollection(outdoor_header, range(365), AnalysisPeriod().doys_int)
    outdoor_temp = outdoor_temp.validate_analysis_period()

    prevail_obj = PrevailingTemperature(outdoor_temp, True)
    assert isinstance(prevail_obj.hourly_prevailing_temperature, HourlyContinuousCollection)
    assert len(prevail_obj.hourly_prevailing_temperature.values) == 8760
    assert isinstance(prevail_obj.daily_prevailing_temperature, DailyCollection)
    assert len(prevail_obj.daily_prevailing_temperature.values) == 365
    assert isinstance(prevail_obj.monthly_prevailing_temperature, MonthlyCollection)
    assert len(prevail_obj.monthly_prevailing_temperature.values) == 12
    assert isinstance(prevail_obj.monthly_per_hour_prevailing_temperature, MonthlyPerHourCollection)
    assert len(prevail_obj.monthly_per_hour_prevailing_temperature.values) == 288

    prevail_obj = PrevailingTemperature(outdoor_temp, False)
    assert isinstance(prevail_obj.hourly_prevailing_temperature, HourlyContinuousCollection)
    assert len(prevail_obj.hourly_prevailing_temperature.values) == 8760
    assert isinstance(prevail_obj.daily_prevailing_temperature, DailyCollection)
    assert len(prevail_obj.daily_prevailing_temperature.values) == 365
    assert isinstance(prevail_obj.monthly_prevailing_temperature, MonthlyCollection)
    assert len(prevail_obj.monthly_prevailing_temperature.values) == 12
    assert isinstance(prevail_obj.monthly_per_hour_prevailing_temperature, MonthlyPerHourCollection)
    assert len(prevail_obj.monthly_per_hour_prevailing_temperature.values) == 288


def test_init_prevailing_temperature_monthly():
    """Test the PrevailingTemperature object with monthly inputs."""
    outdoor_header = Header(Temperature(), 'C', AnalysisPeriod())
    outdoor_temp = MonthlyCollection(outdoor_header, range(12), AnalysisPeriod().months_int)
    outdoor_temp = outdoor_temp.validate_analysis_period()

    prevail_obj = PrevailingTemperature(outdoor_temp, True)
    assert isinstance(prevail_obj.hourly_prevailing_temperature, HourlyContinuousCollection)
    assert len(prevail_obj.hourly_prevailing_temperature.values) == 8760
    assert isinstance(prevail_obj.daily_prevailing_temperature, DailyCollection)
    assert len(prevail_obj.daily_prevailing_temperature.values) == 365
    assert isinstance(prevail_obj.monthly_prevailing_temperature, MonthlyCollection)
    assert len(prevail_obj.monthly_prevailing_temperature.values) == 12
    assert isinstance(prevail_obj.monthly_per_hour_prevailing_temperature, MonthlyPerHourCollection)
    assert len(prevail_obj.monthly_per_hour_prevailing_temperature.values) == 288

    with pytest.raises(Exception):
        prevail_obj = PrevailingTemperature(outdoor_temp, False)
