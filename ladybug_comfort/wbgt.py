# coding=utf-8
"""Utility functions for calculating the Wet Bulb Globe Temperature (WBGT)."""
from __future__ import division

import math

from ladybug.psychrometrics import saturated_vapor_pressure


def wet_bulb_globe_temperature(ta, mrt, ws, rh):
    """Get wet-bulb globe temperature (WBGT) for outdoor conditions.
    
    WBGT is a type of feels-like temperature that is widely used as a heat stress
    index (ISO 7243). It is incorporates the effect of temperature, humidity, wind
    speed, and mean radiant temperature (optionally including the effect of sun).

    The WBGT outdoor formula is based on a mathematical model published by
    K. Blazejczyk et al. in 2014 [1] with the natural wet bulb temperature
    (Tnwb) based on the code written by Nick Burns.

    Note:
        [1] Heat stress and occupational health and safety spatial
        and temporal differentiation, K. Blazejczyk, J.Baranowski, A. Blazejczyk,
        Miscellanea geographica regional studies on development, Vol. 18,
        No. 1, 2014

    Args:
        ta: Air temperature [C]
        mrt: Radiant temperature [C]
        ws: Wind speed at average human height [m/s]
        rh: Relative humidity [%]

    Returns:
        Outdoor WBGT
    """
    p_ws = saturated_vapor_pressure(ta + 273.15)  # saturation pressure
    vp = p_ws * (rh / 10000)  # partial pressure
    tnwb = -9.27522 + 0.70196 * ta + 0.30338 * vp + 0.07823 * rh  # natural wet bulb temp
    tg = 2.098 - 2.561 * ws + 0.5957 * ta + 0.4017 * mrt  # black-globe temperature
    wbgt_od = 0.7 * tnwb + 0.2 * tg + 0.1 * ta  # outdoor WBGT
    return wbgt_od


def wbgt_warning_category(wbgt):
    """Get the warning category associated with a given WBGT.

    Categories are based on the US National Weather Service (NWS), which issues the
    following suggested actions and impact prevention:

    * 0 = No Warning.
    * 1 = Working or exercising in direct sunlight will stress your body after
        45 minutes. Take at least 15 minutes of breaks each hour if working or
        exercising in direct sunlight.
    * 2 = Working or exercising in direct sunlight will stress your body after
        30 minutes. Take at least 30 minutes of breaks each hour if working or
        exercising in direct sunlight.
    * 3 = Working or exercising in direct sunlight will stress your body after
        20 minutes. Take at least 40 minutes of breaks each hour if working or
        exercising in direct sunlight.
    * 4 = Working or exercising in direct sunlight will stress your body after
        15 minutes. Take at least 45 minutes of breaks each hour if working or
        exercising in direct sunlight.

    Args:
        wbgt: Wet Bulb Globe Temperature [C].

    Returns:
        category: An integer indicating the level of warning associated with
        the Wet Bulb Globe Temperature (WBGT).
    """
    wbgt_f = wbgt * 9. / 5. + 32.  # convert to fahrenheit

    if wbgt_f < 80:
        category = 0
    elif wbgt_f < 85:
        category = 1
    elif wbgt_f < 88:
        category = 2
    elif wbgt_f < 90:
        category = 3
    else:
        category = 4

    return category
