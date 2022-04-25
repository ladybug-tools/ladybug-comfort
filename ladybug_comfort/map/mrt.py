# coding=utf-8
"""Methods for resolving MRT from Radiance and EnergyPlus output files."""
from __future__ import division

import os
import json

from ladybug.epw import EPW
from ladybug.sql import SQLiteResult
from ladybug.sunpath import Sunpath
from ladybug.datatype.energyflux import Irradiance
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.header import Header
from ladybug.datacollection import HourlyContinuousCollection

from ..solarcal import sharp_from_solar_and_body_azimuth
from ..collection.solarcal import _HorizontalSolarCalMap, _HorizontalRefSolarCalMap
from ..parameter.solarcal import SolarCalParameter


def shortwave_mrt_map(
    location, longwave_data, sun_up_hours, indirect_ill, direct_ill=None, ref_ill=None,
    contributions=None, transmittance_contribs=None,
    solarcal_par=None, indirect_is_total=False
):
    """Get MRT data collections adjusted for shortwave using Radiance .ill files.

    Args:
        location: A ladybug Location object to dictate the solar positions used
            in the calculation.
        longwave_data: An array of data collections for each point within a thermal
            map. All collections must be aligned with one another. The analysis
            period on the collections does not have to be annual.
        sun_up_hours: File path to a sun-up-hours.txt file output by Radiance.
        indirect_ill: Path to an .ill file output by Radiance containing indirect
            irradiance for each longwave_data collection. Alternatively, if
            indirect_is_total is set to True, this can be an .ill file with
            the total irradiance, which will have the direct_ill subtracted
            from it to yield the indirect illuminance.
        direct_ill: Path to an .ill file output by Radiance containing direct
            irradiance for each longwave_data collection. If None, all shortwave
            will be assumed to be indirect. (Default: None).
        ref_ill: Path to an .ill file output by Radiance containing total ground-
            reflected irradiance for each longwave_data collection. If None, a
            default ground reflectance of 0.25 will be assumed. (Default: None).
        contributions: An optional folder containing sub-folders of irradiance
            contributions from dynamic aperture groups. There should be one
            sub-folder per window groups and each one should contain three .ill
            files named direct.ill, indirect.ill and reflected.ill. If specified,
            these will be added to the irradiance inputs before computing
            shortwave MRT deltas. (Default: None).
        transmittance_contribs: An optional folder containing a transmittance
            schedule JSON and sub-folders of irradiance results that exclude the
            shade from the calculation. There should be one sub-folder per window
            groups and each one should contain three .ill files named direct.ill,
            indirect.ill and reflected.ill. If specified, these will be added to
            the irradiance inputs before computing shortwave MRT deltas.
        solarcal_par: Optional SolarCalParameter object to account for
            properties of the human geometry. (Default: None).
        indirect_is_total: A boolean to note whether the indirect_ill is actually the
            total irradiance, in which case the direct irradiance should be subtracted
            from it to get indirect irradiance. (Default: False).
    """
    # determine the analysis period and open the sun_up_hours file
    a_per = longwave_data[0].header.analysis_period
    is_annual, t_step, lp_yr = a_per.is_annual, a_per.timestep, a_per.is_leap_year
    with open(sun_up_hours) as soh_f:
        sun_indices = [int(float(h) * t_step) for h in soh_f]

    # parse each of the .ill files into annual irradiance data collections
    indirect = _ill_file_to_data(indirect_ill, sun_indices, t_step, lp_yr)
    direct = _ill_file_to_data(direct_ill, sun_indices, t_step, lp_yr) \
        if direct_ill is not None and os.path.isfile(direct_ill) else \
        [_blank_ill_data(t_step, lp_yr)] * len(indirect)
    ref = _ill_file_to_data(ref_ill, sun_indices, t_step, lp_yr) \
        if ref_ill is not None and os.path.isfile(ref_ill) else None

    # if there are dynamic contributions, then add them to the data collections
    if contributions is not None and os.path.isdir(contributions):
        for dyn_group in os.listdir(contributions):
            # get the file paths to the contributions
            group_path = os.path.join(contributions, dyn_group)
            indirect_con_f = os.path.join(group_path, 'indirect.ill')
            direct_con_f = os.path.join(group_path, 'direct.ill')
            ref_con_f = os.path.join(group_path, 'reflected.ill')
            # add the contributions to the irradiance terms
            indirect_con = _ill_file_to_data(indirect_con_f, sun_indices, t_step, lp_yr)
            indirect = [rad + c_rad for rad, c_rad in zip(indirect, indirect_con)]
            direct_con = _ill_file_to_data(direct_con_f, sun_indices, t_step, lp_yr)
            direct = [rad + c_rad for rad, c_rad in zip(direct, direct_con)]
            if ref is not None and os.path.isfile(ref_con_f):
                ref_con = _ill_file_to_data(ref_con_f, sun_indices, t_step, lp_yr)
                ref = [rad + c_rad for rad, c_rad in zip(ref, ref_con)]

    # if the analysis is not annual, apply analysis periods
    if not is_annual:
        indirect = [data.filter_by_analysis_period(a_per) for data in indirect]
        direct = [data.filter_by_analysis_period(a_per) for data in direct]
        if ref is not None:
            ref = [data.filter_by_analysis_period(a_per) for data in ref]

    # if there are any transmittance contributions, then compute and add them
    if transmittance_contribs is not None and os.path.isdir(transmittance_contribs):
        # load the JSON file with the transmittance schedules
        sch_json = os.path.join(transmittance_contribs, 'schedules.json')
        with open(sch_json) as json_file:
            sch_dict = json.load(json_file)
        shd_grps = [grp for grp in os.listdir(transmittance_contribs)
                    if grp != 'schedules.json']
        for dyn_group in shd_grps:
            t_sch_head = Header(Irradiance(), 'W/m2', a_per)
            t_sch = HourlyContinuousCollection(t_sch_head, sch_dict[dyn_group])
            # get the file paths to the transmittance_contribs
            group_path = os.path.join(transmittance_contribs, dyn_group)
            indirect_con_f = os.path.join(group_path, 'indirect.ill')
            direct_con_f = os.path.join(group_path, 'direct.ill')
            ref_con_f = os.path.join(group_path, 'reflected.ill')
            # add the transmittance_contribs to the irradiance terms
            indirect_con = _ill_file_to_data(indirect_con_f, sun_indices, t_step, lp_yr)
            direct_con = _ill_file_to_data(direct_con_f, sun_indices, t_step, lp_yr)
            if not is_annual:
                indirect_con = \
                    [data.filter_by_analysis_period(a_per) for data in indirect_con]
                direct_con = \
                    [data.filter_by_analysis_period(a_per) for data in direct_con]
            indirect = [rad + ((c_rad - rad) * t_sch)
                        for rad, c_rad in zip(indirect, indirect_con)]
            direct = [rad + ((c_rad - rad) * t_sch)
                      for rad, c_rad in zip(direct, direct_con)]
            if ref is not None and os.path.isfile(ref_con_f):
                ref_con = _ill_file_to_data(ref_con_f, sun_indices, t_step, lp_yr)
                if not is_annual:
                    ref_con = [data.filter_by_analysis_period(a_per) for data in ref_con]
                ref = [rad + ((c_rad - rad) * t_sch) for rad, c_rad in zip(ref, ref_con)]

    # if need be, convert total irradiance into indirect irradiance
    if indirect_is_total:
        indirect = [t_rad - d_rad for t_rad, d_rad in zip(indirect, direct)]

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

    # duplicate the longwave data if there is only one data collection
    if len(longwave_data) == 1:
        longwave_data = [longwave_data[0]] * len(direct)

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


def longwave_mrt_map(
        enclosure_info, modifiers, sql, view_factors, epw, analysis_period=None):
    """Get MRT data collections adjusted for shortwave using Radiance .ill files.

    Args:
        enclosure_info: Path to a JSON file containing information about the radiant
            enclosure that sensor points belong to.
        modifiers: Path to modifiers file that aligns with the view-factors.
        sql: Path to an SQLite file that was generated by EnergyPlus.
            This file must contain hourly or sub-hourly results for zone comfort
            variables.
        view_factors: CSV of spherical view factors to the surfaces in the sql.
        epw: An EPW object that will be used to specify data for any sensor outside
            of any enclosure.
        analysis_period: An optional AnalysisPeriod to be applied to all results.
            If None, all data collections will be for the entire run period of
            the sql.
    """
    # load the enclosure information and modifiers list
    with open(enclosure_info) as json_file:
        enclosure_dict = json.load(json_file)
    zone_order = [zone_id.upper() for zone_id in enclosure_dict['mapper']]
    with open(modifiers) as mf:
        mod_lines = mf.readlines()
    srf_order = [line[:-5].upper() for line in mod_lines]
    a_per = analysis_period if analysis_period is not None else AnalysisPeriod()

    # load the indoor surface temperatures if they are needed
    sql_obj = SQLiteResult(sql) if os.path.isfile(sql) \
        and os.stat(sql).st_size != 0 else None
    if enclosure_dict['has_indoor']:
        assert sql_obj is not None, \
            'Indoor sensors were found but no SQLite file was present.'
        in_avg_outp = 'Zone Mean Radiant Temperature'
        in_srf_outp = 'Surface Inside Face Temperature'
        in_avg_dict = {d.header.metadata['Zone']: d for d in
                       sql_obj.data_collections_by_output_name(in_avg_outp)}
        in_srf_dict = {d.header.metadata['Surface']: d for d in
                       sql_obj.data_collections_by_output_name(in_srf_outp)}
        in_avg = [in_avg_dict[z] for z in zone_order]
        in_srf = [in_srf_dict[s] for s in srf_order[:-3]]
        if in_avg[0].header.analysis_period != a_per:
            in_avg = [d.filter_by_analysis_period(a_per) for d in in_avg]
            in_srf = [d.filter_by_analysis_period(a_per) for d in in_srf]
        in_data = []
        for zone in in_avg:
            in_list = in_srf + [zone, zone, zone]
            in_data.append(tuple(zip(*in_list)))

    # load the EPW and outdoor surface temperatures if they are needed
    if enclosure_dict['has_outdoor']:
        if sql_obj is not None:
            out_srf_outp = 'Surface Outside Face Temperature'
            out_srf_dict = {d.header.metadata['Surface']: d for d in
                            sql_obj.data_collections_by_output_name(out_srf_outp)}
            out_srf = [out_srf_dict[s] for s in srf_order[:-3]]
            if out_srf[0].header.analysis_period != a_per:
                out_srf = [d.filter_by_analysis_period(a_per) for d in out_srf]
        else:
            out_srf = []
        epw_obj = EPW(epw)
        out_avg = epw_obj.dry_bulb_temperature
        out_sky = epw_obj.sky_temperature
        if not a_per.is_annual:
            out_avg = out_avg.filter_by_analysis_period(a_per)
            out_sky = out_sky.filter_by_analysis_period(a_per)
        out_data = out_srf + [out_avg, out_sky, out_avg]
        out_data = tuple(zip(*out_data))

    # load the view factors and perform the matrix multiplication with temperature
    with open(view_factors) as csv_data_file:
        vf_data = tuple(
            tuple(float(val) for val in row.split(',')) for row in csv_data_file)
    mrt_data = []
    for sen_enc, view_facs in zip(enclosure_dict['sensor_indices'], vf_data):
        if sen_enc == -1:  # outdoor sensor
            temp_data = out_data
        else:  # indoor sensor
            temp_data = in_data[sen_enc]
        sensor_vals = []
        for t_step in temp_data:
            sensor_vals.append(sum(vf * t for vf, t in zip(view_facs, t_step)))
        mrt_data.append(sensor_vals)
    return mrt_data


def _ill_file_to_data(ill_file, sun_indices, timestep=1, leap_yr=False):
    """Convert a list of sun-up irradiance from an .ill file into annual irradiance data.

    Args:
        ill_file: Path to an .ill file.
        sun_indices: A list of integers for where in the total_count sun-up hours occur.
        timestep: The timestep to make the data collection.
        leap_yr: Boolean to note if data is for a leap year.

    Return:
        A list of annual HourlyContinuousCollection with irradiance data.
    """
    a_period = AnalysisPeriod(timestep=timestep, is_leap_year=leap_yr)
    header = Header(Irradiance(), 'W/m2', a_period)
    irr_data = []
    with open(ill_file) as results:
        for pt_res in results:
            ill_values = [float(v) for v in pt_res.split()]
            pt_irr_data = _ill_values_to_data(
                ill_values, sun_indices, header, timestep, leap_yr)
            irr_data.append(pt_irr_data)
    return irr_data


def _ill_values_to_data(ill_values, sun_indices, header, timestep=1, leap_yr=False):
    """Convert a list of sun-up irradiance from an .ill file into annual irradiance data.

    Args:
        ill_values: A list of raw irradiance values from an .ill file.
        sun_indices: A list of integers for where in the total_count sun-up hours occur.
        header: A Header object for the for the data collection.
        timestep: The timestep to make the data collection.
        leap_yr: Boolean to note if data is for a leap year.

    Return:
        An annual HourlyContinuousCollection of irradiance data.
    """
    values = [0] * (8760 * timestep) if not leap_yr else [0] * (8784 * timestep)
    for i, irr in zip(sun_indices, ill_values):
        values[i] = irr
    return HourlyContinuousCollection(header, values)


def _blank_ill_data(timestep=1, leap_yr=False):
    """Get a list of blank annual irradiance data composed of zero values.

    Args:
        timestep: The timestep to make the data collection.
        leap_yr: Boolean to note if data is for a leap year.

    Return:
        A list of annual HourlyContinuousCollection with zero irradiance data.
    """
    a_period = AnalysisPeriod(timestep=timestep, is_leap_year=leap_yr)
    header = Header(Irradiance(), 'W/m2', a_period)
    values = [0] * (8760 * timestep) if not leap_yr else [0] * (8784 * timestep)
    return HourlyContinuousCollection(header, values)
