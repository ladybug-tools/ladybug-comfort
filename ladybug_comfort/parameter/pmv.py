# coding=utf-8
"""Parameters for specifying acceptable thermal conditions using the PMV model."""
from __future__ import division

from ._base import ComfortParameter
from ..pmv import ppd_threshold_from_comfort_class


class PMVParameter(ComfortParameter):
    """Parameters of PMV comfort.

    Args:
        ppd_comfort_thresh: A number between 5 and 100 that represents the upper
            threshold of PPD that is considered acceptable.
            Default is 10, which charcterizes most buildings in the ASHRAE-55 and
            EN-15251 standards.
        humid_ratio_upper: A number between 0 and 1 indicating the upper limit of
            humidity ratio that is considered acceptable. Default is 1 for
            essentially no limit.
        humid_ratio_lower: A number between 0 and 1 indicating the lower limit of
            humidity ratio considered acceptable. Default is 0 for essentially
            no limit.
        still_air_threshold: The air speed threshold in m/s at which the standard
            effective temperature (SET) model will be used to correct for the
            cooling effect of elevated air speeds.
            Default is 0.1 m/s, which is the limit according to ASHRAE-55.

    Properties:
        * ppd_comfort_thresh
        * humid_ratio_upper
        * humid_ratio_low
        * still_air_threshold
    """
    _model = 'Predicted Mean Vote'
    __slots__ = ('_ppd_thresh', '_hr_upper', '_hr_lower', '_still_thresh')

    def __init__(self, ppd_comfort_thresh=None, humid_ratio_upper=None,
                 humid_ratio_lower=None, still_air_threshold=None):
        """Initalize PMV Parameters.
        """

        self.ppd_comfort_thresh = \
            ppd_comfort_thresh if ppd_comfort_thresh is not None else 10
        self._hr_upper = humid_ratio_upper if humid_ratio_upper is not None else 1
        self._hr_lower = humid_ratio_lower if humid_ratio_lower is not None else 0
        self._still_thresh = \
            still_air_threshold if still_air_threshold is not None else 0.1

        assert 0 <= self._hr_upper <= 1, \
            'humid_ratio_upper must be between 0 and 1. Got {}'.format(
                self._hr_upper)
        assert 0 <= self._hr_lower <= 1, \
            'humid_ratio_lower must be between 0 and 1. Got {}'.format(
                self._hr_lower)
        assert self._hr_lower <= self._hr_upper, \
            'humid_ratio_lower must be less than humid_ratio_upper. {} > {}'.format(
                self._hr_lower, self._hr_upper)

        assert 0 <= self._still_thresh, \
            'still_air_threshold must be greater than 0. Got {}'.format(
                self._still_thresh)

    @property
    def ppd_comfort_thresh(self):
        """The threshold of the percentage of people dissatisfied (PPD) beyond which
        the conditions are not acceptable.  The default is 10%.
        """
        return self._ppd_thresh

    @ppd_comfort_thresh.setter
    def ppd_comfort_thresh(self, ppd):
        assert 5 <= ppd <= 100, \
            'ppd_comfort_thresh must be between 5 and 100. Got {}'.format(ppd)
        self._ppd_thresh = ppd

    @property
    def humid_ratio_upper(self):
        """A number representing the upper boundary of humidity ratio above which conditions
        are considered too humid to be comfortable.  The default is set to 0.03 kg
        wather/kg air.
        """
        return self._hr_upper

    @property
    def humid_ratio_lower(self):
        """A number representing the lower boundary of humidity ratio below which conditions
        are considered too dry to be comfortable.  The default is set to 0 kg wather/kg
        air.
        """
        return self._hr_lower

    @property
    def still_air_threshold(self):
        """A number representing the wind speed beyond which the formula for Standard
        Effective Temperature (SET) is used to dtermine PMV/PPD (as opposed to Fanger's
        original equation). The default is set to 0.1 m/s.
        """
        return self._still_thresh

    def set_ppd_comfort_thresh_from_comfort_class(self, comfort_class):
        """Set the PPD threshold given the EN-15251 comfort class."""
        self.ppd_comfort_thresh = ppd_threshold_from_comfort_class(comfort_class)

    def is_comfortable(self, ppd, humidity_ratio=0):
        """Determine if conditions are comfortable or not.

        Values are one of the following:

        * 0 = uncomfortable
        * 1 = comfortable
        """
        return 1 if (ppd <= self._ppd_thresh and humidity_ratio >= self._hr_lower and
                     humidity_ratio <= self._hr_upper) else 0

    def thermal_condition(self, pmv, ppd):
        """Determine whether conditions are cold, neutral or hot.

        Values are one of the following:

        * -1 = cold
        * 0 = netural
        * +1 = hot
        """
        if ppd >= self._ppd_thresh:
            return 1 if pmv > 0 else -1
        else:
            return 0

    def discomfort_reason(self, pmv, ppd, humidity_ratio=0):
        """Determine the reason why conditions are comfortable or not.

        Values are one of the following:

        * -2 = too dry
        * -1 = too cold
        * 0 = comfortable
        * +1 = too hot
        * +2 = too humid
        """
        if ppd >= self._ppd_thresh:
            return 1 if pmv > 0 else -1
        elif humidity_ratio < self._hr_lower:
            return -2
        elif humidity_ratio > self._hr_upper:
            return 2
        else:
            return 0

    def duplicate(self):
        """Duplicate these comfort parameters."""
        return PMVParameter(self.ppd_comfort_thresh, self.humid_ratio_upper,
                            self.humid_ratio_lower, self.still_air_threshold)

    def __repr__(self):
        """PMV comfort parameters representation."""
        return "PMV Comfort Parameters\n PPD Threshold: {}\n HR Upper: {}"\
            "\n HR Lower: {}\n Still Air Threshold: {}".format(
                self._ppd_thresh, self._hr_upper, self._hr_lower, self._still_thresh)
