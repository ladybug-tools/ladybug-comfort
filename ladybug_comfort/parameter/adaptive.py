# coding=utf-8
"""Parameters for specifying acceptable thermal conditions using the Adaptive model."""
from __future__ import division
import re

from ._base import ComfortParameter
from ..adaptive import neutral_temperature_conditioned, \
    ashrae55_neutral_offset_from_ppd, en15251_neutral_offset_from_comfort_class


class AdaptiveParameter(ComfortParameter):
    """Parameters of Adaptive comfort.

    Args:
        ashrae_or_en: A boolean to note whether to use the ASHRAE-55 neutral
            temperature function (True) or the european neutral function (False),
            which is consistent with both EN-15251 and EN-16798. Note that this
            input will also determine default values for many of the other
            properties of this object.
        neutral_offset:  The number of degrees Celsius from the neutral temperature
            where the input operative temperature is considered acceptable.
            The default is 2.5C when the neutral temperature function is ASHRAE-55
            and 3C when the neutral temperature function is EN, which is consistent
            with comfort class II. You may want to use the set_neutral_offset_from_ppd()
            or the set_neutral_offset_from_comfort_class() methods on this object to
            set this value using ppd from the ASHRAE-55 standard or comfort classes
            from the EN standard respectively.
        avg_month_or_running_mean: A boolean to note whether the prevailing outdoor
            temperature is computed from the average monthly temperature (True) or
            a weighted running mean of the last week (False).  The default is True
            when the neutral temperature function is ASHRAE-55 and False when the
            neutral temperature function is EN.
        discrete_or_continuous_air_speed: A boolean to note whether discrete
            categories should be used to assess the effect of elevated air speed
            (True) or whether a continuous function should be used (False).
            Note that continuous air speeds were only used in the older EN-15251
            standard and are not a part of the more recent EN-16798 standard.
            When unassigned, this will be True for discrete air speeds.
        cold_prevail_temp_limit: A number indicating the prevailing outdoor
            temperature below which acceptable indoor operative temperatures
            flat line. The default is 10C, which is consistent with both ASHRAE-55 and
            EN-16798. However, 15C was used for the older EN-15251 standard.
            This number cannot be greater than 22C and cannot be less than 10C.
        conditioning: A number between 0 and 1 that represents how "conditioned" vs.
            "free-running" the building is.

            * 0 = free-running (completely passive with no air conditioning)
            * 1 = conditioned (no operable windows and fully air conditioned)

            The default is 0 since both the ASHRAE-55 and EN standards prohibit
            the use of adaptive comfort methods when a cooling system is active.

    Properties:
        * ashrae_or_en
        * neutral_offset
        * avg_month_or_running_mean
        * discrete_or_continuous_air_speed
        * cold_prevail_temp_limit
        * conditioning
        * standard
        * prevailing_temperature_method
        * minimum_operative
    """
    _model = 'Adaptive'
    __slots__ = ('_standard', '_neutral_offset', '_prevail_method', '_air_speed_method',
                 '_cold_prevail_temp_limit', '_conditioning', '_min_operative')

    def __init__(self, ashrae_or_en=None, neutral_offset=None,
                 avg_month_or_running_mean=None, discrete_or_continuous_air_speed=None,
                 cold_prevail_temp_limit=None, conditioning=None):
        """Initialize Adaptive Parameters.
        """
        # get the standard
        self._standard = ashrae_or_en if ashrae_or_en is not None else True
        assert isinstance(self._standard, bool), 'ashrae_or_en must be '\
            'a boolean. Got {}'.format(type(self._standard))

        # set defaults based on the standard
        default_air_speed_method = True
        default_cold_prevail_temp_limit = 10
        if self._standard:
            default_neutral_offset = 2.5
            default_prevail_method = True
        else:
            default_neutral_offset = 3
            default_prevail_method = False

        # assign properties based on defaults and input
        self._prevail_method = avg_month_or_running_mean if \
            avg_month_or_running_mean is not None else default_prevail_method
        self._air_speed_method = discrete_or_continuous_air_speed if \
            discrete_or_continuous_air_speed is not None else default_air_speed_method
        self._cold_prevail_temp_limit = cold_prevail_temp_limit if \
            cold_prevail_temp_limit is not None else default_cold_prevail_temp_limit
        self._conditioning = conditioning if conditioning is not None else 0

        # perform range checks on the inputs
        assert 10 <= self._cold_prevail_temp_limit <= 22, \
            'cold_prevail_temp_limit must be between 10 and 22. Got {}'.format(
                self._cold_prevail_temp_limit)
        assert 0 <= self._conditioning <= 1, \
            'conditioning must be between 0 and 1. Got {}'.format(self._conditioning)

        # assign the neutral temperature offset
        self.neutral_offset = neutral_offset if \
            neutral_offset is not None else default_neutral_offset

    @classmethod
    def from_dict(cls, data):
        """Create a AdaptiveParameter object from a dictionary.

        Args:
            data: A AdaptiveParameter dictionary in following the format below.

        .. code-block:: python

            {
            'type': 'AdaptiveParameter',
            'ashrae_or_en': True,
            'neutral_offset': 2.5,
            'avg_month_or_running_mean': False,
            'discrete_or_continuous_air_speed': True,
            'cold_prevail_temp_limit': 10,
            'conditioning': 0
            }
        """
        assert data['type'] == 'AdaptiveParameter', \
            'Expected AdaptiveParameter dictionary. Got {}.'.format(data['type'])
        ashrae_or_en = data['ashrae_or_en'] if \
            'ashrae_or_en' in data else None
        neutral_offset = data['neutral_offset'] if \
            'neutral_offset' in data else None
        avg_month_or_running_mean = data['avg_month_or_running_mean'] if \
            'avg_month_or_running_mean' in data else None
        discrete_or_continuous_air_speed = data['discrete_or_continuous_air_speed'] if \
            'discrete_or_continuous_air_speed' in data else None
        cold_prevail_temp_limit = data['cold_prevail_temp_limit'] if \
            'cold_prevail_temp_limit' in data else None
        conditioning = data['conditioning'] if \
            'conditioning' in data else None
        return cls(ashrae_or_en, neutral_offset, avg_month_or_running_mean,
                   discrete_or_continuous_air_speed, cold_prevail_temp_limit,
                   conditioning)

    @classmethod
    def from_string(cls, adaptive_parameter_string):
        """Create an AdaptiveParameter object from an AdaptiveParameter string."""
        str_pattern = re.compile(r"\-\-(\S*\s\S*)")
        matches = str_pattern.findall(adaptive_parameter_string)
        par_dict = {item.split(' ')[0]: item.split(' ')[1] for item in matches}
        ashrae55 = True if 'standard' not in par_dict \
            or par_dict['standard'].upper() == 'ASHRAE-55' else False
        offset = float(par_dict['neutral-offset']) \
            if 'neutral-offset' in par_dict else None
        avg_month = None
        if 'prevail-method' in par_dict:
            avg_month = True if par_dict['prevail-method'].lower() == 'averagedmonthly' \
                else False
        spd_method = None
        if 'air-speed-method' in par_dict:
            spd_method = True if par_dict['air-speed-method'].lower() == 'discrete' \
                else False
        cold_limit = float(par_dict['cold-limit']) \
            if 'cold-limit' in par_dict else None
        conditioning = float(par_dict['conditioning']) \
            if 'conditioning' in par_dict else None
        return cls(ashrae55, offset, avg_month, spd_method, cold_limit, conditioning)

    @property
    def ashrae_or_en(self):
        """A boolean to note whether to use the ASHRAE-55 neutral temperature
        function (True) or the EN function (False)."""
        return self._standard

    @property
    def neutral_offset(self):
        """The degrees Celsius from the neutral temperature where the operative
        temperature is considered acceptable."""
        return self._neutral_offset

    @neutral_offset.setter
    def neutral_offset(self, offset):
        assert 0 < offset <= 10, \
            'neutral_offset must be between 0 and 10 C. Got {}'.format(offset)
        self._neutral_offset = offset
        self._calc_min_operative_temperature()

    @property
    def avg_month_or_running_mean(self):
        """Boolean noting whether prevailing outdoor temperature is computed from the
        average monthly temperature (True) or a weighted running mean (False)."""
        return self._prevail_method

    @property
    def discrete_or_continuous_air_speed(self):
        """Boolean noting whether discrete categories are used to assess elevated
        air speed (True) or whether a continuous function is used (False)."""
        return self._air_speed_method

    @property
    def cold_prevail_temp_limit(self):
        """The prevailing outdoor temperature below which acceptable indoor
        operative temperatures flat line. [C]"""
        return self._cold_prevail_temp_limit

    @property
    def conditioning(self):
        """A decimal noting how conditioned(1) vs. free-running(0) the building is."""
        return self._conditioning

    @property
    def standard(self):
        """Text denoting the standard.

        Either 'ASHRAE-55' or 'EN-16798'
        """
        if self._standard is True:
            return 'ASHRAE-55'
        else:
            return 'EN-16798'

    @property
    def prevailing_temperature_method(self):
        """Text denoting prevailing temperature method.

        Either 'Averaged Monthly' or 'Running Mean'.
        """
        if self._prevail_method is True:
            return 'AveragedMonthly'
        else:
            return 'RunningMean'

    @property
    def air_speed_method(self):
        """Text denoting the type of function used for the cooling effect of air speed.

        Either 'Discrete' or 'Continuous'.
        """
        if self._air_speed_method is True:
            return 'Discrete'
        else:
            return 'Continuous'

    @property
    def minimum_operative(self):
        """Operative Temperature in C below which conditions cannot be comfortable."""
        return self._min_operative

    def set_neutral_offset_from_ppd(self, ppd):
        """Set the offset from neutral temperature given the ASHRAE-55 PPD limit."""
        self.neutral_offset = ashrae55_neutral_offset_from_ppd(ppd)

    def set_neutral_offset_from_comfort_class(self, comfort_class):
        """Set the offset from neutral temperature given the EN comfort class."""
        self.neutral_offset = en15251_neutral_offset_from_comfort_class(comfort_class)

    def is_comfortable(self, comfort_result, cooling_effect=0):
        """Determine if conditions are comfortable or not.

        Values are one of the following:

        * 0 = uncomfortable
        * 1 = comfortable

        Args:
            comfort_result: An adaptive comfort result dictionary from the
                adaptive_comfort_ashrae55 or adaptive_comfort_en15251 functions.
            cooling_effect: Cooling effect from elevated air speed.
        """
        if self._standard:
            return 1 if (comfort_result['to'] >= self._min_operative and
                        comfort_result['deg_comf'] >= -self.neutral_offset and
                        comfort_result['deg_comf'] <= self.neutral_offset +
                        cooling_effect) else 0
        else:  # lower threshold of EN-16798 is 1 degree cooler than upper threshold
            return 1 if (comfort_result['to'] >= self._min_operative and
                        comfort_result['deg_comf'] >= -self.neutral_offset - 1 and
                        comfort_result['deg_comf'] <= self.neutral_offset +
                        cooling_effect) else 0

    def thermal_condition(self, comfort_result, cooling_effect=0):
        """Determine whether conditions are cold, neutral or hot.

        Values are one of the following:

        * -1 = cold
        * 0 = neutral
        * +1 = hot

        Args:
            comfort_result: An adaptive comfort result dictionary from the
                adaptive_comfort_ashrae55 or adaptive_comfort_en15251 functions.
            cooling_effect: Cooling effect from elevated air speed
        """
        if self.is_comfortable(comfort_result, cooling_effect) == 0:
            return 1 if comfort_result['deg_comf'] > 0 else -1
        else:
            return 0

    def to_dict(self):
        """AdaptiveParameter dictionary representation."""
        return {
            'type': 'AdaptiveParameter',
            'ashrae_or_en': self.ashrae_or_en,
            'neutral_offset': self.neutral_offset,
            'avg_month_or_running_mean': self.avg_month_or_running_mean,
            'discrete_or_continuous_air_speed': self.discrete_or_continuous_air_speed,
            'cold_prevail_temp_limit': self.cold_prevail_temp_limit,
            'conditioning': self.conditioning
        }

    def __copy__(self):
        return AdaptiveParameter(self.ashrae_or_en, self.neutral_offset,
                                 self.avg_month_or_running_mean,
                                 self.discrete_or_continuous_air_speed,
                                 self.cold_prevail_temp_limit, self.conditioning)

    def _calc_min_operative_temperature(self):
        """Set operative temperature below which conditions cannot be comfortable."""
        self._min_operative = neutral_temperature_conditioned(
            self._cold_prevail_temp_limit, self._conditioning, self.standard) \
            - self._neutral_offset

    def __repr__(self):
        """Adaptive comfort parameters representation."""
        return '--standard {} --neutral-offset {} ' \
            '--prevail-method {} --air-speed-method {} ' \
            '--cold-limit {} --conditioning {}'.format(
                self.standard, self.neutral_offset, self.prevailing_temperature_method,
                self.air_speed_method, self.cold_prevail_temp_limit, self.conditioning)
