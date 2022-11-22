# coding=utf-8
"""Object for calculating PET comfort from DataCollections."""
from __future__ import division

from ..pet import physiologic_equivalent_temperature, pet_category, \
    pet_category_humid, core_temperature_category
from ..parameter.pet import PETParameter
from .base import ComfortCollection
from .solarcal import OutdoorSolarCal

from ladybug._datacollectionbase import BaseCollection

from ladybug.datatype.temperature import Temperature, MeanRadiantTemperature, \
    PhysiologicalEquivalentTemperature, AirTemperature, OperativeTemperature, \
    CoreBodyTemperature, SkinTemperature, ClothingTemperature
from ladybug.datatype.fraction import Fraction, RelativeHumidity
from ladybug.datatype.speed import Speed, AirSpeed
from ladybug.datatype.energyflux import MetabolicRate, EnergyFlux
from ladybug.datatype.pressure import Pressure
from ladybug.datatype.rvalue import ClothingInsulation, RValue
from ladybug.datatype.thermalcondition import CoreTemperatureCategory, \
    ThermalComfort, ThermalCondition, ThermalConditionNinePoint

try:
    from itertools import izip as zip  # python 2
except ImportError:
    pass


class PET(ComfortCollection):
    """PET comfort DataCollection object.

    Args:
        air_temperature: Data Collection of air temperature values in Celsius.
        rel_humidity: Data Collection of relative humidity values in % or a
            single relative humidity value to be used for the whole analysis.
        rad_temperature: Data Collection of mean radiant temperature (MRT)
            values in degrees Celsius or a single MRT value to be used for the whole
            analysis. If None, this will be the same as the air_temperature.
        air_speed: Data Collection of air speed values in m/s or a single
            air_speed value to be used for the whole analysis. If None, this
            will default to 0.1 m/s.
        barometric_pressure: A value or data collection representing atmospheric
            pressure [Pa]. Default is to use air pressure at sea level (101,325 Pa).
        met_rate: Data Collection of metabolic rate in met or a single
            metabolic rate value to be used for the whole analysis. If None,
            default is set to 2.4 met (for walking).
        clo_value: Data Collection of clothing level in clo or a single clothing
            value to be used for the whole analysis. If None, default is
            set to 0.7 clo (for long sleeve shirt and pants).
        body_parameter: Optional PETParameter object to specify the body properties
            of the human subject. The default attempts to model as average of a
            human body as possible.

    Properties:
        * air_temperature
        * rad_temperature
        * air_speed
        * rel_humidity
        * barometric_pressure
        * met_rate
        * clo_value
        * body_parameter
        * physiologic_equivalent_temperature
        * core_body_temperature
        * skin_temperature
        * clothing_temperature
        * operative_temperature
        * is_comfortable
        * thermal_condition
        * pet_category
        * core_temperature_category
        * percent_comfortable
        * percent_uncomfortable
        * percent_neutral
        * percent_hot
        * percent_cold
    """
    _model = 'Physiological Equivalent Temperature'
    __slots__ = (
        '_air_temperature', '_rel_humidity', '_rad_temperature', '_air_speed',
        '_barometric_pressure', '_met_rate', '_clo_value', '_body_par', '_comf_func',
        '_pet', '_t_core', '_t_skin', '_t_clo', '_is_comfortable',
        '_thermal_condition', '_pet_cat', '_core_temp_cat',
        '_air_temperature_coll', '_rel_humidity_coll', '_rad_temperature_coll',
        '_air_speed_coll', '_barometric_pressure_coll', '_met_rate_coll',
        '_clo_value_coll', '_pet_coll', '_t_core_coll', '_t_skin_coll', '_t_clo_coll',
        '_is_comfortable_coll', '_thermal_condition_coll', '_pet_cat_coll',
        '_core_temp_cat_coll', '_to', '_to_coll')

    def __init__(self, air_temperature, rel_humidity,
                 rad_temperature=None, air_speed=None, barometric_pressure=None,
                 met_rate=None, clo_value=None, body_parameter=None):
        """Initialize a PET comfort object from DataCollections of PET inputs.
        """
        # set up the object using air temperature as a base
        self._check_datacoll(air_temperature, Temperature, 'C', 'air_temperature')
        self._input_collections = [air_temperature]
        self._calc_length = len(air_temperature.values)
        self._base_collection = air_temperature

        # check and set required inputs
        self._air_temperature = air_temperature.values
        self._rel_humidity = self._check_input(
            rel_humidity, Fraction, '%', 'rel_humidity')

        # check parameters with defaults
        if rad_temperature is not None:
            self._rad_temperature = self._check_input(
                rad_temperature, Temperature, 'C', 'rad_temperature')
        else:
            self._rad_temperature = self._air_temperature

        if air_speed is not None:
            self._air_speed = self._check_input(
                air_speed, Speed, 'm/s', 'air_speed')
        else:
            self._air_speed = [0.1] * self.calc_length

        if met_rate is not None:
            self._met_rate = self._check_input(
                met_rate, EnergyFlux, 'met', 'met_rate')
        else:
            self._met_rate = [2.4] * self.calc_length

        if clo_value is not None:
            self._clo_value = self._check_input(
                clo_value, RValue, 'clo', 'clo_value')
        else:
            self._clo_value = [0.7] * self.calc_length

        if barometric_pressure is not None:
            self._barometric_pressure = self._check_input(
                barometric_pressure, Pressure, 'Pa', 'barometric_pressure')
        else:
            self._barometric_pressure = [101325.] * self.calc_length

        # check that all input data collections are aligned.
        BaseCollection.are_collections_aligned(self._input_collections)

        # check comfort parameters
        if body_parameter is None:
            self._body_par = PETParameter()
        else:
            assert isinstance(body_parameter, PETParameter), 'body_parameter '\
                'must be a PETParameter object. Got {}'.format(type(body_parameter))
            self._body_par = body_parameter
        self._comf_func = pet_category_humid \
            if self._body_par.humid_acclimated else pet_category

        # calculate PET
        self._calculate_pet()

    @classmethod
    def from_epw(cls, epw, include_wind=True, include_sun=True, met_rate=None,
                 clo_value=None, body_parameter=None):
        """Get a PET comfort object from the conditions within an EPW file.

        Args:
            epw: A ladybug EPW object from which the PET object will be created.
            include_wind: Set to True to include the EPW wind speed in the calculation.
                Setting to False will assume a condition that is shielded from wind
                where the human experiences a very low wind speed of 0.1 m/s. If
                included, the wind speed at ground level will be assumed to be 2/3
                times the meteorological wind speed in the EPW (usually at 10 meters).
                This follows the standard assumed for UTCI. (Default: True to
                include wind).
            include_sun: Set to True to include the mean radiant temperature (MRT) delta
                from both shortwave solar falling directly on people and long wave
                radiant exchange with the sky. Setting to False will assume a shaded
                condition with MRT being equal to the EPW dry bulb temperature. When
                set to True, this calculation will assume no surrounding shade context,
                standing human geometry, and a solar horizontal angle relative to
                front of person (SHARP) of 135 degrees. A SHARP of 135 essentially
                assumes that a person typically faces their side or back to the
                sun to avoid glare. (Default: True to include sun).
            met_rate: Data Collection of metabolic rate in met or a single
                metabolic rate value to be used for the whole analysis. Default: 2.4 met
                (walking at 1 m/s, which is the same assumption used in UTCI).
            clo_value: Data Collection of clothing values rate in clo or a single
                clothing value to be used for the whole analysis. Default: 0.7 clo
                (long sleeve shirt and pants).
            body_parameter: Optional PETParameter object to specify the body properties
                of the human subject. The default attempts to model as average of a
                human body as possible.

        Returns:
            An object with data collections of the PET results as properties.

        Usage:

        .. code-block:: python

            from ladybug.epw import EPW
            from ladybug_comfort.collection.pet import PET

            epw_file_path = './tests/epw/chicago.epw'
            epw = EPW(epw_file_path)
            pet = PET.from_epw(epw, include_wind=True, include_sun=True)

            # 12 values for the average PET in each month
            a = pet.physiologic_equivalent_temperature.average_monthly_per_hour().values
            print(a)
        """
        # get wind input
        if include_wind is True:
            wind_speed = epw.wind_speed.duplicate()
            for i, spd in enumerate(wind_speed):
                wind_speed[i] = spd * (2 / 3)  # 2/3 is the conversion used by UTCI
        else:
            wind_speed = 0.1

        # get the mrt input
        if include_sun is True:
            solarcal_obj = OutdoorSolarCal(epw.location, epw.direct_normal_radiation,
                                           epw.diffuse_horizontal_radiation,
                                           epw.horizontal_infrared_radiation_intensity,
                                           epw.dry_bulb_temperature)
            mrt = solarcal_obj.mean_radiant_temperature
        else:
            mrt = epw.dry_bulb_temperature

        # check the met input
        met_rate = 2.4 if met_rate is None else met_rate

        # return the comfort object
        return cls(epw.dry_bulb_temperature, epw.relative_humidity, mrt, wind_speed,
                   epw.atmospheric_station_pressure, met_rate, clo_value, body_parameter)

    def _calculate_pet(self):
        """Compute PET for each step of the Data Collection."""
        self._setup_list_attributes()
        for ta, tr, vel, rh, met, clo, pr in \
            zip(self._air_temperature, self._rad_temperature,
                self._air_speed, self._rel_humidity,
                self._met_rate, self._clo_value, self._barometric_pressure):
            result = physiologic_equivalent_temperature(
                ta, tr, vel, rh, met, clo, self._body_par.age, self._body_par.sex,
                self._body_par.height, self._body_par.body_mass,
                self._body_par.posture, pr)
            self._append_results_to_lists(result)
            self._assess_comfort(result)

    def _setup_list_attributes(self):
        """Set empty lists for all data collection attributes on this object."""
        self._pet = []
        self._t_core = []
        self._t_skin = []
        self._t_clo = []
        self._to = []
        self._is_comfortable = []
        self._thermal_condition = []
        self._pet_cat = []
        self._core_temp_cat = []

    def _append_results_to_lists(self, result):
        """Append PET results from a dictionary to this object's lists."""
        self._pet.append(result['pet'])
        self._t_core.append(result['t_core'])
        self._t_skin.append(result['t_skin'])
        self._t_clo.append(result['t_clo'])

    def _assess_comfort(self, result):
        """Append determine whether conditions are acceptable from a result dict."""
        pet_cat = self._comf_func(result['pet'])
        t_core_cat = core_temperature_category(result['t_core'])
        comf = pet_cat == 0
        condit = 0
        if pet_cat < 0:
            condit = -1
        elif pet_cat > 0:
            condit = 1
        self._is_comfortable.append(comf)
        self._thermal_condition.append(condit)
        self._pet_cat.append(pet_cat)
        self._core_temp_cat.append(t_core_cat)

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
    def air_speed(self):
        """Data Collection of air speed values in m/s."""
        return self._get_coll('_air_speed_coll', self._air_speed,
                              AirSpeed, 'm/s')

    @property
    def rel_humidity(self):
        """Data Collection of relative humidity values in %."""
        return self._get_coll('_rel_humidity_coll', self._rel_humidity,
                              RelativeHumidity, '%')

    @property
    def barometric_pressure(self):
        """Data Collection of the barometric pressure in Pa."""
        return self._get_coll('_barometric_pressure_coll', self._barometric_pressure,
                              Pressure, 'Pa')

    @property
    def met_rate(self):
        """Data Collection of metabolic rate in met.

        * 1 met = Metabolic rate of a resting seated person
        * 1.2 met = Metabolic rate of a standing person
        * 2 met = Metabolic rate of a walking person
        """
        return self._get_coll('_met_rate_coll', self._met_rate,
                              MetabolicRate, 'met')

    @property
    def clo_value(self):
        """Data Collection of clothing level of the human subject in clo.

        * 1 clo = Three-piece suit
        * 0.5 clo = Shorts + T-shirt
        * 0 clo = No clothing
        """
        return self._get_coll('_clo_value_coll', self._clo_value,
                              ClothingInsulation, 'clo')

    @property
    def body_parameter(self):
        """PET body parameters that are assigned to this object."""
        return self._body_par

    @property
    def physiologic_equivalent_temperature(self):
        """Data Collection of physiologic equivalent temperature (PET).

        PET is a "feels like" temperature and is defined as the operative temperature
        of a reference environment that would cause the same physiological
        response in the human subject as the environment under study. That is, the
        same skin temperature and core body temperature.
        """
        return self._get_coll('_pet_coll', self._pet,
                              PhysiologicalEquivalentTemperature, 'C')

    @property
    def core_body_temperature(self):
        """Data Collection of core body temperature of the human subject."""
        return self._get_coll('_t_core_coll', self._t_core, CoreBodyTemperature, 'C')

    @property
    def skin_temperature(self):
        """Data Collection of skin temperature of the human subject."""
        return self._get_coll('_t_skin_coll', self._t_skin, SkinTemperature, 'C')

    @property
    def clothing_temperature(self):
        """Data Collection of clothing temperature of the human subject."""
        return self._get_coll('_t_clo_coll', self._t_clo, ClothingTemperature, 'C')

    @property
    def operative_temperature(self):
        """Data Collection of operative temperature in degrees C."""
        if len(self._to) == 0:
            self._to = [(ta + tr) / 2 for ta, tr in
                        zip(self._air_temperature, self._rad_temperature)]
        return self._get_coll('_to_coll', self._to, OperativeTemperature, 'C')

    @property
    def is_comfortable(self):
        """Data Collection of integers noting whether the input conditions are
        acceptable according to the assigned body_parameter.

        Values are one of the following:

        * 0 = uncomfortable
        * 1 = comfortable
        """
        return self._get_coll('_is_comfortable_coll', self._is_comfortable,
                              ThermalComfort, 'condition')

    @property
    def thermal_condition(self):
        """Data Collection of integers noting the thermal status of a subject
        according to the assigned body_parameter.

        Values are one of the following:

        * -1 = cold
        * 0 = netural
        * +1 = hot
        """
        return self._get_coll('_thermal_condition_coll', self._thermal_condition,
                              ThermalCondition, 'condition')

    @property
    def pet_category(self):
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
        return self._get_coll('_pet_cat_coll', self._pet_cat,
                              ThermalConditionNinePoint, 'condition')

    @property
    def core_temperature_category(self):
        """Data Collection of integers noting the classification of core body temperature.

        Values are one of the following:

        * -2 = Hypothermia
        * -1 = Cold
        * 0 = Normal
        * 1 = Hot
        * 2 = Hyperthermia
        """
        return self._get_coll('_core_temp_cat_coll', self._core_temp_cat,
                              CoreTemperatureCategory, 'condition')

    @property
    def percent_comfortable(self):
        """The percent of time comfortable given by the assigned body_parameter."""
        return (sum(self._is_comfortable) / self._calc_length) * 100

    @property
    def percent_uncomfortable(self):
        """The percent of time uncomfortable given by the assigned body_parameter."""
        return 100 - self.percent_comfortable

    @property
    def percent_neutral(self):
        """The percent of time that the thermal_condition is neutral."""
        _vals = [1 for x in self._thermal_condition if x == 0]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_cold(self):
        """The percent of time that the thermal_condition is cold."""
        _vals = [1 for x in self._thermal_condition if x == -1]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_hot(self):
        """The percent of time that the thermal_condition is hot."""
        _vals = [1 for x in self._thermal_condition if x == 1]
        return (sum(_vals) / self._calc_length) * 100
