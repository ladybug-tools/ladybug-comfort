# coding utf-8

import unittest
import pytest

from ladybug_comfort.collection.pmv import PMV
from ladybug_comfort.parameter.pmv import PMVParameter

from ladybug_comfort.pmv import predicted_mean_vote, fanger_pmv, \
    pierce_set, ppd_from_pmv, pmv_from_ppd, calc_missing_pmv_input

from ladybug.analysisperiod import AnalysisPeriod
from ladybug.header import Header
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.epw import EPW

from ladybug.datatype.temperature import Temperature
from ladybug.datatype.fraction import RelativeHumidity
from ladybug.datatype.speed import AirSpeed
from ladybug.datatype.energyflux import MetabolicRate
from ladybug.datatype.rvalue import ClothingInsulation


class PMVTestCase(unittest.TestCase):
    """Test PMV calculation from single set of values"""

    def test_fanger_pmv(self):
        """Test the fanger_pmv function"""
        pmv_comf, ppd, hl = fanger_pmv(19, 23, 0.1, 60, 1.5, 0.4)
        assert pmv_comf == pytest.approx(-0.680633, rel=1e-2)
        assert ppd == pytest.approx(14.7373, rel=1e-2)
        assert hl['cond'] == pytest.approx(11.60697, rel=1e-2)
        assert hl['sweat'] == pytest.approx(12.2115, rel=1e-2)
        assert hl['res_l'] == pytest.approx(6.7457, rel=1e-2)
        assert hl['res_s'] == pytest.approx(1.8317, rel=1e-2)
        assert hl['rad'] == pytest.approx(26.63829, rel=1e-2)
        assert hl['conv'] == pytest.approx(44.745778, rel=1e-2)
        assert sum(hl.values()) == pytest.approx(103.78, rel=1e-2)

    def test_pierce_set(self):
        """Test the pierce_set function"""
        set = pierce_set(19, 23, 0.5, 60, 1.5, 0.4)
        assert set == pytest.approx(18.8911, rel=1e-2)

    def test_predicted_mean_vote(self):
        """Test the pmv function"""
        result = predicted_mean_vote(19, 23, 0.5, 60, 1.5, 0.4)
        assert result['pmv'] == pytest.approx(-1.6745, rel=1e-2)
        assert round(result['ppd']) == pytest.approx(60.382974, rel=1e-2)
        assert result['set'] == pytest.approx(18.8911, rel=1e-2)

    def test_ppd_from_pmv(self):
        """Test the ppd_from_pmv function"""
        ppd = ppd_from_pmv(-0.5)
        assert ppd == pytest.approx(10, rel=1e-1)
        ppd = ppd_from_pmv(-1)
        assert ppd == pytest.approx(26, rel=1e-1)

    def test_pmv_from_ppd(self):
        """Test the pmv_from_ppd function"""
        pmv_lower, pmv_upper = pmv_from_ppd(10)
        assert pmv_lower == pytest.approx(-0.5, rel=1e-1)
        assert pmv_upper == pytest.approx(0.5, rel=1e-1)
        pmv_lower, pmv_upper = pmv_from_ppd(26)
        assert pmv_lower == pytest.approx(-1, rel=1e-1)
        assert pmv_upper == pytest.approx(1, rel=1e-1)

    def test_calc_missing_pmv_input(self):
        """Test the calc_missing_pmv_input function"""
        input_1 = {'ta': None, 'tr': 20, 'vel': 0.05, 'rh': 50,
                   'met': 1.2, 'clo': 0.75, 'wme': 0}
        input_2 = {'ta': 20, 'tr': None, 'vel': 0.05, 'rh': 50,
                   'met': 1.2, 'clo': 0.75, 'wme': 0}
        input_3 = {'ta': 22, 'tr': 22, 'vel': None, 'rh': 50,
                   'met': 1.2, 'clo': 0.75, 'wme': 0}
        input_4 = {'ta': 20, 'tr': 20, 'vel': 0.05, 'rh': None,
                   'met': 1.2, 'clo': 0.75, 'wme': 0}
        input_5 = {'ta': 20, 'tr': 20, 'vel': 0.05, 'rh': 50,
                   'met': None, 'clo': 0.75, 'wme': 0}
        input_6 = {'ta': 20, 'tr': 20, 'vel': 0.05, 'rh': 50,
                   'met': 1.2, 'clo': None, 'wme': 0}
        input_7 = {'ta': 20, 'tr': 20, 'vel': 0.05, 'rh': 50,
                   'met': 1.4, 'clo': 0.75, 'wme': None}
        updated_input_1 = calc_missing_pmv_input(-1, input_1)
        updated_input_2 = calc_missing_pmv_input(-1, input_2)
        updated_input_3 = calc_missing_pmv_input(-1, input_3, up_bound=1)
        updated_input_4 = calc_missing_pmv_input(-1, input_4)
        updated_input_5 = calc_missing_pmv_input(-1, input_5, up_bound=1)
        updated_input_6 = calc_missing_pmv_input(-1, input_6, up_bound=1)
        updated_input_7 = calc_missing_pmv_input(-1, input_7, up_bound=1)
        assert updated_input_1['ta'] == pytest.approx(18.529, rel=1e-1)
        assert updated_input_2['tr'] == pytest.approx(17.912, rel=1e-1)
        assert updated_input_3['vel'] == pytest.approx(0.720, rel=1e-1)
        assert updated_input_4['rh'] == pytest.approx(7.0, rel=1e-1)
        assert updated_input_5['met'] == pytest.approx(1.1234, rel=1e-2)
        assert updated_input_6['clo'] == pytest.approx(0.6546, rel=1e-2)
        assert updated_input_7['wme'] == pytest.approx(0.3577, rel=1e-2)

    def test_pmv_parameter(self):
        """Test PMVParameter."""
        ppd_comfort_thresh = 20
        humid_ratio_up = 0.012
        humid_ratio_low = 0.004
        still_air_thresh = 0.2

        pmv_comf = PMVParameter(
            ppd_comfort_thresh, humid_ratio_up, humid_ratio_low, still_air_thresh)

        assert pmv_comf.ppd_comfort_thresh == ppd_comfort_thresh
        assert pmv_comf.humid_ratio_upper == humid_ratio_up
        assert pmv_comf.humid_ratio_lower == humid_ratio_low
        assert pmv_comf.still_air_threshold == still_air_thresh

    def test_pmv_parameter_invalid(self):
        """Test PMVParameter for invalid inputs."""
        ppd_comfort_thresh = 110
        humid_ratio_up = 12
        humid_ratio_low = -1
        still_air_thresh = -1

        with pytest.raises(AssertionError):
            PMVParameter(ppd_comfort_thresh=ppd_comfort_thresh)
        with pytest.raises(AssertionError):
            PMVParameter(humid_ratio_upper=humid_ratio_up)
        with pytest.raises(AssertionError):
            PMVParameter(humid_ratio_lower=humid_ratio_low)
        with pytest.raises(AssertionError):
            PMVParameter(still_air_threshold=still_air_thresh)

    def test_comfort_check(self):
        """Test comfort check on PMVParameter."""
        pmv_comf = PMVParameter()
        comf_test = pmv_comf.is_comfortable(13, 0.01)
        assert comf_test is 0
        comf_test = pmv_comf.is_comfortable(7, 0.01)
        assert comf_test is 1

    def test_thermal_condition_check(self):
        """Test the thermal condition check on PMVParameter."""
        pmv_comf = PMVParameter()
        condition_test = pmv_comf.thermal_condition(-1, 20)
        assert condition_test == -1
        condition_test = pmv_comf.thermal_condition(0, 5)
        assert condition_test == 0

    def test_discomfort_reason_check(self):
        """Test the thermal condition check on PMVParameter."""
        pmv_comf = PMVParameter()
        condition_test = pmv_comf.discomfort_reason(-1, 20, 0.01)
        assert condition_test == -1
        condition_test = pmv_comf.discomfort_reason(0, 5, 0.01)
        assert condition_test == 0

    def test_init_pmv_collection(self):
        """Test the initialization of the PMV collection and basic outputs."""
        calc_length = 24
        air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
        air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
        pmv_obj = PMV(air_temp, 50)

        assert pmv_obj.comfort_model == 'Predicted Mean Vote'
        assert pmv_obj.calc_length == calc_length
        assert pmv_obj._hr_calculated is False
        assert pmv_obj._hr_comfort_required is False
        str(pmv_obj)  # test that the string representaiton is ok

        assert isinstance(pmv_obj.air_temperature, HourlyContinuousCollection)
        assert len(pmv_obj.air_temperature.values) == calc_length
        assert pmv_obj.air_temperature[0] == 24
        assert isinstance(pmv_obj.rel_humidity, HourlyContinuousCollection)
        assert len(pmv_obj.rel_humidity.values) == calc_length
        assert pmv_obj.rel_humidity[0] == 50

        assert isinstance(pmv_obj.predicted_mean_vote, HourlyContinuousCollection)
        assert len(pmv_obj.predicted_mean_vote.values) == calc_length
        assert pmv_obj.predicted_mean_vote[0] == pytest.approx(-0.053570216, rel=1e-3)
        assert isinstance(pmv_obj.percentage_people_dissatisfied, HourlyContinuousCollection)
        assert len(pmv_obj.percentage_people_dissatisfied.values) == calc_length
        assert pmv_obj.percentage_people_dissatisfied[0] == pytest.approx(5.0594, rel=1e-3)
        assert isinstance(pmv_obj.standard_effective_temperature, HourlyContinuousCollection)
        assert len(pmv_obj.standard_effective_temperature.values) == calc_length
        assert pmv_obj.standard_effective_temperature[0] == pytest.approx(24.9656, rel=1e-3)

    def test_pmv_collection_defaults(self):
        """Test the default inputs assigned to the PMV collection."""
        calc_length = 24
        air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
        air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
        pmv_obj = PMV(air_temp, 50)

        assert isinstance(pmv_obj.rad_temperature, HourlyContinuousCollection)
        assert len(pmv_obj.rad_temperature.values) == calc_length
        assert pmv_obj.rad_temperature[0] == pmv_obj.air_temperature[0]

        assert isinstance(pmv_obj.air_speed, HourlyContinuousCollection)
        assert len(pmv_obj.air_speed.values) == calc_length
        assert pmv_obj.air_speed[0] == 0.1

        assert isinstance(pmv_obj.met_rate, HourlyContinuousCollection)
        assert len(pmv_obj.met_rate.values) == calc_length
        assert pmv_obj.met_rate[0] == 1.1

        assert isinstance(pmv_obj.clo_value, HourlyContinuousCollection)
        assert len(pmv_obj.clo_value.values) == calc_length
        assert pmv_obj.clo_value[0] == 0.7

        assert isinstance(pmv_obj.external_work, HourlyContinuousCollection)
        assert len(pmv_obj.external_work.values) == calc_length
        assert pmv_obj.external_work[0] == 0

        assert isinstance(pmv_obj.comfort_parameter, PMVParameter)
        default_par = PMVParameter()
        assert pmv_obj.comfort_parameter.ppd_comfort_thresh == default_par.ppd_comfort_thresh
        assert pmv_obj.comfort_parameter.humid_ratio_upper == default_par.humid_ratio_upper
        assert pmv_obj.comfort_parameter.humid_ratio_lower == default_par.humid_ratio_lower
        assert pmv_obj.comfort_parameter.still_air_threshold == default_par.still_air_threshold

    def test_pmv_collection_comfort_outputs(self):
        """Test the is_comfortable and thermal_condition outputs of the PMV collection."""
        calc_length = 24
        air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
        air_temp = HourlyContinuousCollection(air_temp_header, range(20, 20 + calc_length))
        pmv_obj = PMV(air_temp, 50)

        assert isinstance(pmv_obj.is_comfortable, HourlyContinuousCollection)
        assert len(pmv_obj.is_comfortable.values) == calc_length
        assert pmv_obj.is_comfortable[0] == 0
        assert pmv_obj.is_comfortable[5] == 1
        assert pmv_obj.is_comfortable[10] == 0

        assert isinstance(pmv_obj.thermal_condition, HourlyContinuousCollection)
        assert len(pmv_obj.thermal_condition.values) == calc_length
        assert pmv_obj.thermal_condition[0] == -1
        assert pmv_obj.thermal_condition[5] == 0
        assert pmv_obj.thermal_condition[10] == 1

        assert isinstance(pmv_obj.discomfort_reason, HourlyContinuousCollection)
        assert len(pmv_obj.discomfort_reason.values) == calc_length
        assert pmv_obj.discomfort_reason[0] == -1
        assert pmv_obj.discomfort_reason[5] == 0
        assert pmv_obj.discomfort_reason[10] == 1

    def test_pmv_collection_heat_loss_outputs(self):
        """Test the heat loss outputs of the PMV collection."""
        calc_length = 24
        air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
        air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
        pmv_obj = PMV(air_temp, 50, air_speed=0.5)

        assert isinstance(pmv_obj.adjusted_air_temperature, HourlyContinuousCollection)
        assert len(pmv_obj.adjusted_air_temperature.values) == calc_length
        assert pmv_obj.adjusted_air_temperature[0] == pytest.approx(21.914306, rel=1e-3)

        assert isinstance(pmv_obj.cooling_effect, HourlyContinuousCollection)
        assert len(pmv_obj.cooling_effect.values) == calc_length
        assert pmv_obj.cooling_effect[0] == pytest.approx(2.08569, rel=1e-3)

        assert isinstance(pmv_obj.heat_loss_conduction, HourlyContinuousCollection)
        assert len(pmv_obj.heat_loss_conduction.values) == calc_length
        assert pmv_obj.heat_loss_conduction[0] == pytest.approx(12.11224, rel=1e-3)

        assert isinstance(pmv_obj.heat_loss_sweating, HourlyContinuousCollection)
        assert len(pmv_obj.heat_loss_sweating.values) == calc_length
        assert pmv_obj.heat_loss_sweating[0] == pytest.approx(2.4423, rel=1e-3)

        assert isinstance(pmv_obj.heat_loss_latent_respiration, HourlyContinuousCollection)
        assert len(pmv_obj.heat_loss_latent_respiration.values) == calc_length
        assert pmv_obj.heat_loss_latent_respiration[0] == pytest.approx(4.950239787, rel=1e-3)

        assert isinstance(pmv_obj.heat_loss_dry_respiration, HourlyContinuousCollection)
        assert len(pmv_obj.heat_loss_dry_respiration.values) == calc_length
        assert pmv_obj.heat_loss_dry_respiration[0] == pytest.approx(1.0822859, rel=1e-3)

        assert isinstance(pmv_obj.heat_loss_radiation, HourlyContinuousCollection)
        assert len(pmv_obj.heat_loss_radiation.values) == calc_length
        assert pmv_obj.heat_loss_radiation[0] == pytest.approx(28.49618812, rel=1e-3)

        assert isinstance(pmv_obj.heat_loss_convection, HourlyContinuousCollection)
        assert len(pmv_obj.heat_loss_convection.values) == calc_length
        assert pmv_obj.heat_loss_convection[0] == pytest.approx(26.0219599, rel=1e-3)

    def test_pmv_collection_humidity_ratio_outputs(self):
        """Test the humudity ratio outputs of the PMV collection."""
        calc_length = 24
        air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
        air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
        pmv_obj = PMV(air_temp, 90)

        assert isinstance(pmv_obj.humidity_ratio, HourlyContinuousCollection)
        assert len(pmv_obj.humidity_ratio.values) == calc_length
        assert pmv_obj.humidity_ratio[0] == pytest.approx(0.01694444, rel=1e-5)

        hr_par = PMVParameter(humid_ratio_upper=0.012)
        pmv_obj = PMV(air_temp, 90, comfort_parameter=hr_par)
        assert pmv_obj._hr_calculated is True
        assert pmv_obj._hr_comfort_required is True

        assert pmv_obj.humidity_ratio[0] == pytest.approx(0.01694444, rel=1e-5)
        assert pmv_obj.is_comfortable[0] == 0
        assert pmv_obj.thermal_condition[0] == 0
        assert pmv_obj.discomfort_reason[0] == 2

    def test_pmv_collection_immutability(self):
        """Test that the PMV collection is immutable."""
        calc_length = 24
        air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
        air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
        pmv_obj = PMV(air_temp, 50)

        # check that editing the original collection does not mutate the object
        air_temp[0] = 26
        assert pmv_obj.air_temperature[0] == 24

        # check that editing collection properties does not mutate the object
        with pytest.raises(Exception):
            pmv_obj.air_temperature[0] = 26
        with pytest.raises(Exception):
            pmv_obj.air_temperature.values = [26] * calc_length
        with pytest.raises(Exception):
            pmv_obj.predicted_mean_vote[0] = 0.5
        with pytest.raises(Exception):
            pmv_obj.predicted_mean_vote.values = [0.5] * calc_length
        pmv_obj.comfort_parameter.ppd_comfort_thresh = 15
        assert pmv_obj.comfort_parameter.ppd_comfort_thresh == 10

        # check that properties cannot be edited directly
        with pytest.raises(Exception):
            pmv_obj.air_temperature = air_temp
        with pytest.raises(Exception):
            pmv_obj.predicted_mean_vote = air_temp
        with pytest.raises(Exception):
            pmv_obj.comfort_parameter = PMVParameter()

    def test_init_pmv_collection_full_input(self):
        """Test the initialization of the PMV collection will all inputs."""
        calc_length = 24
        air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
        air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
        custom_par = PMVParameter(15, 0.012, 0.004, 0.2)
        pmv_obj = PMV(air_temp, 50, 22, 0.5, 1.2, 0.85, 0.1, custom_par)

        assert pmv_obj.air_temperature[0] == 24
        assert pmv_obj.rel_humidity[0] == 50
        assert pmv_obj.rad_temperature[0] == 22
        assert pmv_obj.air_speed[0] == 0.5
        assert pmv_obj.met_rate[0] == 1.2
        assert pmv_obj.clo_value[0] == 0.85
        assert pmv_obj.external_work[0] == 0.1
        assert pmv_obj.comfort_parameter.ppd_comfort_thresh == 15
        assert pmv_obj.comfort_parameter.humid_ratio_upper == 0.012
        assert pmv_obj.comfort_parameter.humid_ratio_lower == 0.004
        assert pmv_obj.comfort_parameter.still_air_threshold == 0.2

    def test_init_pmv_collection_full_collection_input(self):
        """Test initialization of the PMV collection will all inputs as collections."""
        calc_length = 24
        air_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
        air_temp = HourlyContinuousCollection(air_temp_header, [24] * calc_length)
        rel_humid_header = Header(RelativeHumidity(), '%', AnalysisPeriod(end_month=1, end_day=1))
        rel_humid = HourlyContinuousCollection(rel_humid_header, [50] * calc_length)
        rad_temp_header = Header(Temperature(), 'C', AnalysisPeriod(end_month=1, end_day=1))
        rad_temp = HourlyContinuousCollection(rad_temp_header, [22] * calc_length)
        air_speed_header = Header(AirSpeed(), 'm/s', AnalysisPeriod(end_month=1, end_day=1))
        air_speed = HourlyContinuousCollection(air_speed_header, [0.5] * calc_length)
        met_header = Header(MetabolicRate(), 'met', AnalysisPeriod(end_month=1, end_day=1))
        met_rate = HourlyContinuousCollection(met_header, [1.2] * calc_length)
        clo_header = Header(ClothingInsulation(), 'clo', AnalysisPeriod(end_month=1, end_day=1))
        clo_level = HourlyContinuousCollection(clo_header, [0.85] * calc_length)
        work_header = Header(MetabolicRate(), 'met', AnalysisPeriod(end_month=1, end_day=1))
        ext_work = HourlyContinuousCollection(work_header, [0.1] * calc_length)

        pmv_obj = PMV(air_temp, rel_humid, rad_temp, air_speed, met_rate, clo_level, ext_work)

        assert pmv_obj.air_temperature[0] == 24
        assert pmv_obj.rel_humidity[0] == 50
        assert pmv_obj.rad_temperature[0] == 22
        assert pmv_obj.air_speed[0] == 0.5
        assert pmv_obj.met_rate[0] == 1.2
        assert pmv_obj.clo_value[0] == 0.85
        assert pmv_obj.external_work[0] == 0.1

    def test_init_pmv_collection_epw(self):
        """Test the initialization of the PMV collection with EPW input."""
        calc_length = 8760
        relative_path = './tests/epw/chicago.epw'
        epw = EPW(relative_path)
        pmv_obj = PMV(epw.dry_bulb_temperature, epw.relative_humidity)

        assert len(pmv_obj.air_temperature.values) == calc_length
        assert pmv_obj.air_temperature[0] == -6.1
        assert len(pmv_obj.rel_humidity.values) == calc_length
        assert pmv_obj.rel_humidity[0] == 81

        assert len(pmv_obj.predicted_mean_vote.values) == calc_length
        assert pmv_obj.predicted_mean_vote[0] == pytest.approx(-8.70793209, rel=1e-3)
        assert len(pmv_obj.percentage_people_dissatisfied.values) == calc_length
        assert pmv_obj.percentage_people_dissatisfied[0] == pytest.approx(100.0, rel=1e-1)
        assert len(pmv_obj.standard_effective_temperature.values) == calc_length
        assert pmv_obj.standard_effective_temperature[0] == pytest.approx(-3.7553724, rel=1e-3)

    def test_pmv_collection_comfort_percent_outputs(self):
        """Test the percent outputs of the PMV collection."""
        relative_path = './tests/epw/chicago.epw'
        epw = EPW(relative_path)
        pmv_obj = PMV(epw.dry_bulb_temperature, epw.relative_humidity,
                      met_rate=2.4, clo_value=1)

        assert pmv_obj.percent_comfortable == pytest.approx(18.961187, rel=1e-3)
        assert pmv_obj.percent_uncomfortable == pytest.approx(81.0388127, rel=1e-3)
        assert pmv_obj.percent_neutral == pytest.approx(18.961187, rel=1e-3)
        assert pmv_obj.percent_hot == pytest.approx(38.6415525, rel=1e-3)
        assert pmv_obj.percent_cold == pytest.approx(42.39726027, rel=1e-3)
        assert pmv_obj.percent_dry == 0.0
        assert pmv_obj.percent_humid == 0.0


if __name__ == "__main__":
    unittest.main()
