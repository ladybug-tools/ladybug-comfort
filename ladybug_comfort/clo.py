# coding=utf-8
"""Utility for estimating clothing level from temperature."""
from __future__ import division


def schiavon_clo(adapt_temp, max_clo=1, max_clo_temp=-5, min_clo=0.46, min_clo_temp=26):
    """Estimate levels of clothing using a temperature to which a human subject adapts.

    By default, this function derives clothing levels using a model developed by
    Schiavon, Stefano based on outdoor air temperature, which is implemented in the
    CBE comfort tool (https://comfort.cbe.berkeley.edu/).

    The version of the model implemented here allows changing of the maximum and minimum
    clothing levels, which the Schiavon model sets at 1 and 0.46 respectively, and the
    temperatures at which these clothing levels occur, which the Schiavon model sets
    at -5 C and 26 C respectively.

    Args:
        adapt_temp: A number representing the temperature to which the human subject
            adapts their clothing. This is typically the outdoor air temperature.
        max_clo: A number for the maximum clo value that the human subject wears
            on the coldest days. (Default: 1 clo, per the original Schiavon
            clothing function).
        max_clo_temp: A number for the temperature below which the _max_clo_ value
            is applied (in Celsius). (Default: -5 C, per the original
            Schiavon clothing function with outdoor temperature).
        min_clo: A number for the minimum clo value that the human subject wears
            wears on the hotest days. (Default: 0.46 clo,
            per the original Schiavon clothing function).
        min_clo_temp: A number for the temperature above which the _min_clo_ value
            is applied (in Celsius). (Default: 26 C, per the original
            Schiavon clothing function).

    Returns:
        A number for the clothing level of the human subject in clo.
    """
    assert min_clo_temp - max_clo_temp >= 10, \
        'The difference between min_clo_temp and max_clo_temp must be at least 10 C. ' \
        'Got {}.'.format(min_clo_temp - max_clo_temp)

    if adapt_temp <= max_clo_temp:
        return max_clo
    elif adapt_temp < max_clo_temp + 10:
        f1_slope = ((max_clo - (max_clo - min_clo) * 0.75) - max_clo) / 10
        f1_y_int = max_clo - (f1_slope * max_clo_temp)
        return adapt_temp * f1_slope + f1_y_int
    elif adapt_temp < min_clo_temp:
        f2_slope = (min_clo - (max_clo - (max_clo - min_clo) * 0.75)) / \
            (min_clo_temp - (max_clo_temp + 10))
        f2_y_int = min_clo - (f2_slope * min_clo_temp)
        return adapt_temp * f2_slope + f2_y_int
    else:
        return min_clo
