# coding=utf-8
"""Object for calculating Adaptive comfort from DataCollections."""
from __future__ import division

from ..adaptive import adaptive_comfort_ashrae55, adaptive_comfort_en15251,
    weighted_running_mean_hourly, weighted_running_mean_daily
from ..parameter.adaptive import AdaptiveParameter
from ._base import ComfortDataCollection

from ladybug._datacollectionbase import BaseCollection

from ladybug.datatype.temperature import Temperature, MeanRadiantTemperature, \
    OperativeTemperature
from ladybug.datatype.percentage import RelativeHumidity, ThermalComfort
from ladybug.datatype.speed import Speed, AirSpeed
from ladybug.datatype.thermalcondition import ThermalCondition


class UTCI(ComfortDataCollection):
    """UTCI comfort DataCollection object.

    Properties:
        air_temperature
        rad_temperature
        air_speed
        comfort_parameter
        degrees_from_neutral
        is_comfortable
        thermal_condition
        percent_comfortable
        percent_uncomfortable
        percent_neutral
        percent_hot
        percent_cold
    """
    _model = 'Adaptive'

    def __init__(self, air_temperature, rel_humidity, rad_temperature=None,
                 wind_speed=None, comfort_parameter=None):
        """Initialize a UTCI comfort object from DataCollections of UTCI inputs.

        Args:
            air_temperature: Data Collection of air temperature values in Celcius.
            rel_humidity: Data Collection of relative humidity values in % or a
                single relative humdity value to be used for the whole analysis.
            rad_temperature: Data Collection of mean radiant temperature (MRT)
                values in degrees Celcius or a single MRT value to be used for the whole
                analysis. If None, this will be the same as the air_temperature.
            wind_speed: Data Collection of meteorological wind speed values in m/s
                (measured 10 m above the ground) or a single wind speed value to be
                used for the whole analysis. If None, this will default to a very
                low wind speed of 0.1 m/s.
            comfort_parameter: Optional UTCIParameter object to specify parameters under
                which conditions are considered acceptable. If None, default will
                assume comfort thresholds consistent with those used by meterologists
                to categorize outdoor conditions.
        """
        # check required inputs
        assert isinstance(air_temperature, BaseCollection), 'air_temperature must be a' \
            ' Data Collection. Got {}'.format(type(air_temperature))
        self._air_temperature = self._check_datacoll(
            air_temperature, Temperature, 'C', 'air_temperature')
        self._calc_length = len(self._air_temperature.values)
