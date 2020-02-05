# coding=utf-8
"""Utility functions for calculating the Apparent Temperature (AT)."""
from __future__ import division

import math


def apparent_temperature(ta, rh, ws):
    """Calculate apparent temperature (AT) from air temperature, relative humidity,
     and wind speed.

    The Australian Apparent Temperature (AT) is a type of heat index that was used by
    the Australian Bureau of Meteorology (ABM). It is based on a mathematical model
    published by Robert G. Steadman in 1994 [1]. Two forms of the model are available,
    one including radiation and one without. This algorithm uses the non-radiation
    version. [2]

    Note:
        [1] Steadman, R. G. (1994). Norms of apparent temperature in Australia. Aust.
        Met. Mag, 43, 1-16.
        [2] Thermal Comfort observations. (n.d.). Retrieved May 20, 2016,
        from http://www.bom.gov.au/info/thermal_stress/

    Args:
        ta: Air temperature [C]
        rh: Relative humidity [%]
        ws: Wind speed (km /h)

    Returns:
        at -- Apparent Temperature[C]
    """

    # e =  Water vapour pressure (hPa) [humidity]
    e = (rh / 100) * 6.105 * math.exp((17.27 * ta) / (237.7 + ta))
    at = ta + (0.33 * e) - (0.70 * ws) - 4.00

    return at


def apparent_temperature_warning_category(at):
    """Get the category of apparent suggestion associated with a given apparent
    temperature (AT).

    Categories to indicate apparent suggestion:

    * 4 = (>40 C) Minimal clothing; sun protection required.
    * 3 = (35-40 C) Minimal clothing; sun protection as needed.
    * 2 = (30-35 C) Short sleeve, shirt and shorts.
    * 1 = (25-30 C) Light undershirt.
    * 0 = (20-25 C) Cotton-type slacks (pants).
    * -1 = (15-20 C) Normal office wear.
    * -2 = (10-15 C) Thin or sleeveless sweater.
    * -3 = (5-10 C) Sweater. Thicker underwear.
    * -4 = (0-5 C) Coat and sweater.
    * -5 = (-5-0 C) Overcoat. Wind protection as needed.
    * -6 = (<-5 C) Overcoat. Head insulation. Heavier footwear.

    Args:
        at: Apparent temperature [C]

    Returns:
        category -- An integer indicating the level of warning associated with the
        heat index. Values are one of the following:

        -   4 = Minimal clothing.
        -   3 = Minimal clothing.
        -   2 = Short sleeve, shirt and shorts.
        -   1 = Light undershirt.
        -   0 = Cotton-type slacks (pants).
        -   -1 = Normal office wear.
        -   -2 = Thin or sleeveless sweater.
        -   -3 = Sweater. Thicker underwear.
        -   -4 = Coat and sweater.
        -   -5 = Overcoat.
        -   -6 = Overcoat.
    """

    if at > 40:
        category = 4
    elif at > 35:
        category = 3
    elif at > 30:
        category = 2
    elif at > 25:
        category = 1
    elif at > 20:
        category = 0
    elif at > 15:
        category = -1
    elif at > 10:
        category = -2
    elif at > 5:
        category = -3
    elif at > 0:
        category = -4
    elif at > -5:
        category = -5
    else:
        category = -6

    return category
