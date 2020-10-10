# coding=utf-8
"""Utility functions for calculating the Wet Bulb Globe Temperature (WBGT)."""
from __future__ import division

import math


def wbgt_outdoors(ta, mrt, ws, vp):
    """
    The wet-bulb globe temperature (WBGT) is a type of apparent temperature,
    and is widely used heat stress index globally (ISO 7243). It is used to
    estimate the effect of temperature, humidity, wind speed (wind chill), and
    visible and infrared radiation (usually sunlight) on humans.

    WBGT outdoor formula is based on a mathematical model published by
    K. Blazejczyk et al. in 2014 [1] with the natural wet bulb temparature
    (Tnwb) based on the code written by Nick Burns [2].

    Note:
        [1] Heat stress and occupational health and safety spatial
        and temporal differentiation, K. Blazejczyk, J.Baranowski, A. Blazejczyk,
        Miscellanea geographica regional studies on development, Vol. 18,
        No. 1, 2014
        [2] https://github.com/nickb-/Calculating-WBGT/blob/master/relaxation_Tw/
        working_code/wbgt.R

    Args:
        ta: Air temperature [C]
        mrt: Radiant temperature [C]
        ws: Wind speed [m/s]
        vp: Vapour pressure [hPa]

    Returns:
        outdoor WBGT

    """
    # Natural wet bulb temperature
    tnwb = 1.885 + 0.3704 * ta + 0.4492 * vp
    # Black-globe temperature
    tg = 2.098 - 2.561 * ws + 0.5957 * ta + 0.4017 * mrt
    # outdoor WBGT
    wbgt_od = 0.7 * tnwb + 0.2 * tg + 0.1 * ta

    return wbgt_od


def wbgt_indoors(ta, tdp, ws):
    """
    Used for indoors, or when solar radiation is negligible.
    WBGT indoor formula by Bernard et al. (1999), formula from: "Calculating
    Workplace WBGT from Meteorological Data: A Tool for Climate Change Assessment",
    Lemke, Kjellstrom, 2012

    Args:
        ta: Air temperature [C]
        tdp: Dew point temperature [C]
        ws: Wind speed [m/s]

    Returns:
        indoor WBGT

    """
    # Calculate Psychrometric wet bulb temperature (Tpwb) by iteration using
    # a formula derived from McPherson
    ed = 0.6106 * math.exp(17.27 * tdp / (237.7 + tdp))
    step = 0.02  # lowering the step value increases precision
    tpwb = tdp + step
    mc_pherson_1 = 1
    mc_pherson_2 = 1
    while tpwb <= ta and ((mc_pherson_1 > 0 and mc_pherson_2 > 0) or (
            mc_pherson_1 < 0 and mc_pherson_2 < 0)):
        ew = 0.6106 * math.exp(17.27 * tpwb / (237.7 + tpwb))
        mc_pherson_1 = mc_pherson_2
        mc_pherson_2 = 1556 * ed - 1.484 * ed * tpwb - 1556 * ew +\
                       1.484 * ew * tpwb + 1010 * (ta - tpwb)
        tpwb = tpwb + step

    # Calculate indoor WBGT
    if ws > 3:
        wbgt_id = 0.7 * tpwb + 0.3 * ta
    elif ws >= 0.3:
        wbgt_id = 0.67 * tpwb + 0.33 * ta - 0.048 * math.log10(ws) * (ta - tpwb)
    else:
        ws = 0.3
        wbgt_id = 0.67 * tpwb + 0.33 * ta - 0.048 * math.log10(ws) * (ta - tpwb)

    return wbgt_id


def wbgt_warning_category(wbgt):
    """
    Get the category of warning associated with a given Wet Bulb Globe
    Temperature(WBGT).

    Categories are based on the US National Weather Service(NWS) issue the
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
        exercising in direct sunlight

    Args:
        wbgt: Wet Bulb Globe Temperature [C]

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
