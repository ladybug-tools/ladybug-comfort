# coding=utf-8
"""Object for calculating PMV comfort from DataCollections."""
from __future__ import division

from ..pmv import predicted_mean_vote
from ..parameter.pmv import PMVParameter
from ._base import ComfortCollection

from ladybug._datacollectionbase import BaseCollection
from ladybug.psychrometrics import humid_ratio_from_db_rh

from ladybug.datatype.temperature import Temperature, MeanRadiantTemperature, \
    StandardEffectiveTemperature, AirTemperature
from ladybug.datatype.fraction import RelativeHumidity, HumidityRatio, \
    PercentagePeopleDissatisfied
from ladybug.datatype.speed import Speed, AirSpeed
from ladybug.datatype.energyflux import MetabolicRate
from ladybug.datatype.rvalue import ClothingInsulation
from ladybug.datatype.thermalcondition import PredictedMeanVote, \
    ThermalComfort, ThermalCondition, DiscomfortReason
from ladybug.datatype.temperaturedelta import AirTemperatureDelta
from ladybug.datatype.power import Power

try:
    from itertools import izip as zip  # python 2
except ImportError:
    pass


class PMV(ComfortCollection):
    """PMV comfort DataCollection object.

    Properties:
        air_temperature
        rad_temperature
        air_speed
        rel_humidity
        met_rate
        clo_value
        external_work
        comfort_parameter
        predicted_mean_vote
        percentage_people_dissatisfied
        standard_effective_temperature
        is_comfortable
        thermal_condition
        discomfort_reason
        percent_comfortable
        percent_uncomfortable
        percent_neutral
        percent_hot
        percent_cold
        percent_dry
        percent_humid
        humidity_ratio
        adjusted_air_temperature
        cooling_effect
        heat_loss_conduction
        heat_loss_sweating
        heat_loss_latent_respiration
        heat_loss_dry_respiration
        heat_loss_radiation
        heat_loss_convection
    """
    _model = 'Predicted Mean Vote'

    def __init__(self, air_temperature, rel_humidity,
                 rad_temperature=None, air_speed=None,
                 met_rate=None, clo_value=None, external_work=None,
                 comfort_parameter=None):
        """Initialize a PMV comfort object from DataCollections of PMV inputs.

        Args:
            air_temperature: Data Collection of air temperature values in Celcius.
            rel_humidity: Data Collection of relative humidity values in % or a
                single relative humdity value to be used for the whole analysis.
            rad_temperature: Data Collection of mean radiant temperature (MRT)
                values in degrees Celcius or a single MRT value to be used for the whole
                analysis. If None, this will be the same as the air_temperature.
            air_speed: Data Collection of air speed values in m/s or a single
                air_speed value to be used for the whole analysis. If None, this
                will default to 0.1 m/s.
            met_rate: Data Collection of metabolic rate in met or a single
                metabolic rate value to be used for the whole analysis. If None,
                default is set to 1.1 met (for seated, typing).
            clo_value: Data Collection of clothing values rate in clo or a single
                clothing value to be used for the whole analysis. If None, default is
                set to 0.7 clo (for long sleeve shirt and pants).
            external_work: Data Collection of external work in met or a single
                external work value to be used for the whole analysis. If None,
                default is set to 0 met.
            comfort_parameter: Optional PMVParameter object to specify parameters under
                which conditions are considered acceptable. If None, default will
                assume a PPD threshold of 10%, no absolute humidity constraints
                and a still air threshold of 0.1 m/s.
        """
        # set up the object using air temperature as a base
        self._check_datacoll(air_temperature, Temperature, 'C', 'air_temperature')
        self._input_collections = [air_temperature]
        self._calc_length = len(air_temperature.values)
        self._base_collection = air_temperature

        # check and set required inputs
        self._air_temperature = air_temperature.values
        self._rel_humidity = self._check_input(
            rel_humidity, RelativeHumidity, '%', 'rel_humidity')

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
                met_rate, MetabolicRate, 'met', 'met_rate')
        else:
            self._met_rate = [1.1] * self.calc_length

        if clo_value is not None:
            self._clo_value = self._check_input(
                clo_value, ClothingInsulation, 'clo', 'clo_value')
        else:
            self._clo_value = [0.7] * self.calc_length

        if external_work is not None:
            self._external_work = self._check_input(
                external_work, MetabolicRate, 'met', 'external_work')
        else:
            self._external_work = [0.] * self.calc_length

        # check that all input data collections are aligned.
        BaseCollection.are_collections_aligned(self._input_collections)

        # check comfort parameters
        if comfort_parameter is None:
            self._comfort_par = PMVParameter()
        else:
            assert isinstance(comfort_parameter, PMVParameter), 'comfort_parameter '\
                'must be a PMVParameter object. Got {}'.format(type(comfort_parameter))
            self._comfort_par = comfort_parameter

        # value to track whether humidity ratio has been computed
        self._hr_calculated = False
        self._hr_comfort_required = True
        if self.comfort_parameter.humid_ratio_lower == 0 and \
                self.comfort_parameter.humid_ratio_upper == 1:
            self._hr_comfort_required = False

        # calculate PMV
        self._calculate_pmv()

    def _calculate_humidity_ratio(self):
        """Compute the humidity ratio at each step of the Data Collection."""
        self._humidity_ratio = [humid_ratio_from_db_rh(db, rh) for db, rh in zip(
            self._air_temperature, self._rel_humidity)]
        self._hr_calculated = True

    def _calculate_pmv(self):
        """Compute PMV for each step of the Data Collection."""
        if self._hr_comfort_required is True:
            self._calculate_humidity_ratio()

        # empty properties to be caulculated
        self._pmv = []
        self._ppd = []
        self._set = []
        self._is_comfortable = []
        self._thermal_condition = []
        self._discomfort_reason = []
        self._ta_adj = []
        self._cooling_effect = []
        self._heat_loss_conduction = []
        self._heat_loss_sweating = []
        self._heat_loss_latent_respiration = []
        self._heat_loss_dry_respiration = []
        self._heat_loss_radiation = []
        self._heat_loss_convection = []

        # perform the PMV calculation
        for ta, tr, vel, rh, met, clo, wme, i in \
            zip(self._air_temperature, self._rad_temperature,
                self._air_speed, self._rel_humidity,
                self._met_rate, self._clo_value,
                self._external_work, range(self._calc_length)):
            result = predicted_mean_vote(ta, tr, vel, rh, met, clo, wme,
                                         self._comfort_par.still_air_threshold)
            self._pmv.append(result['pmv'])
            self._ppd.append(result['ppd'])
            self._set.append(result['set'])
            self._ta_adj.append(result['ta_adj'])
            self._cooling_effect.append(result['ce'])
            self._heat_loss_conduction.append(result['heat_loss']['cond'])
            self._heat_loss_sweating.append(result['heat_loss']['sweat'])
            self._heat_loss_latent_respiration.append(result['heat_loss']['res_l'])
            self._heat_loss_dry_respiration.append(result['heat_loss']['res_s'])
            self._heat_loss_radiation.append(result['heat_loss']['rad'])
            self._heat_loss_convection.append(result['heat_loss']['conv'])

            # determine whether conditions are acceptable
            condit = self._comfort_par.thermal_condition(
                result['pmv'], result['ppd'])
            if self._hr_comfort_required is True:
                hr = self._humidity_ratio[i]
                comf = self._comfort_par.is_comfortable(result['ppd'], hr)
                reason = self._comfort_par.discomfort_reason(
                    result['pmv'], result['ppd'], hr)
            else:
                comf = self._comfort_par.is_comfortable(result['ppd'])
                reason = self._comfort_par.discomfort_reason(
                    result['pmv'], result['ppd'])
            self._is_comfortable.append(comf)
            self._thermal_condition.append(condit)
            self._discomfort_reason.append(reason)

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
    def met_rate(self):
        """Data Collection of metabolic rate in met.

        1 met = Metabolic rate of a resting seated person
        1.2 met = Metabolic rate of a standing person
        2 met = Metabolic rate of a wlaking person
        If left blank, default is set to 1.1 met (for seated, typing).
        """
        return self._get_coll('_met_rate_coll', self._met_rate,
                              MetabolicRate, 'met')

    @property
    def clo_value(self):
        """Data Collection of clothing level of the human subject in clo.

        1 clo = Three-piece suit
        0.5 clo = Shorts + T-shirt
        0 clo = No clothing
        If left blank, default is set to 0.85 clo.
        """
        return self._get_coll('_clo_value_coll', self._clo_value,
                              ClothingInsulation, 'clo')

    @property
    def external_work(self):
        """Data Collection of the work done by the human subject in met."""
        return self._get_coll('_external_work_coll', self._external_work,
                              MetabolicRate, 'met')

    @property
    def comfort_parameter(self):
        """PMV comfort parameters that are assigned to this object."""
        return self._comfort_par.duplicate()  # duplicate since ppd_thresh is setable

    @property
    def predicted_mean_vote(self):
        """Data Collection of predicted mean vote (PMV) for the input conditions.

        PMV is a seven-point scale from cold (-3) to hot (+3) that was used in comfort
        surveys of P.O. Fanger.
        Each interger value of the scale indicates the following:
            -3 = Cold
            -2 = Cool
            -1 = Slightly Cool
             0 = Neutral
            +1 = Slightly Warm
            +2 = Warm
            +3 = Hot
        """
        return self._get_coll('_pmv_coll', self._pmv, PredictedMeanVote, 'PMV')

    @property
    def percentage_people_dissatisfied(self):
        """Data Collection of percentage of people dissatisfied (PPD) for the input conditions.

        Specifically, this is defined by the percent of people who would have
        a PMV beyond acceptable thresholds (typically <-0.5 and >+0.5).
        Note that, with the PMV model, the best possible PPD achievable is 5%
        and most standards aim to have a PPD below 10%.
        """
        return self._get_coll('_ppd_coll', self._ppd, PercentagePeopleDissatisfied, '%')

    @property
    def standard_effective_temperature(self):
        """Data Collection of standard effective temperature (SET) for the input conditions.

        These temperatures describe what the given input conditions "feel like" in
        relation to a standard environment of 50% relative humidity, <0.1 m/s average
        air speed, and mean radiant temperature equal to average air temperature, in
        which the total heat loss from the skin of an imaginary occupant with an activity
        level of 1.0 met and a clothing level of 0.6 clo is the same as that from a
        person in the actual environment.
        """
        return self._get_coll('_set_coll', self._set,
                              StandardEffectiveTemperature, 'C')

    @property
    def is_comfortable(self):
        """Data Collection of integers noting whether the input conditions are
        acceptable according to the assigned comfort_parameter.

        Values are one of the following:
            0 = uncomfortable
            1 = comfortable
        """
        return self._get_coll('_is_comfortable_coll', self._is_comfortable,
                              ThermalComfort, 'condition')

    @property
    def thermal_condition(self):
        """Data Collection of integers noting the thermal status of a subject
        according to the assigned comfort_parameter.

        Values are one of the following:
            -1 = cold
             0 = netural
            +1 = hot
        """
        return self._get_coll('_thermal_condition_coll', self._thermal_condition,
                              ThermalCondition, 'condition')

    @property
    def discomfort_reason(self):
        """Data Collection of integers noting the reason for discomfort
        according to the assigned comfort_parameter.

        Values are one of the following:
            -2 = too dry
            -1 = too cold
             0 = comfortable
            +1 = too hot
            +2 = too humid
        """
        return self._get_coll('_discomfort_reason_coll', self._discomfort_reason,
                              DiscomfortReason, 'condition')

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

    @property
    def percent_dry(self):
        """The percent of time that the thermal_condiiton neutral but it is too dry."""
        _vals = [1 for x in self._discomfort_reason if x == -2]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def percent_humid(self):
        """The percent of time that the thermal_condiiton neutral but it is too humid."""
        _vals = [1 for x in self._discomfort_reason if x == 2]
        return (sum(_vals) / self._calc_length) * 100

    @property
    def humidity_ratio(self):
        """Data Collection of humidity ratio for the dry bulb and relative humidity."""
        if self._hr_calculated is False:
            self._calculate_humidity_ratio()
        return self._get_coll('_humidity_ratio_coll', self._humidity_ratio,
                              HumidityRatio, 'fraction')

    @property
    def adjusted_air_temperature(self):
        """Data Collection of air temperatures that have been adjusted by the SET model
        to account for the effect of air speed [C].
        """
        return self._get_coll('_ta_adj_coll', self._ta_adj,
                              AirTemperature('Adjusted Air Temperature'), 'C')

    @property
    def cooling_effect(self):
        """Data Collection of the cooling effect of the air speed in degrees Celcius.

        This is the difference between the air temperature and the
        adjusted air temperature [C].
        """
        return self._get_coll('_cooling_effect_coll', self._cooling_effect,
                              AirTemperatureDelta('Cooling Effect'), 'C')

    @property
    def heat_loss_conduction(self):
        """Data Collection of heat loss by conduction in [W]."""
        return self._get_coll('_hl_conduction_coll', self._heat_loss_conduction,
                              Power('Heat Loss From Conduction'), 'W')

    @property
    def heat_loss_sweating(self):
        """Data Collection of heat loss by sweating in [W]."""
        return self._get_coll('_hl_sweating', self._heat_loss_sweating,
                              Power('Heat Loss From Sweating'), 'W')

    @property
    def heat_loss_latent_respiration(self):
        """Data Collection of heat loss by latent respiration in [W]."""
        return self._get_coll(
            '_hl_latent_respiration_coll', self._heat_loss_latent_respiration,
            Power('Heat Loss From Latent Respiration'), 'W')

    @property
    def heat_loss_dry_respiration(self):
        """Data Collection of heat loss by dry respiration in [W]."""
        return self._get_coll(
            '_hl_dry_respiration_coll', self._heat_loss_dry_respiration,
            Power('Heat Loss From Dry Respiration'), 'W')

    @property
    def heat_loss_radiation(self):
        """Data Collection of heat loss by radiation in [W]."""
        return self._get_coll('_hl_radiation_coll', self._heat_loss_radiation,
                              Power('Heat Loss From Radiation'), 'W')

    @property
    def heat_loss_convection(self):
        """Data Collection of heat loss by convection in [W]."""
        return self._get_coll('_hl_convection_coll', self._heat_loss_convection,
                              Power('Heat Loss From Convection'), 'W')
