# coding=utf-8
"""Utility functions for computing local thermal discomfort according to ASHRAE-55."""
from __future__ import division

import math


def radiant_asymmetry_ppd(radiant_temperature_difference, asymmetry_type):
    """Calculate the percentage of people dissatisfied from radiant asymmetry.

    The comfort functions used here come from Figure 5.2.4.1 of ASHRAE 55 2010.
    Note that, if the resulting input results in a PPD beyond what is included
    in this Figure, the maximum PPD will simply be returned.

    Note:
        [1] ASHRAE Standard 55 (2010). "Thermal Environmental Conditions
        for Human Occupancy." American Society of Heating,
        Refrigerating and Air Conditioning Engineers.

    Args:
        radiant_temperature_difference: The radiant temperature difference between
            two sides of the same plane where an occupant is located [C].
        asymmetry_type: An integer that representing the type of radiant
            asymmetry being evaluated. Occupants are more sensitive to warm
            ceilings and cool walls than cool ceilings and warm walls.
            Choose from the following options.

            * 0 = WarmCeiling
            * 1 = CoolWall
            * 2 = CoolCeiling
            * 3 = WarmWall

    Returns:
        ppd -- The percentage of people dissatisfied (PPD) for the input
        radiant asymmetry.
    """
    td = radiant_temperature_difference
    if asymmetry_type == 0:
        if td > 23:
            ppd = 100 / (1 + math.exp(2.84 - 0.174 * 23)) - 5.5
        else:
            ppd = 100 / (1 + math.exp(2.84 - 0.174 * td)) - 5.5
    elif asymmetry_type == 1:
        if td > 15:
            ppd = 100 / (1 + math.exp(6.61 - 0.345 * 15))
        else:
            ppd = 100 / (1 + math.exp(6.61 - 0.345 * td))
    elif asymmetry_type == 2:
        if td > 15:
            ppd = 100 / (1 + math.exp(9.93 - 0.50 * 15))
        else:
            ppd = 100 / (1 + math.exp(9.93 - 0.50 * td))
    elif asymmetry_type == 3:
        if td > 35:
            ppd = 100 / (1 + math.exp(3.72 - 0.052 * 35)) - 3.5
        else:
            ppd = 100 / (1 + math.exp(3.72 - 0.052 * td)) - 3.5
    else:
        raise ValueError(
            'Radiant asymmetry_type "{}" was not recognized.'.format(asymmetry_type))
    return ppd
