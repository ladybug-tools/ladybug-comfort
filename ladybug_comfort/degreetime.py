# coding=utf-8
"""Utility functions for calculating Heating and Cooling Degree-Time."""
from __future__ import division


def heating_degree_time(temperature, base_temperature=18):
    """Calculate heating degree time at a single time interval.

    Args:
        temperature: The temperature at a given time interval.
        base_temperature: The base temperature below which a given time is considered
            to be in heating mode. This should be in the same units as the input
            temperature. Default is 18 Celcius, which is a common balance point for
            buildings.
    """
    if temperature < base_temperature:
        return base_temperature - temperature
    else:
        return 0


def cooling_degree_time(temperature, base_temperature=23):
    """Calculate cooling degree time at a single time interval.

    Args:
        temperature: The temperature at a given time interval.
        base_temperature: The base temperature above which a given time is considered
            to be in cooling mode. This should be in the same units as the input
            temperature. Default is 23 Celcius, which is a common balance point for
            buildings.
    """
    if temperature > base_temperature:
        return temperature - base_temperature
    else:
        return 0
