# coding=utf-8
"""Utility functions for calculating Wind Chill Index (WCI) and Wind Chill
Temperature (WCT)"""

import math


def windchill_index(ta, ws):
    """Calculate the Wind Chill Index (WCI) from air temperature  and wind
    speed.

    Wind Chill Index is derived from original work carried out by Gregorczuk[1].
    It qualifies thermal sensations of man in wintertime. It is especially
    useful at low and very low air temperature and at high wind speed.

    Note:
        [1] https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/196900031
        09_1969003109.pdf,  equation 55, page 6-113

    Args:
        ta: Air temperature [C]
        ws: Wind speed [m/s]

    Returns:
        wci: Wind Chill Index [W/m2]
    """
    wci = (10 * math.sqrt(ws) + 10.45 - ws) * (33 - ta) * 1.163

    return wci


def windchill_index_effect_category(wci):
    """Get the category of effect associated with a given wind chill index
    (WCI).

    Each number (from -4 to 3) represents a certain WCI thermal sensation
    category. With categories being the following:
    -4 = Extreme frost
    -3 = Frosty
    -2 = Cold
    -1 = Cool
     0 = Comfortable
     1 = Warm
     2 = Hot
     3 = Extremely hot

    Args:
        wci: Wind Chill Index [W/m2]

    Returns:
        category: An integer indicating the level of effect associated with
            the wind chill index. Values are one of the following:
                -4 = Extreme frost
                -3 = Frosty
                -2 = Cold
                -1 = Cool
                 0 = Comfortable
                 1 = Warm
                 2 = Hot
                 3 = Extremely hot
                
    """
    if wci >= 2326:
        category = -4
    elif wci >= 1628.2:
        category = -3
    elif wci >= 930.4:
        category = -2
    elif wci >= 581.5:
        category = -1
    elif wci >= 232.6:
        category = 0
    elif wci >= 116.3:
        category = 1
    elif wci >= 58.3:
        category = 2
    else:
        category = 3

    return category
