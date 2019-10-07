# coding=utf-8
"""Utility function for calculating Discomfort Index (DI)."""


def discomfort_index(ta, rh):
    """Calculate discomfort index (DI) from air temperature and relative
    humidity.

    Discomfort Index is derived from original work carried out by Eral C. Thom
    [1] which defined discomfort index based on dry-bulb and wet-bulb
    temperature.

    Note:
        [1]  Thom, E.C. (1959) "The Discomfort Index". Weatherwise, 12, 57-61. 
    Args:
        ta: Air temperature [C]
        rh: Relative humidity  [%]

    Returns:
        hi: Heat index [C]
    """
    di = ta - (0.55 - 0.0055 * rh) * (ta  - 14.5)

    return di
