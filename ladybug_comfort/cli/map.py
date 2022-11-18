"""Create spatial thermal maps using EnergyPlus and Radiance results."""
import click
import sys
import logging
import json
import os
import shutil

from ladybug.epw import EPW
from ladybug.legend import LegendParameters
from ladybug.color import Colorset
from ladybug.datacollection import HourlyContinuousCollection, \
    HourlyDiscontinuousCollection
from ladybug.header import Header
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.datatype.energyflux import MetabolicRate
from ladybug.datatype.rvalue import ClothingInsulation
from ladybug.datatype.temperature import OperativeTemperature, \
    StandardEffectiveTemperature, Temperature, UniversalThermalClimateIndex
from ladybug.datatype.thermalcondition import PredictedMeanVote, \
    ThermalCondition, ThermalConditionElevenPoint
from ladybug.datatype.temperaturedelta import OperativeTemperatureDelta
from ladybug.datatype.fraction import Fraction

from ladybug_comfort.map.irr import irradiance_contrib_map
from ladybug_comfort.map.mrt import shortwave_mrt_map, longwave_mrt_map
from ladybug_comfort.map.air import air_map
from ladybug_comfort.map.tcp import tcp_model_schedules, tcp_total
from ladybug_comfort.map._enclosure import _parse_enclosure_info, _values_to_data
from ladybug_comfort.collection.pmv import PMV, _PMVnoSET
from ladybug_comfort.collection.adaptive import Adaptive, PrevailingTemperature
from ladybug_comfort.collection.utci import UTCI

from ._helper import load_values, load_analysis_period_str, \
    load_pmv_par_str, load_adaptive_par_str, load_utci_par_str, \
    load_solarcal_par_str, thermal_map_csv, _data_to_ill

_logger = logging.getLogger(__name__)


@click.group(help='Commands for creating spatial thermal maps.')
def map():
    pass


@map.command('pmv')
@click.argument('result-sql', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('enclosure-info', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('epw-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--total-irradiance', '-tr', help='Path to an .ill file output by '
              'Radiance containing total irradiance for each sensor in the '
              'enclosure-info. If unspecified, no shortwave solar will be '
              'assumed for the study.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--direct-irradiance', '-dr', help='Path to an .ill file output by '
              'Radiance containing direct irradiance for each sensor in the '
              'enclosure-info. If unspecified, all shortwave will be assumed '
              'to be indirect.', default=None,
              type=click.Path(file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--ref-irradiance', '-rr', help='Path to an .ill file output by Radiance '
              'containing total ground-reflected irradiance for each sensor in the '
              'enclosure-info. If unspecified, a default ground reflectance of 0.25 '
              'will be assumed for the study.', default=None,
              type=click.Path(file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--sun-up-hours', '-sh', help='Path to a sun-up-hours.txt file output by '
              'Radiance. Required if any irradiance options are provided.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--air-speed', '-v', help='A single number for air speed in m/s or a '
              'string of a JSON array with numbers that align with the result-sql '
              'reporting period. If unspecified, 0.1 m/s will be used.',
              default=None, type=str)
@click.option('--met-rate', '-m', help='A single number for metabolic rate in met '
              'or a string of a JSON array with numbers that align with the '
              'result-sql reporting period. If unspecified, 1.1 met will be used.',
              default=None, type=str)
@click.option('--clo-value', '-c', help='A single number for clothing level in clo '
              'or a string of a JSON array with numbers that align with the '
              'result-sql reporting period. If unspecified, 0.7 clo will be used.',
              default=None, type=str)
@click.option('--run-period', '-rp', help='An AnalysisPeriod string to dictate the '
              'start and end of the analysis (eg. "6/21 to 9/21 between 8 and 16 @1"). '
              'If unspecified, results will be generated for the entire run period of '
              'the result-sql.', default=None, type=str)
@click.option('--write-op-map/--write-set-map', ' /-set', help='Flag to note whether '
              'the output temperature CSV should record Operative Temperature '
              'or Standard Effective Temperature (SET). SET is relatively intense '
              'to compute and so only recording Operative Temperature can greatly '
              'reduce run time, particularly when air speeds are low. However, SET '
              'accounts for all 6 PMV model inputs and so is a more representative '
              '"feels-like" temperature for the PMV model.', default=True)
@click.option('--solarcal-par', '-sp', help='A SolarCalParameter string to customize '
              'the assumptions of the SolarCal model.', default=None, type=str)
@click.option('--comfort-par', '-cp', help='A PMVParameter string to customize the '
              'assumptions of the PMV model.', default=None, type=str)
@click.option('--folder', '-f', help='Folder into which the result CSV files will be '
              'written. If None, files will be written to a "thermal_map" sub-folder in'
              'same directory as the result-sql.', default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output the paths to the '
              'generated CSV files. By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def pmv(result_sql, enclosure_info, epw_file,
        total_irradiance, direct_irradiance, ref_irradiance, sun_up_hours,
        air_speed, met_rate, clo_value, write_op_map,
        run_period, comfort_par, solarcal_par, folder, log_file):
    """Get CSV files with maps of PMV comfort from EnergyPlus and Radiance results.

    \b
    Args:
        result_sql: Path to an SQLite file that was generated by EnergyPlus.
            This file must contain hourly or sub-hourly results for zone comfort
            variables.
        enclosure_info: Path to a JSON file containing information about the radiant
            enclosure that sensor points belong to.
        epw_file: Path to an .epw file, used to estimate conditions for any outdoor
            sensors and to provide sun positions.
    """
    try:
        # load the EPW object, run period, air speed, and other parameters
        epw_obj = EPW(epw_file)
        run_period = load_analysis_period_str(run_period)
        air_speed = load_values(air_speed)
        met_rate = load_values(met_rate)
        clo_value = load_values(clo_value)
        solarcal_par = load_solarcal_par_str(solarcal_par)
        comfort_par = load_pmv_par_str(comfort_par)

        # load and align the thermal results from the result_sql file
        pt_air_temps, pt_rad_temps, pt_humids, pt_speeds, a_per = _parse_enclosure_info(
            enclosure_info, result_sql, epw_obj, run_period, air_speed,
            include_humidity=True)

        # adjust the radiant temperature for shortwave solar
        if total_irradiance is not None and os.path.isfile(total_irradiance):
            assert sun_up_hours is not None and os.path.isfile(sun_up_hours), \
                'Sun up hours must be specified when total irradiance is specified.'
            pt_rad_temps = shortwave_mrt_map(
                epw_obj.location, pt_rad_temps, sun_up_hours,
                total_irradiance, direct_irradiance, ref_irradiance,
                solarcal_par=solarcal_par, indirect_is_total=True)

        # convert any input lists of clothing or met to data collections
        met_rate = _values_to_data(met_rate, a_per, MetabolicRate, 'met')
        clo_value = _values_to_data(clo_value, a_per, ClothingInsulation, 'clo')
        if run_period is not None and a_per != run_period:
            met_rate = met_rate.filter_by_analysis_period(run_period) \
                if isinstance(met_rate, HourlyContinuousCollection) else met_rate
            clo_value = clo_value.filter_by_analysis_period(run_period) \
                if isinstance(clo_value, HourlyContinuousCollection) else clo_value

        # run the collections through the PMV model and output results
        comf_class = _PMVnoSET if write_op_map else PMV
        temperature, condition, condition_intensity = [], [], []
        for t_a, rh, t_r, vel in zip(pt_air_temps, pt_humids, pt_rad_temps, pt_speeds):
            pmv_obj = comf_class(
                t_a, rh, t_r, vel, met_rate, clo_value, comfort_parameter=comfort_par)
            condition.append(pmv_obj.thermal_condition)
            condition_intensity.append(pmv_obj.predicted_mean_vote)
            if write_op_map:
                temperature.append(pmv_obj.operative_temperature)
            else:
                temperature.append(pmv_obj.standard_effective_temperature)

        # write out the final results to CSV files
        if folder is None:
            folder = os.path.join(os.path.dirname(result_sql), 'thermal_map')
        result_file_dict = thermal_map_csv(
            folder, temperature, condition, condition_intensity)
        log_file.write(json.dumps(result_file_dict))
    except Exception as e:
        _logger.exception('Failed to run PMV model comfort map.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@map.command('adaptive')
@click.argument('result-sql', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('enclosure-info', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('epw-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--total-irradiance', '-tr', help='Path to an .ill file output by '
              'Radiance containing total irradiance for each sensor in the '
              'enclosure-info. If unspecified, no shortwave solar will be '
              'assumed for the study.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--direct-irradiance', '-dr', help='Path to an .ill file output by '
              'Radiance containing direct irradiance for each sensor in the '
              'enclosure-info. If unspecified, all shortwave will be assumed '
              'to be indirect.', default=None,
              type=click.Path(file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--ref-irradiance', '-rr', help='Path to an .ill file output by Radiance '
              'containing total ground-reflected irradiance for each sensor in the '
              'enclosure-info. If unspecified, a default ground reflectance of 0.25 '
              'will be assumed for the study.', default=None,
              type=click.Path(file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--sun-up-hours', '-sh', help='Path to a sun-up-hours.txt file output by '
              'Radiance. Required if any irradiance options are provided.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--air-speed', '-v', help='A single number for air speed in m/s or a '
              'string of a JSON array with numbers that align with the result-sql '
              'reporting period. If unspecified, 0.1 m/s will be used.',
              default=None, type=str)
@click.option('--run-period', '-rp', help='An AnalysisPeriod string to dictate the '
              'start and end of the analysis (eg. "6/21 to 9/21 between 8 and 16 @1"). '
              'If unspecified, results will be generated for the entire run period of '
              'the result-sql.', default=None, type=str)
@click.option('--solarcal-par', '-sp', help='A SolarCalParameter string to customize '
              'the assumptions of the SolarCal model.', default=None, type=str)
@click.option('--comfort-par', '-cp', help='An AdaptiveParameter string to customize '
              'the assumptions of the Adaptive comfort model.', default=None, type=str)
@click.option('--folder', '-f', help='Folder into which the result CSV files will be '
              'written. If None, files will be written to a "thermal_map" sub-folder in'
              'same directory as the result-sql.', default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output the paths to the '
              'generated CSV files. By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def adaptive(result_sql, enclosure_info, epw_file,
             total_irradiance, direct_irradiance, ref_irradiance, sun_up_hours,
             air_speed, run_period, comfort_par, solarcal_par, folder, log_file):
    """Get CSV files with maps of Adaptive comfort from EnergyPlus and Radiance results.

    \b
    Args:
        result_sql: Path to an SQLite file that was generated by EnergyPlus.
            This file must contain hourly or sub-hourly results for zone comfort
            variables.
        enclosure_info: Path to a JSON file containing information about the radiant
            enclosure that sensor points belong to.
        epw_file: Path to an .epw file, used to estimate conditions for any outdoor
            sensors and to provide prevailing outdoor temperature for the adaptive
            comfort model.
    """
    try:
        # load the EPW object, run period, air speed, and other parameters
        epw_obj = EPW(epw_file)
        run_period = load_analysis_period_str(run_period)
        air_speed = load_values(air_speed)
        solarcal_par = load_solarcal_par_str(solarcal_par)
        comfort_par = load_adaptive_par_str(comfort_par)

        # load and align the thermal results from the result_sql file
        pt_air_temps, pt_rad_temps, _, pt_speeds, _ = _parse_enclosure_info(
            enclosure_info, result_sql, epw_obj, run_period, air_speed)

        # adjust the radiant temperature for shortwave solar
        if total_irradiance is not None and os.path.isfile(total_irradiance):
            assert sun_up_hours is not None and os.path.isfile(sun_up_hours), \
                'Sun up hours must be specified when total irradiance is specified.'
            pt_rad_temps = shortwave_mrt_map(
                epw_obj.location, pt_rad_temps, sun_up_hours,
                total_irradiance, direct_irradiance, ref_irradiance,
                solarcal_par=solarcal_par, indirect_is_total=True)

        # compute previaling outdoor temperature so it's not recomputed for each sensor
        avg_month = comfort_par.avg_month_or_running_mean \
            if comfort_par is not None else True
        prev_obj = PrevailingTemperature(epw_obj.dry_bulb_temperature, avg_month)
        prevail_temp = prev_obj.get_aligned_prevailing(pt_air_temps[0])

        # run the collections through the Adaptive model and output results
        temperature, condition, condition_intensity = [], [], []
        for t_air, t_rad, vel in zip(pt_air_temps, pt_rad_temps, pt_speeds):
            adaptive_obj = Adaptive.from_air_and_rad_temp(
                prevail_temp, t_air, t_rad, vel, comfort_parameter=comfort_par)
            temperature.append(adaptive_obj.operative_temperature)
            condition.append(adaptive_obj.thermal_condition)
            condition_intensity.append(adaptive_obj.degrees_from_neutral)

        # write out the final results to CSV files
        if folder is None:
            folder = os.path.join(os.path.dirname(result_sql), 'thermal_map')
        result_file_dict = thermal_map_csv(
            folder, temperature, condition, condition_intensity)
        log_file.write(json.dumps(result_file_dict))
    except Exception as e:
        _logger.exception('Failed to run Adaptive model comfort map.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@map.command('utci')
@click.argument('result-sql', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('enclosure-info', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('epw-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--total-irradiance', '-tr', help='Path to an .ill file output by '
              'Radiance containing total irradiance for each sensor in the '
              'enclosure-info. If unspecified, no shortwave solar will be '
              'assumed for the study.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--direct-irradiance', '-dr', help='Path to an .ill file output by '
              'Radiance containing direct irradiance for each sensor in the '
              'enclosure-info. If unspecified, all shortwave will be assumed '
              'to be indirect.', default=None,
              type=click.Path(file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--ref-irradiance', '-rr', help='Path to an .ill file output by Radiance '
              'containing total ground-reflected irradiance for each sensor in the '
              'enclosure-info. If unspecified, a default ground reflectance of 0.25 '
              'will be assumed for the study.', default=None,
              type=click.Path(file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--sun-up-hours', '-sh', help='Path to a sun-up-hours.txt file output by '
              'Radiance. Required if any irradiance options are provided.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--wind-speed', '-v', help='A single number for meteorological wind '
              'speed in m/s or a string of a JSON array with numbers that align with '
              'the result-sql reporting period. This will be used for all indoor '
              'comfort evaluation while the EPW wind speed will be used for the '
              'outdoors. If unspecified, 0.5 m/s will be used.', default=None, type=str)
@click.option('--run-period', '-rp', help='An AnalysisPeriod string to dictate the '
              'start and end of the analysis (eg. "6/21 to 9/21 between 8 and 16 @1"). '
              'If unspecified, results will be generated for the entire run period of '
              'the result-sql.', default=None, type=str)
@click.option('--solarcal-par', '-sp', help='A SolarCalParameter string to customize '
              'the assumptions of the SolarCal model.', default=None, type=str)
@click.option('--comfort-par', '-cp', help='An UTCIParameter string to customize the '
              'assumptions of the Adaptrive comfort model.', default=None, type=str)
@click.option('--folder', '-f', help='Folder into which the result CSV files will be '
              'written. If None, files will be written to a "thermal_map" sub-folder in'
              'same directory as the result-sql.', default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output the paths to the '
              'generated CSV files. By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def utci(result_sql, enclosure_info, epw_file,
         total_irradiance, direct_irradiance, ref_irradiance, sun_up_hours,
         wind_speed, run_period, comfort_par, solarcal_par, folder, log_file):
    """Get CSV files with maps of UTCI comfort from EnergyPlus and Radiance results.

    \b
    Args:
        result_sql: Path to an SQLite file that was generated by EnergyPlus.
            This file must contain hourly or sub-hourly results for zone comfort
            variables.
        enclosure_info: Path to a JSON file containing information about the radiant
            enclosure that sensor points belong to.
        epw_file: Path to an .epw file, used to estimate conditions for any outdoor
            sensors and to provide sun positions.
    """
    try:
        # load the EPW object, run period, air speed, and other parameters
        epw_obj = EPW(epw_file)
        run_period = load_analysis_period_str(run_period)
        wind_speed = load_values(wind_speed)
        solarcal_par = load_solarcal_par_str(solarcal_par)
        comfort_par = load_utci_par_str(comfort_par)

        # load and align the thermal results from the result_sql file
        pt_air_temps, pt_rad_temps, pt_humids, pt_speeds, _ = _parse_enclosure_info(
            enclosure_info, result_sql, epw_obj, run_period, wind_speed,
            include_humidity=True, use_10m_wind_speed=True)

        # adjust the radiant temperature for shortwave solar
        if total_irradiance is not None and os.path.isfile(total_irradiance):
            assert sun_up_hours is not None and os.path.isfile(sun_up_hours), \
                'Sun up hours must be specified when total irradiance is specified.'
            pt_rad_temps = shortwave_mrt_map(
                epw_obj.location, pt_rad_temps, sun_up_hours,
                total_irradiance, direct_irradiance, ref_irradiance,
                solarcal_par=solarcal_par, indirect_is_total=True)

        # run the collections through the UTCI model and output results
        temperature, condition, condition_intensity = [], [], []
        for t_a, rh, t_r, vel in zip(pt_air_temps, pt_humids, pt_rad_temps, pt_speeds):
            utci_obj = UTCI(t_a, rh, t_r, vel, comfort_parameter=comfort_par)
            temperature.append(utci_obj.universal_thermal_climate_index)
            condition.append(utci_obj.thermal_condition)
            condition_intensity.append(utci_obj.thermal_condition_eleven_point)

        # write out the final results to CSV files
        if folder is None:
            folder = os.path.join(os.path.dirname(result_sql), 'thermal_map')
        result_file_dict = thermal_map_csv(
            folder, temperature, condition, condition_intensity)
        log_file.write(json.dumps(result_file_dict))
    except Exception as e:
        _logger.exception('Failed to run UTCI model comfort map.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@map.command('irradiance-contrib')
@click.argument('result-sql', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('direct-specular', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('indirect-specular', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('ref-specular', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('indirect-diffuse', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('ref-diffuse', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('sun-up-hours', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--aperture-id', '-id', help='Text string for the identifier of the '
              'aperture associated with the irradiance. If unspecified, it will the '
              'first aperture found in the result-sql, essentially assuming there is '
              'only one dynamic group in the file.', default=None, type=str)
@click.option('--folder', '-f', help='Folder into which the result CSV files will be '
              'written. If None, files will be written to a "contrib" sub-folder in'
              'same directory as the result-sql.', default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output the paths to the '
              'generated CSV files. By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def irradiance_contrib(
    result_sql, direct_specular, indirect_specular, ref_specular,
    indirect_diffuse, ref_diffuse, sun_up_hours, aperture_id, folder, log_file
):
    """Get CSV files with irradiance contributions from dynamic windows.

    \b
    Args:
        result_sql: Path to an SQLite file that was generated by EnergyPlus.
            This file must contain results for window transmittance.
        direct_specular: Path to an .ill file output by Radiance containing direct
            irradiance for the specular version of the aperture group.
        indirect_specular: Path to an .ill file output by Radiance containing
            the indirect irradiance for the specular version of the aperture group.
        ref_specular: Path to an .ill file output by Radiance containing ground-reflected
            irradiance for the specular version of the aperture group.
        indirect_diffuse: Path to an .ill file output by Radiance containing
            the indirect irradiance for the diffuse version of the aperture group.
        ref_diffuse: Path to an .ill file output by Radiance containing ground-reflected
            irradiance for the diffuse version of the aperture group.
        sun_up_hours: Path to a sun-up-hours.txt file output by an annual
            irradiance simulation.
    """
    try:
        # compute the irradiance contribution values from the input
        direct_mtx, indirect_mtx, ref_mtx = irradiance_contrib_map(
            result_sql, direct_specular, indirect_specular, ref_specular,
            indirect_diffuse, ref_diffuse, sun_up_hours, aperture_id)

        # prepare the files and directory where the results will be written
        out_folder = folder if folder is not None else \
            os.path.join(os.path.dirname(result_sql), 'contrib')
        if not os.path.isdir(out_folder):
            os.mkdir(out_folder)
        direct_file = os.path.join(out_folder, 'direct.ill')
        indirect_file = os.path.join(out_folder, 'indirect.ill')
        ref_file = os.path.join(out_folder, 'reflected.ill')

        # write the irradiance matrices into CSV files
        _data_to_ill(direct_mtx, direct_file)
        _data_to_ill(indirect_mtx, indirect_file)
        _data_to_ill(ref_mtx, ref_file)
        log_file.write(json.dumps([direct_file, indirect_file, ref_file]))
    except Exception as e:
        _logger.exception('Failed to run Shortwave MRT Delta map.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@map.command('shortwave-mrt')
@click.argument('epw-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('indirect-irradiance', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('direct-irradiance', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('ref-irradiance', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('sun-up-hours', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--contributions', '-c', help='An optional folder containing '
              'sub-folders of irradiance contributions from dynamic aperture groups. '
              'There should be one sub-folder per window groups and each one should '
              'contain three .ill files named direct.ill, indirect.ill and '
              'reflected.ill. If specified, these will be added to the irradiance '
              'inputs before computing shortwave MRT deltas.',
              default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--transmittance-contribs', '-tc', help='An optional folder containing '
              'a transmittance schedule JSON and sub-folders of irradiance results '
              'that exclude the shade from the calculation. There should be one '
              'sub-folder per window groups and each one should contain three .ill '
              'files named direct.ill, indirect.ill and reflected.ill. If specified, '
              'these will be added to the irradiance inputs before computing shortwave '
              'MRT deltas.', default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--trans-schedule-json', '-ts', help='An optional path to a transmittance '
              'schedule JSON output by the honeybee-energy model-transmittance-schedules'
              ' command, which is coordinated with the --transmittance-contribs. '
              'If unspecified, it will be assumed that this JSON already exists in '
              'the root of the --transmittance-contribs with a name schedules.json.',
              default=None, type=click.Path(exists=False, file_okay=True, dir_okay=False,
                                            resolve_path=True))
@click.option('--run-period', '-rp', help='An AnalysisPeriod string to dictate the '
              'start and end of the analysis (eg. "6/21 to 9/21 between 8 and 16 @1"). '
              'If unspecified, results will be annual.', default=None, type=str)
@click.option('--solarcal-par', '-sp', help='A SolarCalParameter string to customize '
              'the assumptions of the SolarCal model.', default=None, type=str)
@click.option('--is-indirect/--indirect-is-total', ' /-t', help='Flag to '
              'note whether the indirect-irradiance argument is actually the total '
              'irradiance, in which case the direct irradiance should be subtracted '
              'from it to get indirect irradiance.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the CSV matrix '
              'of MRT deltas. By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def shortwave_mrt(
        epw_file, indirect_irradiance, direct_irradiance, ref_irradiance,
        sun_up_hours, contributions, transmittance_contribs, trans_schedule_json,
        run_period, solarcal_par, is_indirect, output_file):
    """Get CSV files with maps of shortwave MRT Deltas from Radiance results.

    \b
    Args:
        epw_file: Path to an .epw file, used to estimate conditions for any outdoor
            sensors and to provide sun positions.
        indirect_irradiance: Path to an .ill file output by Radiance containing
            the indirect irradiance for each sensor. Alternatively, if the
            --indirect-is-total input is used, then this input should be the total
            irradiance for each sensor.
        direct_irradiance: Path to an .ill file output by Radiance containing direct
            irradiance for each sensor.
        ref_irradiance: Path to an .ill file output by Radiance containing
            ground-reflected irradiance for each sensor.
        sun_up_hours: Path to a sun-up-hours.txt file output by an annual
            irradiance simulation.
    """
    try:
        # load the EPW object, run period, and other parameters
        epw_obj = EPW(epw_file)
        run_period = load_analysis_period_str(run_period)
        run_period = run_period if run_period is not None else AnalysisPeriod()
        solarcal_par = load_solarcal_par_str(solarcal_par)

        # create a dummy longwave MRT matrix to pass to the shortwave calculator
        header = Header(Temperature(), 'C', run_period)
        lt_values = [0] * len(run_period)
        pt_rad_temps = [HourlyContinuousCollection(header, lt_values)] \
            if run_period.st_hour == 0 and run_period.end_hour == 23 else \
            [HourlyDiscontinuousCollection(header, lt_values, run_period.datetimes)]

        # if the trans_schedule_json is specified, copy it to the contrib folder
        if trans_schedule_json is not None and os.path.isfile(trans_schedule_json):
            if transmittance_contribs is not None and \
                    os.path.isdir(transmittance_contribs):
                sch_json = os.path.join(transmittance_contribs, 'schedules.json')
                shutil.copyfile(trans_schedule_json, sch_json)

        # adjust the radiant temperature for shortwave solar
        is_total = not is_indirect
        d_mrt_temps = shortwave_mrt_map(
            epw_obj.location, pt_rad_temps, sun_up_hours,
            indirect_irradiance, direct_irradiance, ref_irradiance,
            contributions, transmittance_contribs,
            solarcal_par=solarcal_par, indirect_is_total=is_total)

        # write out the final results to CSV files
        if len(d_mrt_temps) == 0:  # no sun-up hours; just create a blank file
            output_file.write('')
        else:
            for mrt_d in d_mrt_temps:
                output_file.write(','.join(str(v) for v in mrt_d))
                output_file.write('\n')
    except Exception as e:
        _logger.exception('Failed to run Shortwave MRT Delta map.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@map.command('longwave-mrt')
@click.argument('result-sql', type=click.Path(
    file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('view-factors', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('modifiers', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('enclosure-info', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('epw-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--run-period', '-rp', help='An AnalysisPeriod string to dictate the '
              'start and end of the analysis (eg. "6/21 to 9/21 between 8 and 16 @1"). '
              'If unspecified, results will be annual.', default=None, type=str)
@click.option('--output-file', '-f', help='Optional file to output the CSV matrix '
              'of longwave MRT. By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def longwave_mrt(result_sql, view_factors, modifiers, enclosure_info, epw_file,
                 run_period, output_file):
    """Get CSV files with maps of longwave MRT from Radiance and EnergyPlus results.

    \b
    Args:
        result_sql: Path to an SQLite file that was generated by EnergyPlus.
            This file must contain hourly or sub-hourly results for zone comfort
            variables.
        view_factors: CSV of spherical view factors to the surfaces in the result-sql.
        modifiers: Path to modifiers file that aligns with the view-factors.
        enclosure_info: Path to a JSON file containing information about the radiant
            enclosure that sensor points belong to.
        epw_file: Path to an .epw file, used to estimate conditions for any outdoor
            sensors and to provide sun positions.
    """
    try:
        # load the run period
        run_period = load_analysis_period_str(run_period)
        run_period = run_period if run_period is not None else AnalysisPeriod()

        # get the longwave MRT data
        mrt_temps = longwave_mrt_map(
            enclosure_info, modifiers, result_sql, view_factors, epw_file, run_period)

        # write out the final results to CSV files
        for mrt_d in mrt_temps:
            output_file.write(','.join(str(v) for v in mrt_d))
            output_file.write('\n')
    except Exception as e:
        _logger.exception('Failed to run Longwave MRT map.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@map.command('air')
@click.argument('result-sql', type=click.Path(
    file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('enclosure-info', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('epw-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--run-period', '-rp', help='An AnalysisPeriod string to dictate the '
              'start and end of the analysis (eg. "6/21 to 9/21 between 8 and 16 @1"). '
              'If unspecified, results will be generated for the entire run period of '
              'the result-sql.', default=None, type=str)
@click.option('--air-temperature/--relative-humidity', ' /-rh', help='Flag to '
              'note whether the the output matrix should be with relative humidity '
              'values instead of air temperature values.',
              default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the CSV matrix '
              'of values. By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def air_temperature(result_sql, enclosure_info, epw_file,
                    run_period, air_temperature, output_file):
    """Get CSV files with maps of air temperatures or humidity from EnergyPlus results.

    \b
    Args:
        result_sql: Path to an SQLite file that was generated by EnergyPlus.
            This file must contain hourly or sub-hourly results for zone comfort
            variables.
        enclosure_info: Path to a JSON file containing information about the radiant
            enclosure that sensor points belong to.
        epw_file: Path to an .epw file, used to estimate conditions for any outdoor
            sensors and to provide sun positions.
    """
    try:
        # load the run period
        run_period = load_analysis_period_str(run_period)
        run_period = run_period if run_period is not None else AnalysisPeriod()

        # get the air data
        humidity = not air_temperature
        air_data = air_map(enclosure_info, result_sql, epw_file, run_period, humidity)

        # write out the final results to CSV files
        for air_d in air_data:
            output_file.write(','.join(str(v) for v in air_d))
            output_file.write('\n')
    except Exception as e:
        _logger.exception('Failed to run Air Temperature map.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@map.command('map-result-info')
@click.argument('comfort-model', type=str)
@click.option('--run-period', '-rp', help='The AnalysisPeriod string that dictates the '
              'start and end of the analysis (eg. "6/21 to 9/21 between 8 and 16 @1"). '
              'If unspecified, it will be assumed results are for a full year.',
              default=None, type=str)
@click.option('--qualifier', '-q', help='Text for any options used on the comfort '
              'map simulation that change the output data type of results. For example, '
              'the write-set-map text of the pmv map can be passed here to ensure '
              'the output of this command is for SET instead of operative temperature.',
              default=None, type=str, multiple=True)
@click.option('--folder', '-f', help='Result folder into which JSON info files will be '
              'written. If None, the info will only be output to the output-file and '
              'not written into result sub folders.', default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional file to output the JSON '
              'string of the result info. By default, it will be printed to stdout',
              type=click.File('w'), default='-', show_default=True)
def map_result_info(comfort_model, run_period, qualifier, folder, log_file):
    """Get a JSON that specifies the data type and units for comfort map outputs.

    This JSON is needed by interfaces to correctly parse comfort map results.

    \b
    Args:
        comfort_model: Text for the comfort model of the thermal mapping simulation.
            Choose from: pmv, adaptive, utci.
    """
    try:
        # parse the run period
        run_period = load_analysis_period_str(run_period)
        run_period = run_period if run_period is not None else AnalysisPeriod()

        # get the data type and units from the comfort model
        comfort_model = comfort_model.lower()
        cond, cond_units = ThermalCondition(), 'condition'
        if comfort_model == 'pmv':
            temp, temp_units = OperativeTemperature(), 'C'
            if 'write-set-map' in qualifier:
                temp = StandardEffectiveTemperature()
            cond_i, cond_i_units = PredictedMeanVote(), 'PMV'
        elif comfort_model == 'adaptive':
            temp, temp_units = OperativeTemperature(), 'C'
            cond_i, cond_i_units = OperativeTemperatureDelta(), 'dC'
        elif comfort_model == 'utci':
            temp, temp_units = UniversalThermalClimateIndex(), 'C'
            cond_i, cond_i_units = ThermalConditionElevenPoint(), 'condition'
        else:
            raise ValueError(
                'Comfort model "{}" not recognized. Choose from: {}.'.format(
                    comfort_model, ('pmv', 'adaptive', 'utci')))

        # build up the dictionary of data headers
        temp_header = Header(temp, temp_units, run_period)
        cond_header = Header(cond, cond_units, run_period)
        cond_i_header = Header(cond_i, cond_i_units, run_period)
        result_info_dict = {
            'temperature': temp_header.to_dict(),
            'condition': cond_header.to_dict(),
            'condition_intensity': cond_i_header.to_dict()
        }

        # build up dictionaries of visualization metadata
        tcp_lpar = LegendParameters(colors=Colorset.annual_comfort())
        hsp_lpar = LegendParameters(colors=Colorset.heat_sensation())
        csp_lpar = LegendParameters(colors=Colorset.cold_sensation())
        metric_info_dict = {
            'TCP': {
                'type': 'VisualizationMetaData',
                'data_type': Fraction('Thermal Comfort Percentage').to_dict(),
                'unit': '%',
                'legend_parameters': tcp_lpar.to_dict()
            },
            'HSP': {
                'type': 'VisualizationMetaData',
                'data_type': Fraction('Heat Sensation Percentage').to_dict(),
                'unit': '%',
                'legend_parameters': hsp_lpar.to_dict()
            },
            'CSP': {
                'type': 'VisualizationMetaData',
                'data_type': Fraction('Cold Sensation Percentage').to_dict(),
                'unit': '%',
                'legend_parameters': csp_lpar.to_dict()
            }
        }

        # write the JSON into result sub-folders
        if folder is not None:
            if not os.path.isdir(folder):
                os.makedirs(folder)
            for metric in ('temperature', 'condition', 'condition_intensity'):
                file_path = os.path.join(folder, '{}.json'.format(metric))
                with open(file_path, 'w') as fp:
                    json.dump(result_info_dict[metric], fp, indent=4)
            for metric in ('TCP', 'HSP', 'CSP'):
                file_path = os.path.join(folder, '{}.json'.format(metric))
                with open(file_path, 'w') as fp:
                    json.dump(metric_info_dict[metric], fp, indent=4)

            # write the VTK config file
            config_file = os.path.join(folder, 'config.json')
            cfg = _tcp_config()
            with open(config_file, 'w') as outf:
                json.dump(cfg, outf)

        log_file.write(json.dumps(result_info_dict))
    except Exception as e:
        _logger.exception('Failed to write thermal map info.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@map.command('tcp')
@click.argument('condition-csv', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('enclosure-info', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--schedule', '-s', help='An optional path to a CSV file to specify '
              'the relevant times during which comfort should be evaluated. If '
              'specified, this will override the --occ-schedule-json for both '
              'indoor and outdoor conditions. If both this option and the '
              '--occ-schedule-json are unspecified, it will be assumed that all '
              'times are relevant.',
              default=None, type=click.Path(exists=False, file_okay=True, dir_okay=False,
                                            resolve_path=True))
@click.option('--occ-schedule-json', '-occ', help='Path to an occupancy schedule '
              'JSON output by the honeybee-energy model-occ-schedules command. This '
              'JSON derives the relevant times based on the occupancy schedules of the '
              'energy model and assumes that all outdoor times are relevant. '
              'If both this option and the --schedule are unspecified, all '
              'times of the study will be considered occupied.',
              default=None, type=click.Path(exists=False, file_okay=True, dir_okay=False,
                                            resolve_path=True))
@click.option('--folder', '-f', help='Result folder into which the result CSV files '
              'will be written. If None, they will be output into the same folder as '
              'the condition-csv.', default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output the paths to the '
              'CSV files. By default, it will be printed to stdout',
              type=click.File('w'), default='-', show_default=True)
def tcp(condition_csv, enclosure_info, schedule, occ_schedule_json, folder, log_file):
    """Compute Thermal Comfort Percent (TCP) from thermal mapping results.

    \b
    Args:
        condition_csv: Path to a CSV file of thermal conditions output by a
            thermal mapping command.
        enclosure_info: Path to a JSON file containing information about the radiant
            enclosure that sensor points belong to.
    """
    try:
        # set the default folder if not specified
        if folder is None:
            folder = os.path.dirname(condition_csv)
        if not os.path.isdir(folder):
            os.makedirs(folder)

        # compute thermal comfort percent
        schedule = schedule if schedule and os.path.isfile(schedule) else None
        if schedule is not None or occ_schedule_json is None:
            tcp_list, hsp_list, csp_list = tcp_total(condition_csv, schedule)
        else:
            tcp_list, hsp_list, csp_list = tcp_model_schedules(
                condition_csv, enclosure_info, occ_schedule_json)

        # write the lists into CSV files
        tcp_file = os.path.join(folder, 'tcp.csv')
        hsp_file = os.path.join(folder, 'hsp.csv')
        csp_file = os.path.join(folder, 'csp.csv')
        with open(tcp_file, 'w') as fp:
            fp.write('\n'.join([str(v) for v in tcp_list]))
            fp.write('\n')
        with open(hsp_file, 'w') as fp:
            fp.write('\n'.join([str(v) for v in hsp_list]))
            fp.write('\n')
        with open(csp_file, 'w') as fp:
            fp.write('\n'.join([str(v) for v in csp_list]))
            fp.write('\n')
        log_file.write(json.dumps([tcp_file, hsp_file, csp_file]))
    except Exception as e:
        _logger.exception('Failed to compute TCP.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def _tcp_config():
    """Return vtk-config for a thermal comfort map."""
    return {
        "data": [
            {
                "identifier": "Thermal Comfort Percentage",
                "object_type": "grid",
                "unit": "Percentage",
                "path": 'TCP',
                "hide": False,
                "legend_parameters": {
                    "hide_legend": False,
                    "color_set": "annual_comfort",
                    "label_parameters": {
                        "color": [34, 247, 10],
                        "size": 0,
                        "bold": True
                    }
                }
            },
            {
                "identifier": "Heat Sensation Percentage",
                "object_type": "grid",
                "unit": "Percentage",
                "path": 'HSP',
                "hide": False,
                "legend_parameters": {
                    "hide_legend": False,
                    "color_set": "heat_sensation",
                    "label_parameters": {
                        "size": 0,
                        "color": [34, 247, 10],
                        "bold": True
                    }
                }
            },
            {
                "identifier": "Cold Sensation Percentage",
                "object_type": "grid",
                "unit": "Percentage",
                "path": 'CSP',
                "hide": False,
                "legend_parameters": {
                    "hide_legend": False,
                    "color_set": "cold_sensation",
                    "label_parameters": {
                        "color": [34, 247, 10],
                        "size": 0,
                        "bold": True
                    }
                }
            }
        ]
    }
