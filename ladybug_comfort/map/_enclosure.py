# coding=utf-8
"""Methods for parsing comfort-related data from EnergyPlus output files."""
from __future__ import division

import json

from ladybug.sql import SQLiteResult
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.header import Header
from ladybug.datatype.speed import AirSpeed


def _parse_enclosure_info(enclosure_info, result_sql, epw, analysis_period=None,
                          default_air_speed=0.1, include_humidity=False,
                          use_10m_wind_speed=False):
    """Get lists of comfort-related data collections from an enclosure_info JSON.

    Args:
        enclosure_info: Path to a JSON file containing information about the radiant
            enclosure that sensor points belong to.
        result_sql: Path to an SQLite file that was generated by EnergyPlus.
            This file must contain hourly or sub-hourly results for zone comfort
            variables.
        epw: An EPW object that will be used to specify data for any sensor outside
            of any enclosure.
        analysis_period: An optional AnalysisPeriod to be applied to all results.
            If None, all data collections will be for the entire run period of
            the result_sql.
        default_air_speed: A single value or data collection to be used for all
            indoor air speed.
        include_humidity: Boolean to note whether data collections of humidity should
            be returned or not.
        use_10m_wind_speed: Boolean to note whether the meteorological wind speed
            should be used as-is for any outdoor sensors or whether it should be
            converted to ground-level speed (multiplying by 2/3).

    Returns:
        A tuple of 5 values.

        * pt_air_temps -- Data collections of air temperatures.

        * pt_rad_temps -- Data collections of long wave mean radiant temperature.

        * pt_humids - Data collections of relative humidity if include_humidity is True.

        * pt_speeds - Data collections of air speed values.

        * base_a_per - The AnalysisPeriod of the data in the result_sql.
    """
    # load all comfort-related outputs from the result_sql
    sql_obj = SQLiteResult(result_sql)
    air_temps = sql_obj.data_collections_by_output_name('Zone Mean Air Temperature')
    rad_temps = sql_obj.data_collections_by_output_name('Zone Mean Radiant Temperature')
    if include_humidity:
        humids = sql_obj.data_collections_by_output_name('Zone Air Relative Humidity')

    # check that EnergyPlus sql data is correct and note the analysis period
    assert len(air_temps) != 0, \
        'Input result-sql does not contain thermal comfort outputs.'
    assert isinstance(air_temps[0], HourlyContinuousCollection), 'EnergyPlus ' \
        'reporting frequency must be Hourly or Timestep to use thermal mapping. ' \
        'Not {}'.format(air_temps[0])
    base_a_per = air_temps[0].header.analysis_period

    # convert default air speed into a data collection if it's a list
    default_air_speed = _values_to_data(default_air_speed, base_a_per, AirSpeed, 'm/s')

    # parse the enclosure_info
    with open(enclosure_info) as json_file:
        enclosure_dict = json.load(json_file)

    # order the sql data based on the relevant zones from the enclosure_info
    rel_air_temps, rel_rad_temps, rel_humids, rel_speeds = [], [], [], []
    for zone_id in enclosure_dict['mapper']:
        zone_id = zone_id.upper()  # capitalize to match the output of EnergyPlus
        for data in air_temps:
            if data.header.metadata['Zone'] == zone_id:
                rel_air_temps.append(data)
                break
        for data in rad_temps:
            if data.header.metadata['Zone'] == zone_id:
                rel_rad_temps.append(data)
                break
        if include_humidity:
            for data in humids:
                if data.header.metadata['System'] == zone_id:
                    rel_humids.append(data)
                    break
        rel_speeds.append(default_air_speed)

    # if the enclosure info includes outdoor sensors, ensure epw data is added
    if enclosure_dict['has_outdoor']:
        _add_epw_data(epw, rel_air_temps, rel_rad_temps, rel_humids, rel_speeds,
                      base_a_per, use_10m_wind_speed)

    # apply the analysis periods if it is specified
    if analysis_period is not None and base_a_per != analysis_period:
        a_per = analysis_period
        rel_air_temps = [data.filter_by_analysis_period(a_per) for data in rel_air_temps]
        rel_rad_temps = [data.filter_by_analysis_period(a_per) for data in rel_rad_temps]
        if include_humidity:
            rel_humids = [data.filter_by_analysis_period(a_per) for data in rel_humids]
        new_rel_speeds = []
        for a_spd in rel_speeds:
            new_a_spd = a_spd.filter_by_analysis_period(a_per) \
                if isinstance(a_spd, HourlyContinuousCollection) else a_spd
            new_rel_speeds.append(new_a_spd)
        rel_speeds = new_rel_speeds

    # loop through the sensors and select the relevant data collections
    pt_air_temps, pt_rad_temps, pt_humids, pt_speeds = [], [], [], []
    for pt_i in enclosure_dict['sensor_indices']:
        pt_air_temps.append(rel_air_temps[pt_i])
        pt_rad_temps.append(rel_rad_temps[pt_i])
        if include_humidity:
            pt_humids.append(rel_humids[pt_i])
        pt_speeds.append(rel_speeds[pt_i])
    return pt_air_temps, pt_rad_temps, pt_humids, pt_speeds, base_a_per


def _values_to_data(values, base_period, data_type, data_units):
    """Load an array of values to a data collection.

    Args:
        values: An array of numbers.
        base_period: An AnalysisPeriod to be used for data collection.
        data_type: The class of the data type for the values.
        data_units: The units of the values.
    """
    if isinstance(values, list):
        header = Header(data_type(), data_units, base_period)
        return HourlyContinuousCollection(header, values)
    return values


def _add_epw_data(epw, rel_air_temps, rel_rad_temps, rel_humids, rel_speeds,
                  base_a_per, use_10m_wind_speed):
    """Add EPW data to zone data collections and align it with these collections."""
    rel_air_temps.append(epw.dry_bulb_temperature)
    out_l_mrt = (epw.dry_bulb_temperature + epw.sky_temperature) / 2
    rel_rad_temps.append(out_l_mrt)
    rel_humids.append(epw.relative_humidity)
    if use_10m_wind_speed:
        rel_speeds.append(epw.wind_speed)
    else:
        rel_speeds.append(epw.wind_speed * (2 / 3))  # conversion used by UTCI
    if not base_a_per.is_annual:  # apply sim analysis period to the annual EPW data
        rel_air_temps[-1] = rel_air_temps[-1].filter_by_analysis_period(base_a_per)
        rel_rad_temps[-1] = rel_rad_temps[-1].filter_by_analysis_period(base_a_per)
        rel_humids[-1] = rel_humids[-1].filter_by_analysis_period(base_a_per)
        rel_speeds[-1] = rel_speeds[-1].filter_by_analysis_period(base_a_per)
    if base_a_per.timestep != 1:  # interpolate the EPW data to timestep
        t_step = base_a_per.timestep
        rel_air_temps[-1] = rel_air_temps[-1].interpolate_to_timestep(t_step)
        rel_rad_temps[-1] = rel_rad_temps[-1].interpolate_to_timestep(t_step)
        rel_humids[-1] = rel_humids[-1].interpolate_to_timestep(t_step)
        rel_speeds[-1] = rel_speeds[-1].interpolate_to_timestep(t_step)