# coding=utf-8
"""Utility functions for calculating Heat Index (HI)."""
from __future__ import division

import math


def heat_index(ta, rh):
    """Calculate heat index (HI) from air temperature and relative humidity.

    Heat index is derived from original work carried out by Robert G. Steadman [1],
    which defined heat index through large tables of empirical data.
    The formula here approximates the heat index to within +/- 0.7C and is
    the result of a multivariate fit [2].
    Heat index was adopted by the US's National Weather Service (NWS) in 1979.

    Note:
        [1] Steadman, R. G. (July 1979). "The Assessment of Sultriness. Part I: A
        Temperature-Humidity Index Based on Human Physiology and Clothing Science".
        Journal of Applied Meteorology. 18 (7): 861–873.

        [2] Lans P. Rothfusz. "The Heat Index 'Equation' (or, More Than You Ever
        Wanted to Know About Heat Index)", Scientific Services Division
        (NWS Southern Region Headquarters), 1 July 1990.
        https://www.weather.gov/media/ffc/ta_htindx.PDF

    Args:
        ta: Air temperature [C]
        rh: Relative humidity [%]

    Returns:
        hi: Heat index [C]
    """
    tf = ta * 9. / 5. + 32.  # convert to fahrenheit

    if tf < 80:
        hif = 0.5 * (tf + 61.0 + ((tf - 68.0) * 1.2) + (rh * 0.094))
    else:
        hif = -42.379 + 2.04901523 * tf + \
            10.14333127 * rh - \
            0.22475541 * tf * rh - \
            6.83783e-3 * tf ** 2 - \
            5.481717e-2 * rh ** 2 + \
            1.22874e-3 * tf ** 2 * rh + \
            8.5282e-4 * tf * rh ** 2 - \
            1.99e-6 * tf ** 2 * rh ** 2
        if tf >= 80 and tf <= 112 and rh < 13:
            adjust = ((13. - rh) / 4.) * math.sqrt((17. - abs(tf - 95.)) / 17.)
            hif = hif - adjust
        elif tf >= 80 and tf <= 87 and rh > 85:
            adjust = ((rh - 85) / 10) * ((87 - tf) / 5)
            hif = hif + adjust

    hi = (hif - 32.) * 5. / 9.  # convert to celcius

    return hi


def heat_index_warning_category(hi):
    """Get the category of warning associated with a given heat index (HI).

    Categories are used by the US National Weather Service (NWS) and National
    Oceanic and Atmospheric Administration (NOAA) to issue the following warnings:
        0 = No Warning. Satisfactory temperature. Can continue with activity.
        1 = Caution: Fatigue is possible with prolonged exposure and activity.
            Continuing activity could result in heat cramps.
        2 = Extreme caution: Heat cramps and heat exhaustion are possible.
            Continuing activity could result in heat stroke.
        3 = Danger: Heat cramps and heat exhaustion are likely.
            Heat stroke is probable with continued activity.
        4 = Extreme danger: Heat stroke is imminent.

    Args:
        hi: Heat index [C]

    Returns:
        category: An integer indicating the level of warning associated with the
            heat index. Values are one of the following:
                0 = No Warning
                1 = Caution
                2 = Extreme Caution
                3 = Danger
                4 = Extreme Danger
    """
    if hi < 26.6:
        category = 0
    elif hi < 32.2:
        category = 1
    elif hi < 40.5:
        category = 2
    elif hi < 54.4:
        category = 3
    else:
        category = 4

    return category


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
