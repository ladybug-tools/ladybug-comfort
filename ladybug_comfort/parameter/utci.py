# coding=utf-8
"""Parameters for specifying acceptable thermal conditions using the UTCI model."""
from __future__ import division
import re

from ._base import ComfortParameter


class UTCIParameter(ComfortParameter): 
    """Parameters of UTCI comfort.

    Args:
        cold_thresh:  UTCI temperature below which conditions
            represent cold stress [C]. Default: 9C.
        heat_thresh:  UTCI temperature above which conditions
            represent heat stress [C]. Default: 26C.
        extreme_cold_thresh:  UTCI temperature below which conditions
            represent extreme cold stress [C]. Default: -40C.
        very_strong_cold_thresh:  UTCI temperature below which conditions
            represent very strong cold stress [C]. Default: -27C.
        strong_cold_thresh:  UTCI temperature below which conditions
            represent strong cold stress [C]. Default: -13C.
        moderate_cold_thresh:  UTCI temperature below which conditions
            represent moderate cold stress [C]. Default: 0C.
        moderate_heat_thresh:  UTCI temperature above which conditions
            represent moderate heat stress [C]. Default: 28C.
        strong_heat_thresh:  UTCI temperature above which conditions
            represent strong heat stress [C]. Default: 32C.
        very_strong_heat_thresh:  UTCI temperature above which conditions
            represent very strong heat stress [C]. Default: 38C.
        extreme_heat_thresh:  UTCI temperature above which conditions
            represent extreme heat stress [C]. Default: 46C.

    Properties:
        * cold_thresh
        * heat_thresh
        * extreme_cold_thresh
        * very_strong_cold_thresh
        * strong_cold_thresh
        * moderate_cold_thresh
        * moderate_heat_thresh
        * strong_heat_thresh
        * very_strong_heat_thresh
        * extreme_heat_thresh
    """
    _model = 'Universal Thermal Climate Index'
    __slots__ = ('_cold_thresh', '_heat_thresh', '_extreme_cold_thresh',
                 '_very_strong_cold_thresh', '_strong_cold_thresh',
                 '_moderate_cold_thresh', '_moderate_heat_thresh', '_strong_heat_thresh',
                 '_very_strong_heat_thresh', '_extreme_heat_thresh')

    def __init__(self, cold_thresh=None, heat_thresh=None,
                 extreme_cold_thresh=None, very_strong_cold_thresh=None,
                 strong_cold_thresh=None,
                 moderate_cold_thresh=None, moderate_heat_thresh=None,
                 strong_heat_thresh=None,
                 very_strong_heat_thresh=None, extreme_heat_thresh=None):
        """Initialize UTCI Parameters.
        """

        self._cold_thresh = cold_thresh if cold_thresh is not None else 9
        self._heat_thresh = heat_thresh if heat_thresh is not None else 26

        self._extreme_cold_thresh = \
            extreme_cold_thresh if extreme_cold_thresh is not None else -40
        self._very_strong_cold_thresh = \
            very_strong_cold_thresh if very_strong_cold_thresh is not None else -27
        self._strong_cold_thresh = \
            strong_cold_thresh if strong_cold_thresh is not None else -13

        self._moderate_cold_thresh = \
            moderate_cold_thresh if moderate_cold_thresh is not None else 0
        self._moderate_heat_thresh = \
            moderate_heat_thresh if moderate_heat_thresh is not None else 28

        self._strong_heat_thresh = \
            strong_heat_thresh if strong_heat_thresh is not None else 32
        self._very_strong_heat_thresh = \
            very_strong_heat_thresh if very_strong_heat_thresh is not None else 38
        self._extreme_heat_thresh = \
            extreme_heat_thresh if extreme_heat_thresh is not None else 46

        assert self._extreme_cold_thresh <= self._very_strong_cold_thresh, \
            'extreme_strong_cold_thresh must be <= very_strong_cold_thresh'
        assert self._very_strong_cold_thresh <= self._strong_cold_thresh, \
            'very_strong_cold_thresh must be <= strong_cold_thresh'
        assert self._strong_cold_thresh <= self._moderate_cold_thresh, \
            'strong_cold_thresh must be <= moderate_cold_thresh'
        assert self._moderate_cold_thresh <= self._cold_thresh, \
            'moderate_cold_thresh must be <= cold_thresh'
        assert self._cold_thresh <= self._heat_thresh, \
            'cold_thresh must be <= heat_thresh'
        assert self._heat_thresh <= self._moderate_heat_thresh, \
            'heat_thresh must be <= moderate_heat_thresh'
        assert self._moderate_heat_thresh <= self._strong_heat_thresh, \
            'moderate_heat_thresh must be <= strong_heat_thresh'
        assert self._strong_heat_thresh <= self._very_strong_heat_thresh, \
            'strong_heat_thresh must be <= very_strong_heat_thresh'
        assert self._very_strong_heat_thresh <= self._extreme_heat_thresh, \
            'very_strong_heat_thresh must be <= extreme_heat_thresh'

    @classmethod
    def from_dict(cls, data):
        """Create a UTCIParameter object from a dictionary.

        Args:
            data: A UTCIParameter dictionary in following the format below.

        .. code-block:: python

            {
            'type': 'UTCIParameter',
            'cold_thresh': 9,
            'heat_thresh': 26,
            'extreme_cold_thresh': -40,
            'very_strong_cold_thresh': -27,
            'strong_cold_thresh': -13,
            'moderate_cold_thresh': 0,
            'moderate_heat_thresh': 28,
            'strong_heat_thresh': 32,
            'very_strong_heat_thresh': 38,
            'extreme_heat_thresh': 46
            }
        """
        assert data['type'] == 'UTCIParameter', \
            'Expected UTCIParameter dictionary. Got {}.'.format(data['type'])

        def _default_value(data, key):
            return data[key] if key in data else None

        cold_thresh = _default_value(data, 'cold_thresh')
        heat_thresh = _default_value(data, 'heat_thresh')
        extreme_cold_thresh = _default_value(data, 'extreme_cold_thresh')
        very_strong_cold_thresh = _default_value(data, 'very_strong_cold_thresh')
        strong_cold_thresh = _default_value(data, 'strong_cold_thresh')
        moderate_cold_thresh = _default_value(data, 'moderate_cold_thresh')
        moderate_heat_thresh = _default_value(data, 'moderate_heat_thresh')
        strong_heat_thresh = _default_value(data, 'strong_heat_thresh')
        very_strong_heat_thresh = _default_value(data, 'very_strong_heat_thresh')
        extreme_heat_thresh = _default_value(data, 'extreme_heat_thresh')
        return cls(
            cold_thresh, heat_thresh, extreme_cold_thresh, very_strong_cold_thresh,
            strong_cold_thresh, moderate_cold_thresh, moderate_heat_thresh,
            strong_heat_thresh, very_strong_heat_thresh, extreme_heat_thresh)

    @classmethod
    def from_string(cls, utci_parameter_string):
        """Create an UTCIParameter object from an PMVParameter string."""
        str_pattern = re.compile(r"\-\-(\S*\s\S*)")
        matches = str_pattern.findall(utci_parameter_string)
        par_dict = {item.split(' ')[0]: item.split(' ')[1] for item in matches}
        cold = float(par_dict['cold']) if 'cold' in par_dict else None
        heat = float(par_dict['heat']) if 'heat' in par_dict else None
        extreme_cold = float(par_dict['extreme-cold']) \
            if 'extreme-cold' in par_dict else None
        very_strong_cold = float(par_dict['very-strong-cold']) \
            if 'very-strong-cold' in par_dict else None
        strong_cold = float(par_dict['strong-cold']) \
            if 'strong-cold' in par_dict else None
        moderate_cold = float(par_dict['moderate-cold']) \
            if 'moderate-cold' in par_dict else None
        moderate_heat = float(par_dict['moderate-heat']) \
            if 'moderate-heat' in par_dict else None
        strong_heat = float(par_dict['strong-heat']) \
            if 'strong-heat' in par_dict else None
        very_strong_heat = float(par_dict['very-strong-heat']) \
            if 'very-strong-heat' in par_dict else None
        extreme_heat = float(par_dict['extreme-heat']) \
            if 'extreme-heat' in par_dict else None
        return cls(
            cold, heat, extreme_cold, very_strong_cold, strong_cold, moderate_cold,
            moderate_heat, strong_heat, very_strong_heat, extreme_heat)

    @property
    def cold_thresh(self):
        """UTCI temperature below which conditions represent cold stress [C].

        Default: 9C.
        """
        return self._cold_thresh

    @property
    def heat_thresh(self):
        """UTCI temperature above which conditions represent heat stress [C].

        Default: 26C.
        """
        return self._heat_thresh

    @property
    def extreme_cold_thresh(self):
        """UTCI temperature below which conditions represent extreme cold stress [C].

        Default: -40C.
        """
        return self._extreme_cold_thresh

    @property
    def very_strong_cold_thresh(self):
        """UTCI temperature below which conditions represent very strong cold stress [C].

        Default: -27C.
        """
        return self._very_strong_cold_thresh

    @property
    def strong_cold_thresh(self):
        """UTCI temperature below which conditions represent strong cold stress [C].

        Default: -13C.
        """
        return self._strong_cold_thresh

    @property
    def moderate_cold_thresh(self):
        """UTCI temperature below which conditions represent moderate cold stress [C].

        Default: 0C.
        """
        return self._moderate_cold_thresh

    @property
    def moderate_heat_thresh(self):
        """UTCI temperature above which conditions represent moderate heat stress [C].

        Default: 28C.
        """
        return self._moderate_heat_thresh

    @property
    def strong_heat_thresh(self):
        """UTCI temperature above which conditions represent strong heat stress [C].

        Default: 32C.
        """
        return self._strong_heat_thresh

    @property
    def very_strong_heat_thresh(self):
        """UTCI temperature above which conditions represent very strong heat stress [C].

        Default: 38C.
        """
        return self._very_strong_heat_thresh

    @property
    def extreme_heat_thresh(self):
        """UTCI temperature above which conditions represent extreme heat stress [C].

        Default: 46C.
        """
        return self._extreme_heat_thresh

    def is_comfortable(self, utci):
        """Determine if conditions are comfortable or not.

        Values are one of the following:
            0 = uncomfortable
            1 = comfortable
        """
        return 1 if (utci >= self._cold_thresh and utci <= self._heat_thresh) else 0

    def thermal_condition(self, utci):
        """Determine whether conditions are cold, neutral or hot.

        Values are one of the following:

        * -1 = cold
        * 0 = netural
        * +1 = hot
        """
        if utci < self._cold_thresh:
            return -1
        elif utci > self._heat_thresh:
            return 1
        else:
            return 0

    def thermal_condition_five_point(self, utci):
        """Determine the thermal condition on a five-point scale.

        Values are one of the following:

        * -2 = strong/extreme cold stress
        * -1 = moderate cold stress
        * 0 = no thermal stress
        * +1 = moderate heat stress
        * +2 = strong/extreme heat stress
        """
        if utci < self._strong_cold_thresh:
            return -2
        elif utci < self._cold_thresh:
            return -1
        elif utci > self._strong_heat_thresh:
            return 2
        elif utci > self._heat_thresh:
            return 1
        else:
            return 0

    def thermal_condition_seven_point(self, utci):
        """Determine the thermal condition on a seven-point scale.

        Values are one of the following:

        * -3 = very strong/extreme cold stress
        * -2 = strong cold stress
        * -1 = moderate cold stress
        * 0 = no thermal stress
        * +1 = moderate heat stress
        * +2 = strong heat stress
        * +3 = very strong/extreme heat stress
        """
        if utci < self._very_strong_cold_thresh:
            return -3
        elif utci < self._strong_cold_thresh:
            return -2
        elif utci < self._cold_thresh:
            return -1
        elif utci > self._very_strong_heat_thresh:
            return 3
        elif utci > self._strong_heat_thresh:
            return 2
        elif utci > self._heat_thresh:
            return 1
        else:
            return 0

    def thermal_condition_nine_point(self, utci):
        """Determine the thermal condition on a nine-point scale.

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
        if utci < self._very_strong_cold_thresh:
            return -4
        elif utci < self._strong_cold_thresh:
            return -3
        elif utci < self._moderate_cold_thresh:
            return -2
        elif utci < self._cold_thresh:
            return -1
        elif utci > self._very_strong_heat_thresh:
            return 4
        elif utci > self._strong_heat_thresh:
            return 3
        elif utci > self._moderate_heat_thresh:
            return 2
        elif utci > self._heat_thresh:
            return 1
        else:
            return 0

    def thermal_condition_eleven_point(self, utci):
        """Determine the thermal condition on an eleven-point scale.

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
        if utci < self._extreme_cold_thresh:
            return -5
        elif utci < self._very_strong_cold_thresh:
            return -4
        elif utci < self._strong_cold_thresh:
            return -3
        elif utci < self._moderate_cold_thresh:
            return -2
        elif utci < self._cold_thresh:
            return -1
        elif utci > self._extreme_heat_thresh:
            return 5
        elif utci > self._very_strong_heat_thresh:
            return 4
        elif utci > self._strong_heat_thresh:
            return 3
        elif utci > self._moderate_heat_thresh:
            return 2
        elif utci > self._heat_thresh:
            return 1
        else:
            return 0

    def original_utci_category(self, utci):
        """Determine the category according to the original UTCI assessment scale.

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
        if utci < self._extreme_cold_thresh:
            return 0
        elif utci < self._very_strong_cold_thresh:
            return 1
        elif utci < self._strong_cold_thresh:
            return 2
        elif utci < self._moderate_cold_thresh:
            return 3
        elif utci < self._cold_thresh:
            return 4
        elif utci > self._extreme_heat_thresh:
            return 9
        elif utci > self._very_strong_heat_thresh:
            return 8
        elif utci > self._strong_heat_thresh:
            return 7
        elif utci > self._heat_thresh:
            return 6
        else:
            return 5

    def to_dict(self):
        """UTCIParameter dictionary representation."""
        return {
            'type': 'UTCIParameter',
            'cold_thresh': self.cold_thresh,
            'heat_thresh': self.heat_thresh,
            'extreme_cold_thresh': self.extreme_cold_thresh,
            'very_strong_cold_thresh': self.very_strong_cold_thresh,
            'strong_cold_thresh': self.strong_cold_thresh,
            'moderate_cold_thresh': self.moderate_cold_thresh,
            'moderate_heat_thresh': self.moderate_heat_thresh,
            'strong_heat_thresh': self.strong_heat_thresh,
            'very_strong_heat_thresh': self.very_strong_heat_thresh,
            'extreme_heat_thresh': self.extreme_heat_thresh
        }

    def __copy__(self):
        return UTCIParameter(self.cold_thresh, self.heat_thresh,
                             self.extreme_cold_thresh, self.very_strong_cold_thresh,
                             self.strong_cold_thresh,
                             self.moderate_cold_thresh, self.moderate_heat_thresh,
                             self.strong_heat_thresh,
                             self.very_strong_heat_thresh, self.extreme_heat_thresh)

    def __repr__(self):
        """UTCI comfort parameters representation."""
        return '--cold {} --heat {} --extreme-cold {} ' \
            '--very-strong-cold {} --strong-cold {} --moderate-cold {} ' \
            '--moderate-heat {} --strong-heat {} --very-strong-heat {} ' \
            '--extreme-heat {}'.format(
                self.cold_thresh, self.heat_thresh, self.extreme_cold_thresh,
                self.very_strong_cold_thresh, self.strong_cold_thresh,
                self.moderate_cold_thresh, self.moderate_heat_thresh,
                self.strong_heat_thresh, self.very_strong_heat_thresh,
                self.extreme_heat_thresh)
