# coding=utf-8
"""Utility functions for calculating Universal Thermal Climate Index (UTCI).

This module is devoted to calculating UTCI with NumPy.
"""
import numpy as np
from ..utci import _utci_polynomial


def universal_thermal_climate_index_np(ta, tr, vel, rh):
    """Calculate Universal Thermal Climate Index (UTCI) using a polynomial approximation.

    This function is the same as the base universal_thermal_climate_index function
    but it uses NumPy arrays for calculating UTCI.

    Args:
        ta: Air temperature [C] as a NumPy array.
        tr: Mean radiant temperature [C] as a NumPy array.
        vel: Wind speed 10 m above ground level [m/s] as a NumPy array.
            Note that this meteorological speed at 10 m is simply 1.5 times the
            speed felt at ground in the original Fiala model used to build UTCI.
        rh: Relative humidity [%] as a NumPy array.

    Returns:
        UTCI_approx -- The Universal Thermal Climate Index (UTCI) for the input
        conditions as approximated by a 4-D polynomial.
    """
    # set upper and lower limits of air velocity according to Fiala model scenarios
    vel = np.where(vel < 0.5, 0.5, np.where(vel > 17, 17, vel))

    # metrics derived from the inputs used in the polynomial equation
    eh_pa = saturated_vapor_pressure_hpa_np(
        ta) * (rh / 100.0).astype(np.float32)  # partial vapor pressure
    pa_pr = eh_pa / 10.0  # convert vapour pressure to kPa
    d_tr = tr - ta  # difference between radiant and air temperature

    # pre-calculate powers so we can re-use them
    utci_approx = _utci_polynomial(ta, d_tr, vel, pa_pr)

    return utci_approx


def saturated_vapor_pressure_hpa_np(db_temp):
    """Calculate saturated vapor pressure (hPa) at temperature (C).

    This equation of saturation vapor pressure is specific to the UTCI model.
    """
    g = np.array([-2836.5744, -6028.076559, 19.54263612, -0.02737830188,
                  0.000016261698, 7.0229056e-10, -1.8680009e-13])
    tk = db_temp + 273.15  # air temp in K
    es = 2.7150305 * np.log(tk)
    for i, x in enumerate(g):
        es = es + (x * (tk**(i - 2)))
    es = np.exp(es) * 0.01

    return es


def thermal_condition_np(utci, comfort_par):
    """Determine whether conditions are cold, neutral or hot.

    Values are one of the following:

    * -1 = cold
    * 0 = netural
    * +1 = hot
    """
    conditions = [
        utci < comfort_par.cold_thresh,
        utci > comfort_par.heat_thresh
    ]
    choices = [-1, 1]
    result = np.select(conditions, choices, default=0)

    return result

def thermal_condition_eleven_point_np(utci, comfort_par):
    """Determine the thermal condition on an eleven-point scale.

    Values are one of the following:

    * -5 = extreme cold stress
    * -4 = very strong cold stress
    * -3 = strong cold stress
    * -2 = moderate cold stress
    * -1 = slight cold stress
    * 0 = no thermal stress
    * +1 = slight heat stress
    * +2 = moderate heat stress
    * +3 = strong heat stress
    * +4 = very strong heat stress
    * +5 = extreme heat stress
    """
    conditions = [
        utci < comfort_par.extreme_cold_thresh,
        (utci >= comfort_par.extreme_cold_thresh) & (utci < comfort_par.very_strong_cold_thresh),
        (utci >= comfort_par.very_strong_cold_thresh) & (utci < comfort_par.strong_cold_thresh),
        (utci >= comfort_par.strong_cold_thresh) & (utci < comfort_par.moderate_cold_thresh),
        (utci >= comfort_par.moderate_cold_thresh) & (utci < comfort_par.cold_thresh),
        utci > comfort_par.extreme_heat_thresh,
        (utci <= comfort_par.extreme_heat_thresh) & (utci > comfort_par.very_strong_heat_thresh),
        (utci <= comfort_par.very_strong_heat_thresh) & (utci > comfort_par.strong_heat_thresh),
        (utci <= comfort_par.strong_heat_thresh) & (utci > comfort_par.moderate_heat_thresh),
        (utci <= comfort_par.moderate_heat_thresh) & (utci > comfort_par.heat_thresh)
    ]

    choices = [-5, -4, -3, -2, -1, 5, 4, 3, 2, 1]
    result = np.select(conditions, choices, default=0)

    return result
