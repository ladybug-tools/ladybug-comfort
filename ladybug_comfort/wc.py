# coding=utf-8
"""Utility functions for calculating Wind Chill Index (WCI) and Wind Chill
Temperature (WCT)"""

import math


def windchill_index(ta, ws):
    """Calculate the Wind Chill Index (WCI) from air temperature and wind
    speed.

    Wind Chill Index is derived from original work carried out by Gregorczuk[1].
    It qualifies thermal sensations of a person in wintertime. It is especially
    useful at low and very low air temperature and at high wind speed.

    Note:
        [1] https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/196900031\
09_1969003109.pdf,  equation 55, page 6-113

    Args:
        ta: Air temperature [C]
        ws: Wind speed [m/s]

    Returns:
        wci -- Wind Chill Index [W/m2]
    """
    wci = (10 * math.sqrt(ws) + 10.45 - ws) * (33 - ta) * 1.163

    return wci


def windchill_index_effect_category(wci):
    """Get the category of effect associated with a given wind chill index
    (WCI).

    Each number (from -4 to 3) represents a certain WCI thermal sensation
    category. With categories being the following:

    * -4 = Extreme frost
    * -3 = Frosty
    * -2 = Cold
    * -1 = Cool
    * 0 = Comfortable
    * 1 = Warm
    * 2 = Hot
    * 3 = Extremely hot

    Args:
        wci: Wind Chill Index [W/m2]

    Returns:
        category -- An integer indicating the level of effect associated with
        the wind chill index. Values are one of the following:

        -   -4 = Extreme frost
        -   -3 = Frosty
        -   -2 = Cold
        -   -1 = Cool
        -    0 = Comfortable
        -    1 = Warm
        -    2 = Hot
        -    3 = Extremely hot
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


def windchill_temp(ta, ws):
    """Calculate the Wind Chill Temperature (WCT) from air temperature and wind
    speed.

    It is the perceived decrease in air temperature felt by the body on
    exposed skin due to the flow of air. It's used by both National
    Weather Service (NSW) in US and Canadian Meteorologist service.
    The formula is derived from Environment Canada [1].

    Note:
        [1]  "Environment Canada - Weather and Meteorology - Canada's Wind
        Chill Index". Ec.gc.ca. Retrieved 2013-08-09.

    Args:
        ta: Air temperature [C]
        ws: Wind speed [m/s]

    Returns:
        twc -- Wind Chill Temperature [C]
    """
    ws_km_h = ws * 3.6   # convert wind speed from m/s to km/h
    twc = 13.12 + 0.6215 * ta - 11.37 * (ws_km_h ** 0.16) + 0.3965 * ta * \
        (ws_km_h ** 0.16)

    return twc


def windchill_temp_effect_category(twc):
    """Get the category of effect associated with a given wind chill
    temperature (WCT).

    Each number (from -6 to 0) represents a certain WCT thermal sensation
    category. With categories being the following:

    * 0 = No discomfort. No risk of frostbite formost people
    * -1 = Slight increase in discomfort. Low risk of frostbite for most people
    * -2 = Risk of hypothermia if outside for long periods without adequate
      protection. Low risk of frostbite for most people
    * -3 = Risk of hypothermia if outside for long periods without adequate
      clothing or shelter from wind and cold. Increasing risk of frostbite
      for most people in 10 to 30 minutes of exposure
    * -4 = Risk of hypothermia if outside for long periods without adequate
      clothing or shelter from wind and cold. High risk of frostbite
      for most people in 5 to 10 minutes of exposure
    * -5 = Serious risk of hypothermia if outside for long periods without
      adequate clothing or shelter from wind and cold. High risk of
      frostbite for most people in 2 to 5 minutes of exposure
    * -6 = Danger! Outdoor conditions are hazardous. High risk of frostbite for
      most people in 2 minutes of exposure or less

    Args:
        twc: Wind Chill Temperature [C]

    Returns:
        category -- An integer indicating the level of warning associated with the
        heat index. Values are one of the following:

        -    0 = No discomfort
        -   -1 = Slight increase in discomfort
        -   -2 = Risk of hypothermia if outside for long periods without adequate
            protection
        -   -3 = Risk of hypothermia if outside for long periods without adequate
            clothing or shelter from wind and cold.
        -   -4 = Risk of hypothermia if outside for long periods without adequate
            clothing or shelter from wind and cold.
        -   -5 = Serious risk of hypothermia if outside for long periods without
            adequate clothing or shelter from wind and cold.
        -   -6 = Danger! Outdoor conditions are hazardous.
    """
    if twc >= 0:
        category = 0
    elif twc >= -9:
        category = -1
    elif twc >= -27:
        category = -2
    elif twc >= -39:
        category = -3
    elif twc >= -47:
        category = -4
    elif twc >= -54:
        category = -5
    else:
        category = -6

    return category
