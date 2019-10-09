# coding=utf-8
"""Utility functions for calculating the Humidex."""
from __future__ import division

import math


def humidex(ta, tdp):
    """Calculate Humidex  from air temperature and the Dew Point.

    The Humidex is a Canadian innovation that was first used in 1965.
    It describes how hot, humid weather feels to the average person.
    The Humidex combines the temperature and humidity into one number to reflect the perceived temperature.
    Because it takes into account the two most important factors that affect summer comfort, it can be a better
    measure of how stifling the air feels than either temperature or humidity alone. [1]

    The air temperature should be above 20c or the given result is implicitly comfortable.
    Humidex values range from 20 and up with the following degree of comfort guidelines:
        20 to 29: Little discomfort
        30 to 39: Some discomfort
        40 to 45: Great discomfort; avoid exertion
        Above 45: Dangerous; heat stroke possible

    The Humidex is a nominally dimensionless quantity (though generally recognized by the
    public as equivalent to the degree Celsius)... [2]

    Note:
        [1] Environment Canada (October 2017). "Warm Season Weather Hazards".
            https://www.canada.ca/en/environment-climate-change/services/seasonal-weather-hazards/warm-season-weather-hazards.html#toc7
        [2] https://en.wikipedia.org/wiki/Humidex

    Args:
        ta: Air temperature [C]
        tdp: The Dew Point [C]

    Returns:
        float: Humidex
    """

    dew_point_k = tdp + 273.15  # celsius to kelvin

    e = 6.11 * math.exp(5417.7530 * ((1 / 273.16) - (1 / dew_point_k)))
    h = (0.5555) * (e - 10.0)

    humidex = float(ta + h)
    return humidex
