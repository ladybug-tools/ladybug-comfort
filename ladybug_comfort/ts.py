# coding=utf-8
"""Utility functions for calculating Thermal Sensation (TS)."""


def thermal_sensation(ta, ws, rh, sr, tground):
    """Calculate Thermal Sensation (TS) from air temperature, wind speed,
    relative humidity, solar radiation and ground temperature.

    Thermal Sensation is an index which predicts sensation of
    satisfaction/dissatisfaction under the prevailing outdoor climatic
    conditions.
    Thermal Sensation is derived from original work carried out by Givoni and
    Noguchi [1].

    Note:
        [1] Givoni, Baruch & Noguchi, Mikiko & Saaroni, Hadas & Potchter,
        Oded & Yaakov, Yaron & Feller, Noa & Becker, Stefan. (2003). Outdoor
        comfort research issues. Energy and Buildings. 35. 77-86.
        10.1016/S0378-7788(02)00082-8.

    Args:
        ta: Air temperature [C]
        ws: Wind speed [m/s]
        rh: Relative humidity [%]
        sr: Solar radiation [Wh/m2]
        tground: Ground temperature [C]

    Returns:
        ts -- Thermal sensation [unitless]
    """
    ts = 1.7 + 0.1118 * ta + 0.0019 * sr - 0.322 * ws - 0.0073 * rh + 0.0054 \
        * tground

    return ts


def thermal_sensation_effect_category(ts):
    """Get the category of effect associated with a given thermal sensation
    (TS).

    Each number (from -3 to 3) represents a certain TS thermal sensation
    category. With categories being the following:

    * -3 = Very cold
    * -2 = Quite cold
    * -1 = Cold
    * 0 = Comfort
    * 1 = Hot
    * 2 = Quite Hot
    * 3 = Very hot

    Args:
        ts: Thermal Sensation [unitless]

    Returns:
        category -- An integer indicating the level of effect associated with the
        thermal sensation. Values are one of the following:

        -   -3 = Very cold
        -   -2 = Quite cold
        -   -1 = Cold
        -    0 = Comfort
        -    1 = Hot
        -    2 = Quite Hot
        -    3 = Very hot
    """
    if ts >= 7:
        category = 3
    elif ts >= 6:
        category = 2
    elif ts >= 5:
        category = 1
    elif ts >= 4:
        category = 0
    elif ts >= 3:
        category = -1
    elif ts >= 2:
        category = -2
    else:
        category = -3

    return category
