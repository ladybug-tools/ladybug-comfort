# coding=utf-8
"""Utility functions for calculating Actual Sensation Vote (ASV)"""


def actual_sensation_vote(ta, ws, rh, sr):
    """Calculate Actual Sensation Vote (ASV) from air temperature, wind speed,
    relative humidity and solar radiation.

    Actual Sensation Vote is an index which estimates human thermal sensation
    based on the empirical data gathered from field and human surveys,
    interviews and questionnaires.
    Actual Sensation Vote is derived from original work carried out by Givoni and
    Noguchi [1].

    Note:
        [1] Zambrano, Letícia & Malafaia, Cristina & Bastos, Leopoldo.
        (2006). Thermal comfort evaluation in outdoor space of tropical humid
        climate.

    Args:
        ta: Air temperature [C]
        ws: Wind speed [m/s]
        rh: Relative humidity [%]
        sr: Solar radiation [Wh/m2]

    Returns:
        asv -- Actual sensation vote [unitless]
    """
    asv = 0.049 * ta + 0.001 * sr - 0.051 * ws + 0.014 * rh - 2.079

    return asv


def actual_sensation_vote_effect_category(asv):
    """Get the category of effect associated with a given actual sensation vote
    (ASV).

    Each number (from -2 to 2) represents a certain ASV thermal sensation
    category. With categories being the following:

    * -2 = Very cold
    * -1 = Cold
    * 0 = Comfort
    * 1 = Hot
    * 2 = Very Hot

    Args:
        asv -- Actual Sensation Vote [unitless]

    Returns:
        category -- An integer indicating the level of effect associated with the
        thermal sensation. Values are one of the following:

        -   -2 = Very cold
        -   -1 = Cold
        -   0 = Comfort
        -   1 = Hot
        -   2 = Very Hot
    """
    if asv > 2:
        category = 2
    elif asv > 1:
        category = 1
    elif asv >= -1:
        category = 0
    elif asv >= -2:
        category = -1
    else:
        category = -2

    return category
