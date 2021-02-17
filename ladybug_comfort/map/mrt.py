# coding=utf-8
"""Methods for resolving MRT from Radiance output files."""
from __future__ import division

from ladybug.sunpath import Sunpath
from ladybug.datatype.energyflux import Irradiance
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.header import Header
from ladybug.datacollection import HourlyContinuousCollection

from ..solarcal import sharp_from_solar_and_body_azimuth
from ..collection.solarcal import _HorizontalSolarCalMap, _HorizontalRefSolarCalMap
from ..parameter.solarcal import SolarCalParameter


def shortwave_mrt_map(location, longwave_data, sun_up_hours, total_ill, direct_ill,
                      ref_ill=None, solarcal_par=None):
    """Get MRT data collections adjusted for shortwave using Radiance .ill files.

    Args:
        location: A ladybug Location object to dictate the solar positions used
            in the calculation.
        longwave_data: An array of data collections for each point within a thermal
            map. All collections must be aligned with one another. The analysis
            period on the collections does not have to be annual.
        sun_up_hours: File path to a sun-up-hours.txt file output by Radiance.
        total_ill: Path to an .ill file output by Radiance containing total
            irradiance for each longwave_data collection.
        direct_ill: Path to an .ill file output by Radiance containing direct
            irradiance for each longwave_data collection.
        ref_ill: Path to an .ill file output by Radiance containing total ground-
            reflected irradiance for each longwave_data collection. If None, a
            default ground reflectance of 0.25 will be assumed.
        solarcal_par: Optional SolarCalParameter object to account for
            properties of the human geometry.
    """
    # determine the analysis period and open the sun_up_hours file
    a_per = longwave_data[0].header.analysis_period
    is_annual, t_step, lp_yr = a_per.is_annual, a_per.timestep, a_per.is_leap_year
    with open(sun_up_hours) as soh_f:
        sun_indices = [int(float(h) * t_step) for h in soh_f]

    # parse each of the .ill files into annual irradiance data collections
    total = _ill_file_to_data(total_ill, sun_indices, t_step, lp_yr)
    direct = _ill_file_to_data(direct_ill, sun_indices, t_step, lp_yr)
    ref = _ill_file_to_data(ref_ill, sun_indices, t_step, lp_yr) \
        if ref_ill is not None else None

    # if the analysis is not annual, apply analysis periods
    if not is_annual:
        total = [data.filter_by_analysis_period(a_per) for data in total]
        direct = [data.filter_by_analysis_period(a_per) for data in direct]
        if ref is not None:
            ref = [data.filter_by_analysis_period(a_per) for data in ref]

    # convert total irradiance into indirect irradiance
    indirect = [t_rad - d_rad for t_rad, d_rad in zip(total, direct)]

    # compute solar altitudes and sharps
    body_par = SolarCalParameter() if solarcal_par is None else solarcal_par
    sp = Sunpath.from_location(location)
    _altitudes = []
    if body_par.body_azimuth is None:
        _sharps = [body_par.sharp] * len(a_per)
        for t_date in a_per.datetimes:
            sun = sp.calculate_sun_from_date_time(t_date)
            _altitudes.append(sun.altitude)
    else:
        _sharps = []
        for t_date in a_per.datetimes:
            sun = sp.calculate_sun_from_date_time(t_date)
            sharp = sharp_from_solar_and_body_azimuth(sun.azimuth, body_par.body_azimuth)
            _sharps.append(sharp)
            _altitudes.append(sun.altitude)

    # pass all data through the solarcal collections and return MRT data collections
    mrt_data = []
    if ref is not None:  # fully-detailed SolarCal with ground reflectance
        for l_mrt, d_rad, i_rad, r_rad in zip(longwave_data, direct, indirect, ref):
            scl_obj = _HorizontalRefSolarCalMap(
                _altitudes, _sharps, d_rad, i_rad, r_rad, l_mrt, None, body_par)
            mrt_data.append(scl_obj.mean_radiant_temperature)
    else:  # simpler SolarCal assuming default ground reflectance
        for l_mrt, d_rad, i_rad in zip(longwave_data, direct, indirect):
            scl_obj = _HorizontalSolarCalMap(
                _altitudes, _sharps, d_rad, i_rad, l_mrt, None, None, body_par)
            mrt_data.append(scl_obj.mean_radiant_temperature)
    return mrt_data


def _ill_file_to_data(ill_file, sun_indices, timestep=1, leap_yr=False):
    """Convert a list of sun-up irradiance from an .ill file into annual irradiance data.

    Args:
        ill_values: A list of raw irradiance values from an .ill file.
        sun_indices: A list of integers for where in the total_count sun-up hours occur.
        timestep: The timestep to make the data collection.
        leap_yr: Boolean to note if data is for a leap year.
    
    Return:
        A list of annual HourlyContinuousCollection with irradiance data.
    """
    irr_data = []
    with open(ill_file) as results:
        for pt_res in results:
            ill_values = [float(v) for v in pt_res.split()]
            pt_irr_data = _ill_values_to_data(ill_values, sun_indices, timestep, leap_yr)
            irr_data.append(pt_irr_data)
    return irr_data


def _ill_values_to_data(ill_values, sun_indices, timestep=1, leap_yr=False):
    """Convert a list of sun-up irradiance from an .ill file into annual irradiance data.

    Args:
        ill_values: A list of raw irradiance values from an .ill file.
        sun_indices: A list of integers for where in the total_count sun-up hours occur.
        timestep: The timestep to make the data collection.
        leap_yr: Boolean to note if data is for a leap year.
    
    Return:
        An annual HourlyContinuousCollection of irradiance data.
    """
    values = [0] * (8760 * timestep) if not leap_yr else [0] * (8784 * timestep)
    for i, irr in zip(sun_indices, ill_values):
        values[i] = irr
    a_period = AnalysisPeriod(timestep=timestep, is_leap_year=leap_yr)
    header = Header(Irradiance(), 'W/m2', a_period)
    return HourlyContinuousCollection(header, values)
