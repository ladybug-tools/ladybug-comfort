# coding=utf-8
"""Object for calculating Adaptive comfort from DataCollections."""
from __future__ import division

from ..adaptive import adaptive_comfort_ashrae55, adaptive_comfort_en15251, \
    get_adaptive_comfort_conditioned_function, cooling_effect_ashrae55, \
    cooling_effect_en15251, get_operative_temperature, \
    weighted_running_mean_hourly, weighted_running_mean_daily
from ..parameter.adaptive import AdaptiveParameter
from ._base import ComfortDataCollection

from ladybug._datacollectionbase import BaseCollection
from ladybug.datacollection import HourlyContinuousCollection, DailyCollection, \
    MonthlyCollection, MonthlyPerHourCollection, HourlyDiscontinuousCollection
from ladybug.analysisperiod import AnalysisPeriod

from ladybug.datatype.temperature import Temperature, OperativeTemperature, \
    PrevailingOutdoorTemperature
from ladybug.datatype.speed import Speed, AirSpeed
from ladybug.datatype.thermalcondition import ThermalComfort, ThermalCondition
from ladybug.datatype.temperaturedelta import OperativeTemperatureDelta


class Adaptive(ComfortDataCollection):
    """Adaptive comfort DataCollection object.

    Properties:
        prevailing_outdoor_temperature
        operative_temperature
        air_speed
        comfort_parameter
        neutral_temperature
        degrees_from_neutral
        is_comfortable
        thermal_condition
        cooling_effect
        percent_comfortable
        percent_uncomfortable
        percent_neutral
        percent_hot
        percent_cold
    """
    _model = 'Adaptive'

    def __init__(self, outdoor_temperature, operative_temperature, air_speed=None,
                 comfort_parameter=None):
        """Initialize an Adaptive comfort object from DataCollections of inputs.

        Args:
            outdoor_temperature: Either one of the following inputs are acceptable:
                1 - A Data Collection of prevailing outdoor temperature values in C.
                    Such a Data Collection must align with the operative_temperature
                    input and bear the PrevailingOutdoorTemperature data type in
                    its header.
                2 - A single prevailing outdoor temperature value in C to be used
                    for all of the operative_temperature inputs below.
                3 - A Data Collection of actual outdoor temperatures recorded over
                    the entire year. This Data Collection must be continouous and
                    must either be an Hourly Collection or Daily Collection. In the event
                    that the input comfort_parameter has a prevailing_temperature_method
                    of 'Monthly', Monthly collections are also acceptable here. Note
                    that, because an annual input is required, this input collection
                    does not have to align with the operative_temperature input.
            operative_temperature: Data Collection of operative temperature (To)
                values in degrees Celcius.
            air_speed: Data Collection of air speed values in m/s or a single
                air_speed value to be used for the whole analysis. If None, this
                will default to 0.1 m/s.
            comfort_parameter: Optional AdaptiveParameter object to specify parameters
                under which conditions are considered acceptable. If None, default will
                assume ASHRAE-55 criteria.
        """
        # check operative_temperature
        assert isinstance(operative_temperature, BaseCollection), \
            'operative_temperature must be a' \
            ' Data Collection. Got {}'.format(type(operative_temperature))
        self._op_temp = self._check_datacoll(
            operative_temperature, Temperature, 'C', 'operative_temperature')
        self._calc_length = len(self._op_temp.values)
        self._base_collection = self._op_temp

        # check air_speed
        if air_speed is not None:
            self._air_speed = self._check_datacoll(air_speed, Speed, 'm/s', 'air_speed')
        else:
            self._air_speed = self._base_collection.get_aligned_collection(
                0.1, AirSpeed(), 'm/s')

        # check comfort parameters
        if comfort_parameter is None:
            self._comfort_par = AdaptiveParameter()
        else:
            assert isinstance(comfort_parameter, AdaptiveParameter), \
                'comfort_parameter must be an AdaptiveParameter object. '\
                'Got {}'.format(type(comfort_parameter))
            self._comfort_par = comfort_parameter

        # check outdoor_temperature
        self._o_temp = outdoor_temperature
        if isinstance(self._o_temp, BaseCollection) and not \
                isinstance(self._o_temp.header.data_type, PrevailingOutdoorTemperature):
            # it is a data collection of actual recorded outdoor temperatures
            prev_obj = PrevailingTemperature(
                self._o_temp, self._comfort_par.avg_month_or_running_mean)
            self._prevail_temp = prev_obj.get_aligned_prevailing(self._base_collection)
        else:
            # it is either a data collection or single value of prevailing temperature
            self._prevail_temp = self._check_datacoll(
                self._o_temp, PrevailingOutdoorTemperature, 'C', 'outdoor_temperature')

        # calculate Adaptive comfort
        self._calculate_adaptive()

    @classmethod
    def from_air_and_rad_temp(cls, outdoor_temperature, air_temperature,
                              rad_temperature=None, air_speed=None,
                              comfort_parameter=None):
        """Initalize an Adaptive Comfort object from air and radiant temperature."""
        if rad_temperature is None:
            to = air_temperature
        else:
            to = BaseCollection.compute_function_aligned(
                get_operative_temperature, [air_temperature, rad_temperature],
                OperativeTemperature(), 'C')
        return cls(outdoor_temperature, to, air_speed, comfort_parameter)

    def _calculate_adaptive(self):
        """Compute Adaptive comfort for each step of the Data Collection."""
        # empty properties to be caulculated
        self._neutral_temperature = []
        self._degrees_from_neutral = []
        self._is_comfortable = []
        self._thermal_condition = []
        self._cooling_effect = []

        # determine the comfort function to use
        if self._comfort_par.conditioning != 0:
            comf_funct = get_adaptive_comfort_conditioned_function(
                self._comfort_par.conditioning, self._comfort_par.standard)
        elif self._comfort_par.ashrae55_or_en15251 is True:
            comf_funct = adaptive_comfort_ashrae55
        else:
            comf_funct = adaptive_comfort_en15251

        # determine the cooling effect function to use
        if self._comfort_par.discrete_or_continuous_air_speed is True:
            cooling_funct = cooling_effect_ashrae55
        else:
            cooling_funct = cooling_effect_en15251

        # perform the Adaptive calculation
        if self._comfort_par.ashrae55_or_en15251 is True:
            for tp, to, vel in zip(self._prevail_temp, self._op_temp, self._air_speed):
                result = comf_funct(tp, to, self._comfort_par.conditioning)
                ce = cooling_funct(vel)
                comf = self._comfort_par.is_comfortable(result, ce)
                if comf is False:
                    condit = 1 if comf > 0 else -1
                else:
                    comf = 0
            self._neutral_temperature.append(result['t_comf'])
            self._degrees_from_neutral.append(result['deg_comf'])
            self._is_comfortable.append(comf)
            self._thermal_condition.append(condit)
            self._cooling_effect.append(ce)

    @property
    def prevailing_outdoor_temperature(self):
        """Data Collection of prevailing outdoor temperature in degrees C."""
        return self._prevail_temp.duplicate()

    @property
    def operative_temperature(self):
        """Data Collection of operative temperature in degrees C."""
        return self._op_temp.duplicate()

    @property
    def air_speed(self):
        """Data Collection of air speed in m/s."""
        return self._air_speed.duplicate()

    @property
    def comfort_parameter(self):
        """Adaptive comfort parameters that are assigned to this object."""
        return self._comfort_par.duplicate()

    @property
    def neutral_temperature(self):
        """Data Collection of the desired neutral temperature in degrees C."""
        return self._build_coll(self._neutral_temperature, OperativeTemperature(), 'C')

    @property
    def degrees_from_neutral(self):
        """Data Collection of the degrees from desired neutral temperature in C."""
        return self._build_coll(self._degrees_from_neutral,
                                OperativeTemperatureDelta(), 'C')

    @property
    def is_comfortable(self):
        """Data Collection of integers noting whether the input conditions are
        acceptable according to the assigned comfort_parameter.

        Values are one of the following:
            0 = uncomfortable
            1 = comfortable
        """
        return self._build_coll(self._is_comfortable, ThermalComfort(), 'condition')

    @property
    def thermal_condition(self):
        """Data Collection of integers noting the thermal status of a subject
        according to the assigned comfort_parameter.

        Values are one of the following:
            -1 = cold
             0 = netural
            +1 = hot
        """
        return self._build_coll(self._thermal_condition, ThermalCondition(), 'condition')

    @property
    def cooling_effect(self):
        """Data Collection of the cooling effect of the air speed in degrees Celcius.

        This is the difference between the air temperature and the
        adjusted air temperature [C].
        """
        return self._build_coll(self._cooling_effect, OperativeTemperatureDelta(), 'C')

    @property
    def percent_comfortable(self):
        """The percent of time comfortabe given by the assigned comfort_parameter."""
        return (sum(self._is_comfortable) / self._calc_length) * 100

    @property
    def percent_uncomfortable(self):
        """The percent of time uncomfortabe given by the assigned comfort_parameter."""
        return 100 - self.percent_comfortable

    @property
    def percent_neutral(self):
        """The percent of time that the thermal_condiiton is neutral."""
        _vals = [1 for x in self._thermal_condition if x == 0]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_cold(self):
        """The percent of time that the thermal_condiiton is cold."""
        _vals = [1 for x in self._thermal_condition if x == -1]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_hot(self):
        """The percent of time that the thermal_condiiton is hot."""
        _vals = [1 for x in self._thermal_condition if x == 1]
        return (sum(_vals) / self._calc_length) * 100


class PrevailingTemperature(object):
    """Determine prevailing temperature from annual DataCollections of outdoor temperature.

    Properties:
        outdoor_temperature
        avg_month_or_running_mean
        hourly_prevailing_temperature
        daily_prevailing_temperature
        monthly_prevailing_temperature
        monthly_per_hour_prevailing_temperature
    """

    def __init__(self, outdoor_temperature, avg_month_or_running_mean=True):
        """Initialize an prevailing temperature object from DataCollections of inputs.

        Args:
            outdoor_temperature: A Data Collection of outdoor temperatures recorded
                over an entire year. This Data Collection must be continouous and
                must either be an Hourly Collection or Daily Collection. In the event
                that the input avg_month_or_running_mean is True (for average monthly
                prevailing method), Monthly collections are also acceptable here.
            avg_month_or_running_mean: A boolean to note whether the prevailing outdoor
                temperature is computed from the average monthly temperature (True) or
                a weighted running mean of the last week (False).  The default is True.
        """
        # perform checks on the inputs
        self._o_temp = outdoor_temperature
        self._prevail_method = avg_month_or_running_mean
        acceptabe = (HourlyContinuousCollection, DailyCollection, MonthlyCollection)
        assert isinstance(self._o_temp, acceptabe), 'outdoor_temperature must be one ' \
            'of the following: {}.\n Got {}'.format(acceptabe, type(self._o_temp))
        self._head = self._o_temp.header
        assert isinstance(self._head.data_type, Temperature) and self._head.unit == 'C',\
            'outdoor_temperature must be Temperature in C. Got {} in {}'.format(
                self._head.data_type, self._head.unit)
        assert self._o_temp.is_continuous, 'outdoor_temperature must be continuous.'
        assert self._head.analysis_period.is_annual, 'outdoor_temperature must be annual'
        assert isinstance(self._prevail_method, bool), 'avg_month_or_running_mean' \
            ' must be a boolean. Got {}.'.format(type(self._prevail_method))

        # defaults to be calculated
        self._hourly_prevail = []
        self._daily_prevail = []
        self._monthly_prevail = []

        # calculate the base data of prevailing temperature
        if self._prevail_method is True:
            if isinstance(self._o_temp, (HourlyContinuousCollection, DailyCollection)):
                self._monthly_prevail = self._o_temp.average_monthly().values
            elif isinstance(self._o_temp, MonthlyCollection):
                self._monthly_prevail = self._o_temp.values
        else:
            if isinstance(self._o_temp, HourlyContinuousCollection):
                self._hourly_prevail = weighted_running_mean_hourly(self._o_temp.values)
            elif isinstance(self._o_temp, DailyCollection):
                self._daily_prevail = weighted_running_mean_daily(self._o_temp.values)
                for val in self._daily_prevail:
                    self._hourly_prevail.extend([val] * 24)
            else:
                raise TypeError('outdoor_temperature must be hourly or daily when '
                                'avg_month_or_running_mean is False.')

    @property
    def outdoor_temperature(self):
        """The input outdoor_temperature data collection."""
        return self._o_temp

    @property
    def avg_month_or_running_mean(self):
        """The input avg_month_or_running_mean."""
        return self._prevail_method

    @property
    def hourly_prevailing_temperature(self):
        """HourlyContinuousCollection of prevailing outdoor temperature in C."""
        if self._hourly_prevail == []:
            self._hourly_prevail_from_monthly()
        return HourlyContinuousCollection(self._get_header(), self._hourly_prevail)

    @property
    def daily_prevailing_temperature(self):
        """DailyCollection of prevailing outdoor temperature in C."""
        if self._daily_prevail == []:
            if self._prevail_method is True:
                self._daily_prevail_from_monthly()
            else:
                self._daily_prevail_from_hourly()
        return DailyCollection(self._get_header(), self._daily_prevail,
                               self._head.analysis_period.doys_int)

    @property
    def monthly_prevailing_temperature(self):
        """MonthlyCollection of prevailing outdoor temperature in C."""
        if self._monthly_prevail == []:
            return self.hourly_prevailing_temperature.average_monthly()
        else:
            return MonthlyCollection(self._get_header(), self._monthly_prevail,
                                     self._head.analysis_period.months_int)

    @property
    def monthly_per_hour_prevailing_temperature(self):
        """MonthlyPerHourCollection of prevailing outdoor temperature in C."""
        mon_per_hr_vals = []
        for val in self.monthly_prevailing_temperature:
            mon_per_hr_vals.extend([val] * 24)
        return MonthlyPerHourCollection(self._get_header(), mon_per_hr_vals,
                                        self._head.analysis_period.months_per_hour)

    def hourly_prevailing_temperature_timestep(self, timestep):
        """HourlyContinuousCollection of prevailing temperature at timestep."""
        if timestep != 1:
            hourly_coll = self.hourly_prevailing_temperature
            _new_values = []
            for val in hourly_coll.values:
                _new_values.extend([val] * timestep)
            a_per = hourly_coll.header.analysis_period
            _new_a_per = AnalysisPeriod(a_per.st_month, a_per.st_day, a_per.st_hour,
                                        a_per.end_month, a_per.end_day, a_per.end_hour,
                                        timestep, a_per.is_leap_year)
            _new_header = hourly_coll.header.duplicate()
            _new_header._analysis_period = _new_a_per
            return HourlyContinuousCollection(_new_header, _new_values)
        return self.hourly_prevailing_temperature

    def get_aligned_prevailing(self, collection):
        """"Get a Prevailing Temperature Collection aligned with input collection."""
        if isinstance(collection, HourlyContinuousCollection):
            new_coll = self.hourly_prevailing_temperature_timestep(
                collection.header.analysis_period.timestep)
            if not collection.header.analysis_period.is_annual:
                new_coll.filter_by_analysis_period(collection.header.analysis_period)
            return new_coll

        new_coll = collection.get_aligned_collection(
            data_type=PrevailingOutdoorTemperature(), unit='C')
        if isinstance(collection, HourlyDiscontinuousCollection):
            prevail_val_dict = self.hourly_prevailing_temperature_timestep(
                collection.header.analysis_period.timestep).moys_dict
            for i, datetime in enumerate(new_coll.datetimes):
                new_coll[i] = prevail_val_dict[datetime.moy]
        elif isinstance(collection, DailyCollection):
            daily_temps = self.daily_prevailing_temperature
            for i, datetime in enumerate(new_coll.datetimes):
                new_coll[i] = daily_temps[datetime - 1]
        elif isinstance(collection, MonthlyCollection):
            monthly_temps = self.monthly_prevailing_temperature
            for i, datetime in enumerate(new_coll.datetimes):
                new_coll[i] = monthly_temps[datetime - 1]
        elif isinstance(collection, MonthlyPerHourCollection):
            mon_per_hr = self.monthly_per_hour_prevailing_temperature
            monthly_per_hour_dict = {}
            for val, dt in zip(mon_per_hr.values, mon_per_hr.datetimes):
                monthly_per_hour_dict[dt] = val
            for i, datetime in enumerate(new_coll.datetimes):
                new_coll[i] = monthly_per_hour_dict[datetime]

        return new_coll

    def _hourly_prevail_from_monthly(self):
        for i, days in enumerate(self._head.analysis_period._num_of_days_each_month):
            self._hourly_prevail.extend(self._monthly_prevail[i] * days * 24)

    def _daily_prevail_from_monthly(self):
        for i, days in enumerate(self._head.analysis_period._num_of_days_each_month):
            self._daily_prevail.extend(self._monthly_prevail[i] * days)

    def _daily_prevail_from_hourly(self):
        for i in range(0, len(self._hourly_prevail), 24):
            self._daily_prevail.append(self._hourly_prevail[i])

    def _get_header(self):
        new_header = self._head.duplicate()
        new_header._data_type = PrevailingOutdoorTemperature()
        return new_header
