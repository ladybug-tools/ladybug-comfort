# coding=utf-8
"""Utility functions for calculating Heating and Cooling Degree-Time."""
from __future__ import division


def heating_degree_time(t, t_base=18):
    """Calculate heating degree time at a single time interval.

    Args:
        t: The temperature at a given time interval.
        t_base: The base temperature below which a given time is considered
            to be in heating mode. This should be in the same units as the input
            temperature. Default is 18 Celsius, which is a common balance point for
            buildings.
    """
    if t < t_base:
        return t_base - t
    else:
        return 0


def cooling_degree_time(t, t_base=23):
    """Calculate cooling degree time at a single time interval.

    Args:
        t: The temperature at a given time interval.
        t_base: The base temperature above which a given time is considered
            to be in cooling mode. This should be in the same units as the input
            temperature. Default is 23 Celsius, which is a common balance point for
            buildings.
    """
    if t > t_base:
        return t - t_base
    else:
        return 0
