# -*- coding: utf-8 -*-
"""Utility functions to calculate Effective Temperature"""


def effective_temperature_conditions(tre, te):
    """ Inputs:
        * tre: Radiant effective temperature
        * te: Thermal emission
        Outputs:
        * tre: Radiant effective temperature
        * te: Effective temperature
    """
    if tre < 1:
        effectTE = -4
    elif tre >= 1 and te < 9:
        effectTE = -3
    elif tre >= 9 and te < 17:
        effectTE = -2
    elif tre >= 17 and te < 21:
        effectTE = -1
    elif tre >= 21 and te < 23:
        effectTE = 0
    elif tre >= 23 and te < 27:
        effectTE = 1
    elif tre >= 27:
        effectTE = 2

    return tre, effectTE


def effective_temperature(ta, ws, rh, sr, ac):
    """ Inputs: 
            * ta: Air Temperature 
            * ws: Wind Speed
            * rh: Relative Humidity
            * sr: Solar Radiation
            * ac: Air Flow
        Outputs:
            * tre: Radiant Effective Temperature 
            * effectTE
            * Comfort: boolean value for whether or not the effective temp is comfortable
    """
    if ws <= 0.2:
        # formula by Missenard
        te = ta - 0.4 * (ta - 10) * (1 - rh / 100)
    elif ws > 0.2:
        # modified formula by Gregorczuk (WMO, 1972; Hentschel, 1987)
        te = 37 - ((37 - ta) / (0.68 - (0.0014 * rh) + (1 / (1.76 + 1.4 * (ws ** 0.75))))) - \
            (0.29 * ta * (1 - 0.01 * rh))

    # Radiative-effective temperature
    tre = te + ((1 - 0.01 * ac) * sr) * ((0.0155 - 0.00025 * te) - (0.0043 - 0.00011 * te))

    return effective_temperature_conditions(tre, te)
