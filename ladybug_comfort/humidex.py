# coding=utf-8
"""Utility functions for calculating the Humidex."""
from __future__ import division

import math


def humidex(ta, tdp):
    """Calculate Humidex from air temperature and the Dew Point.

    The Humidex is a Canadian innovation first used in 1965.
    It combines the temperature and humidity into one number to reflect the
    perceived temperature.
    Because it takes into account the two most important
    factors that affect summer comfort, it can be a better
    measure of how stifling the air feels than either temperature or
    humidity alone. [1]

    Air temperatures below 20c will give a generally meaningless result as the Humidex
    only describes perceived heat.

    The Humidex is a "nominally dimensionless quantity" but is generally
    recognized by the public as equivalent to the degree Celsius [2]

    Note:
        [1] Environment Canada (October 2017). "Warm Season Weather Hazards".
            https://www.canada.ca/en/environment-climate-change/services/seasonal\
-weather-hazards/warm-season-weather-hazards.html#toc7

        [2] https://en.wikipedia.org/wiki/Humidex

    Args:
        ta: Air temperature [C]
        tdp: The Dew Point [C]

    Returns:
        float -- Humidex
    """

    dew_point_k = tdp + 273.15  # celsius to kelvin

    e = 6.11 * math.exp(5417.7530 * ((1 / 273.15) - (1 / dew_point_k)))
    h = 0.5555 * (e - 10.0)

    humidex_value = float(ta + h)
    return humidex_value


def humidex_degree_of_comfort(humidex):
    """Get the degree of comfort associated with a given Humidex value.

    Degrees of comfort are provided by the Government of Canada and are indicated
    here with the following integer values:

    * 0 = No discomfort (Humidex of 19 and below)
    * 1 = Little discomfort (Humidex between 20 - 29)
    * 2 = Some discomfort (Humidex between 30 - 39)
    * 3 = Great discomfort; avoid exertion (Humidex between 40 - 45)
    * 4 = Dangerous; heat stroke possible (Humidex of 45 and above)

    See: https://www.canada.ca/en/environment-climate-change/services/seasonal-\
weather-hazards/warm-season-weather-hazards.html#toc7

    Args:
        humidex: Humidex

    Returns:
        int -- Degree of Comfort
    """

    if humidex < 20.0:
        return 0
    elif 20.0 <= humidex < 30.0:
        return 1
    elif 30.0 <= humidex < 40.0:
        return 2
    elif 40.0 <= humidex < 46.0:
        return 3
    return 4
