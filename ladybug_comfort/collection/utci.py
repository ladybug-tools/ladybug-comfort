# coding=utf-8
"""Object for calculating UTCI comfort from DataCollections."""
from __future__ import division

from ..utci import universal_thermal_climate_index
from ..parameter.utci import UTCIParameter
from .base import ComfortCollection
from .solarcal import OutdoorSolarCal

from ladybug._datacollectionbase import BaseCollection

from ladybug.datatype.temperature import Temperature, MeanRadiantTemperature, \
    AirTemperature, UniversalThermalClimateIndex
from ladybug.datatype.fraction import Fraction, RelativeHumidity
from ladybug.datatype.speed import Speed, WindSpeed
from ladybug.datatype.thermalcondition import ThermalComfort, ThermalCondition, \
    ThermalConditionFivePoint, ThermalConditionSevenPoint, \
    ThermalConditionNinePoint, ThermalConditionElevenPoint, UTCICategory


class UTCI(ComfortCollection):
    """UTCI comfort DataCollection object.

    Args:
        air_temperature: Data Collection of air temperature values in Celsius.
        rel_humidity: Data Collection of relative humidity values in % or a
            single relative humidity value to be used for the whole analysis.
        rad_temperature: Data Collection of mean radiant temperature (MRT)
            values in degrees Celsius or a single MRT value to be used for the whole
            analysis. If None, this will be the same as the air_temperature.
        wind_speed: Data Collection of meteorological wind speed values in m/s
            (measured 10 m above the ground) or a single wind speed value to be
            used for the whole analysis. If None, this will default to a low
            wind speed of 0.5 m/s, which is the lowest input speed that is
            recommended for the UTCI model.
        comfort_parameter: Optional UTCIParameter object to specify parameters under
            which conditions are considered acceptable. If None, default will
            assume comfort thresholds consistent with those used by meteorologists
            to categorize outdoor conditions.

    Properties:
        * air_temperature
        * rad_temperature
        * air_speed
        * rel_humidity
        * comfort_parameter
        * universal_thermal_climate_index
        * is_comfortable
        * thermal_condition
        * thermal_condition_five_point
        * thermal_condition_seven_point
        * thermal_condition_nine_point
        * thermal_condition_eleven_point
        * original_utci_category
        * percent_comfortable
        * percent_uncomfortable
        * percent_neutral
        * percent_hot
        * percent_cold
        * percent_extreme_cold_stress
        * percent_very_strong_cold_stress
        * percent_strong_cold_stress
        * percent_moderate_cold_stress
        * percent_slight_cold_stress
        * percent_slight_heat_stress
        * percent_moderate_heat_stress
        * percent_strong_heat_stress
        * percent_very_strong_heat_stress
        * percent_extreme_heat_stress
    """
    _model = 'Universal Thermal Climate Index'
    __slots__ = ('_air_temperature', '_rel_humidity', '_rad_temperature', '_wind_speed',
                 '_comfort_par', '_utci', '_thermal_category', '_air_temperature_coll',
                 '_rel_humidity_coll', '_rad_temperature_coll', '_wind_speed_coll',
                 '_utci_coll', '_is_comfortable_coll', '_thermal_condition_coll',
                 '_five_point_coll', '_seven_point_coll', '_nine_point_coll',
                 '_eleven_point_coll', '_original_category_coll')

    def __init__(self, air_temperature, rel_humidity, rad_temperature=None,
                 wind_speed=None, comfort_parameter=None):
        """Initialize a UTCI comfort object from DataCollections of UTCI inputs.
        """
        # set up the object using air temperature as a base
        self._check_datacoll(air_temperature, Temperature, 'C', 'air_temperature')
        self._input_collections = [air_temperature]
        self._calc_length = len(air_temperature.values)
        self._base_collection = air_temperature

        # check required inputs
        self._air_temperature = air_temperature.values
        self._rel_humidity = self._check_input(
            rel_humidity, Fraction, '%', 'rel_humidity')

        # check inputs with defaults
        if rad_temperature is not None:
            self._rad_temperature = self._check_input(
                rad_temperature, Temperature, 'C', 'rad_temperature')
        else:
            self._rad_temperature = self._air_temperature

        if wind_speed is not None:
            self._wind_speed = self._check_input(
                wind_speed, Speed, 'm/s', 'air_speed')
        else:
            self._wind_speed = [0.5] * self.calc_length

        # check that all input data collections are aligned.
        BaseCollection.are_collections_aligned(self._input_collections)

        # check comfort parameters
        if comfort_parameter is None:
            self._comfort_par = UTCIParameter()
        else:
            assert isinstance(comfort_parameter, UTCIParameter), 'comfort_parameter '\
                'must be a UTCIParameter object. Got {}'.format(type(comfort_parameter))
            self._comfort_par = comfort_parameter

        # compute UTCI
        self._calculate_utci()

    @classmethod
    def from_epw(cls, epw, include_wind=True, include_sun=True,
                 utci_parameter=None):
        """Get a UTCI comfort object from the conditions within an EPW file.

        Args:
            epw: A ladybug EPW object from which the UTCI object will be created.
            include_wind: Set to True to include the EPW wind speed in the calculation.
                Setting to False will assume a condition that is shielded from
                wind where the human subject experiences a low wind speed of 0.5 m/s,
                which is the lowest input speed that is recommended for the UTCI
                model. Default: True to include wind.
            include_sun: Set to True to include the mean radiant temperature (MRT) delta
                from both shortwave solar falling directly on people and long wave
                radiant exchange with the sky. Setting to False will assume a shaded
                condition with MRT being equal to the EPW dry bulb temperature. When
                set to True, this calculation will assume no surrounding shade context,
                standing human geometry, and a solar horizontal angle relative to
                front of person (SHARP) of 135 degrees. A SHARP of 135 essentially
                assumes that a person typically faces their side or back to the sun
                to avoid glare. Default: True to include sun.
            utci_parameter: Optional UTCIParameter object to specify parameters under
                which conditions are considered acceptable. If None, default will
                assume comfort thresholds consistent with those used by meterologists
                to categorize outdoor conditions.

        Returns:
            A UTCI object with data collections of the results as properties.

        Usage:

        .. code-block:: python

            from ladybug.epw import EPW
            from ladybug_comfort.collection.utci import UTCI

            epw_file_path = './tests/epw/chicago.epw'
            epw = EPW(epw_file_path)
            utci_exposed = UTCI.from_epw(epw, include_wind=True, include_sun=True)
            utci_protected = UTCI.from_epw(epw, include_wind=False, include_sun=False)

            print(utci_exposed.percent_neutral)  # comfortable % with sun + wind
            print(utci_protected.percent_neutral)  # comfortable % without sun + wind
        """
        # Get wind and mrt inputs
        wind_speed = epw.wind_speed if include_wind is True else 0.5
        if include_sun is True:
            solarcal_obj = OutdoorSolarCal(epw.location, epw.direct_normal_radiation,
                                           epw.diffuse_horizontal_radiation,
                                           epw.horizontal_infrared_radiation_intensity,
                                           epw.dry_bulb_temperature)
            mrt = solarcal_obj.mean_radiant_temperature
        else:
            mrt = epw.dry_bulb_temperature

        # return the comfort object
        return cls(epw.dry_bulb_temperature, epw.relative_humidity, mrt, wind_speed,
                   utci_parameter)

    def _calculate_utci(self):
        """Compute UTCI for each step of the Data Collection."""
        self._utci = []
        self._thermal_category = []
        for ta, tr, vel, rh in \
            zip(self._air_temperature, self._rad_temperature,
                self._wind_speed, self._rel_humidity):
            result = universal_thermal_climate_index(ta, tr, vel, rh)
            self._utci.append(result)
            self._thermal_category.append(
                self._comfort_par.thermal_condition_eleven_point(result))

    @property
    def air_temperature(self):
        """Data Collection of air temperature values in degrees C."""
        return self._get_coll('_air_temperature_coll', self._air_temperature,
                              AirTemperature, 'C')

    @property
    def rad_temperature(self):
        """Data Collection of mean radiant temperature (MRT) values in degrees C."""
        return self._get_coll('_rad_temperature_coll', self._rad_temperature,
                              MeanRadiantTemperature, 'C')

    @property
    def wind_speed(self):
        """Data Collection of air speed values in m/s."""
        return self._get_coll('_wind_speed_coll', self._wind_speed,
                              WindSpeed, 'm/s')

    @property
    def rel_humidity(self):
        """Data Collection of relative humidity values in %."""
        return self._get_coll('_rel_humidity_coll', self._rel_humidity,
                              RelativeHumidity, '%')

    @property
    def comfort_parameter(self):
        """UTCI comfort parameters that are assigned to this object."""
        return self._comfort_par

    @property
    def universal_thermal_climate_index(self):
        """A Data Collection of Universal Thermal Climate Index (UTCI) in C."""
        return self._get_coll('_utci_coll', self._utci,
                              UniversalThermalClimateIndex, 'C')

    @property
    def is_comfortable(self):
        """Data Collection of integers noting whether the input conditions are
        acceptable according to the assigned comfort_parameter.

        Values are one of the following:

        * 0 = uncomfortable
        * 1 = comfortable
        """
        return self._get_coll('_is_comfortable_coll', self._comf_val_funct,
                              ThermalComfort, 'condition')

    @property
    def thermal_condition(self):
        """Data Collection of integers noting the thermal status of a subject
        according to the assigned comfort_parameter.

        Values are one of the following:

        * -1 = cold
        * 0 = netural
        * +1 = hot
        """
        return self._get_coll('_thermal_condition_coll', self._condit_val_funct,
                              ThermalCondition, 'condition')

    @property
    def thermal_condition_five_point(self):
        """Data Collection of integers noting the thermal status on a five-point scale.

        Values are one of the following:

        * -2 = strong/extreme cold stress
        * -1 = moderate cold stress
        * 0 = no thermal stress
        * +1 = moderate heat stress
        * +2 = strong/extreme heat stress
        """
        return self._get_coll('_five_point_coll', self._five_pt_funct,
                              ThermalConditionFivePoint, 'condition')

    @property
    def thermal_condition_seven_point(self):
        """Data Collection of integers noting the thermal status on a seven-point scale.

        Values are one of the following:

        * -3 = very strong/extreme cold stress
        * -2 = strong cold stress
        * -1 = moderate cold stress
        * 0 = no thermal stress
        * +1 = moderate heat stress
        * +2 = strong heat stress
        * +3 = very strong/extreme heat stress
        """
        return self._get_coll('_seven_point_coll', self._seven_pt_funct,
                              ThermalConditionSevenPoint, 'condition')

    @property
    def thermal_condition_nine_point(self):
        """Data Collection of integers noting the thermal status on a nine-point scale.

        Values are one of the following:

        * -4 = very strong/extreme cold stress
        * -3 = strong cold stress
        * -2 = moderate cold stress
        * -1 = slight cold stress
        * 0 = no thermal stress
        * +1 = slight heat stress
        * +2 = moderate heat stress
        * +3 = strong heat stress
        * +4 = very strong/extreme heat stress
        """
        return self._get_coll('_nine_point_coll', self._nine_pt_funct,
                              ThermalConditionNinePoint, 'condition')

    @property
    def thermal_condition_eleven_point(self):
        """Data Collection of integers noting the thermal status on an eleven-point scale.

        Values are one of the following:

        * -5 = extreme cold stress
        * -4 = very strong cold stress
        * -3 = strong cold stress
        * -2 = moderate cold stress
        * -1 = slight cold stress
        * 0 = no thermal stress
        * +1 = slight heat stress
        * +2 = moderate heat stress
        * +3 = strong heat stress
        * +4 = very strong heat stress
        * +5 = extreme heat stress
        """
        return self._get_coll('_eleven_point_coll', self._thermal_category,
                              ThermalConditionElevenPoint, 'condition')

    @property
    def original_utci_category(self):
        """Data Collection of integers noting the original UTCI assessment scale.

        Glossary of Terms for Thermal Physiology (2003).
        Journal of Thermal Biology 28, 75-106

        Values are one of the following:

        * 0 = extreme cold stress
        * 1 = very strong cold stress
        * 2 = strong cold stress
        * 3 = moderate cold stress
        * 4 = slight cold stress
        * 5 = no thermal stress
        * 6 = moderate heat stress
        * 7 = strong heat stress
        * 8 = strong heat stress
        * 9 = extreme heat stress
        """
        return self._get_coll('_original_category_coll', self._original_category_funct,
                              UTCICategory, 'condition')

    @property
    def percent_comfortable(self):
        """The percent of time comfortabe given by the assigned comfort_parameter."""
        _vals = [1 for t in self._thermal_category if t == 0]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_uncomfortable(self):
        """The percent of time uncomfortable given by the assigned comfort_parameter."""
        return 100 - self.percent_comfortable

    @property
    def percent_neutral(self):
        """The percent of time that the thermal_condition is neutral."""
        return self.percent_comfortable

    @property
    def percent_cold(self):
        """The percent of time that the thermal_condition is cold."""
        _vals = [1 for x in self._thermal_category if x < 0]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_hot(self):
        """The percent of time that the thermal_condition is hot."""
        _vals = [1 for x in self._thermal_category if x > 0]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_slight_cold_stress(self):
        """The percent of time that conditions have slight cold stress."""
        _vals = [1 for x in self._thermal_category if x == -1]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_moderate_cold_stress(self):
        """The percent of time that conditions have moderate cold stress."""
        _vals = [1 for x in self._thermal_category if x == -2]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_strong_cold_stress(self):
        """The percent of time that conditions have strong cold stress."""
        _vals = [1 for x in self._thermal_category if x == -3]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_very_strong_cold_stress(self):
        """The percent of time that conditions have very strong cold stress."""
        _vals = [1 for x in self._thermal_category if x == -4]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_extreme_cold_stress(self):
        """The percent of time that conditions have very strong cold stress."""
        _vals = [1 for x in self._thermal_category if x == -5]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_slight_heat_stress(self):
        """The percent of time that conditions have slight heat stress."""
        _vals = [1 for x in self._thermal_category if x == 1]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_moderate_heat_stress(self):
        """The percent of time that conditions have moderate heat stress."""
        _vals = [1 for x in self._thermal_category if x == 2]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_strong_heat_stress(self):
        """The percent of time that conditions have strong heat stress."""
        _vals = [1 for x in self._thermal_category if x == 3]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_very_strong_heat_stress(self):
        """The percent of time that conditions have very strong heat stress."""
        _vals = [1 for x in self._thermal_category if x == 4]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_extreme_heat_stress(self):
        """The percent of time that conditions have very strong heat stress."""
        _vals = [1 for x in self._thermal_category if x == 5]
        return (sum(_vals) / self._calc_length) * 100

    def _comf_val_funct(self):
        return [self._comfort_par.is_comfortable(t) for t in self._utci]

    def _condit_val_funct(self):
        return [self._comfort_par.thermal_condition(t) for t in self._utci]

    def _five_pt_funct(self):
        return [self._comfort_par.thermal_condition_five_point(t) for t in self._utci]

    def _seven_pt_funct(self):
        return [self._comfort_par.thermal_condition_seven_point(t) for t in self._utci]

    def _nine_pt_funct(self):
        return [self._comfort_par.thermal_condition_nine_point(t) for t in self._utci]

    def _original_category_funct(self):
        return [self._comfort_par.original_utci_category(t) for t in self._utci]
