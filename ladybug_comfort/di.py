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
        di: Discomfort index [C]
    """
    di = ta - (0.55 - 0.0055 * rh) * (ta - 14.5)

    return di


def discomfort_index_effect_category(di):
    """Get the category of effect associated with a given discomfort index
    (DI).

    Note:
        The categories have been taken with reference to categories by Kyle,
        1994 in Unger, 1999.

    Args:
        di: Discomfort Index

    Returns:
        category: An integer indicating the level of effect associated with the
        discomfort index. Values range from -6 to +3.
    """
    if di >= 30:
        category = 3
    elif di >= 26.5:
        category = 2
    elif di >= 20:
        category = 1
    elif di >= 15:
        category = 0
    elif di >= 13:
        category = -1
    elif di >= -1.8:
        category = -2
    elif di >= -10:
        category = -3
    elif di >= -20:
        category = -4
    elif di >= -40:
        category = -5
    else:
        category = -6

    return category
