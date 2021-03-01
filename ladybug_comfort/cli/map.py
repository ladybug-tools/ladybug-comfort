"""Create spatial thermal maps using EnergyPlus and Radiance results."""
import click
import sys
import logging
import json
import os

from ladybug.epw import EPW
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.header import Header
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.datatype.energyflux import MetabolicRate
from ladybug.datatype.rvalue import ClothingInsulation
from ladybug.datatype.temperature import OperativeTemperature, \
    StandardEffectiveTemperature, UniversalThermalClimateIndex
from ladybug.datatype.thermalcondition import PredictedMeanVote, \
    ThermalCondition, ThermalConditionElevenPoint
from ladybug.datatype.temperaturedelta import OperativeTemperatureDelta

from ladybug_comfort.map.mrt import shortwave_mrt_map
from ladybug_comfort.map.tcp import tcp_model_schedules, tcp_total
from ladybug_comfort.map._enclosure import _parse_enclosure_info, _values_to_data
from ladybug_comfort.collection.pmv import PMV, _PMVnoSET
from ladybug_comfort.collection.adaptive import Adaptive, PrevailingTemperature
from ladybug_comfort.collection.utci import UTCI

from ._helper import _load_values, _load_analysis_period_str, \
    _load_pmv_par_str, _load_adaptive_par_str, _load_utci_par_str, \
    _load_solarcal_par_str, _thermal_map_csv

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
              'enclosure-info. If unspecified, no shortwave solar will be '
              'assumed for the study.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--ref-irradiance', '-rr', help='Path to an .ill file output by Radiance '
              'containing total ground-reflected irradiance for each sensor in the '
              'enclosure-info. If unspecified, a default ground reflectance of 0.25 '
              'will be assumed for the study.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
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
        run_period = _load_analysis_period_str(run_period)
        air_speed = _load_values(air_speed)
        met_rate = _load_values(met_rate)
        clo_value = _load_values(clo_value)
        solarcal_par = _load_solarcal_par_str(solarcal_par)
        comfort_par = _load_pmv_par_str(comfort_par)

        # load and align the thermal results from the result_sql file
        pt_air_temps, pt_rad_temps, pt_humids, pt_speeds, a_per = _parse_enclosure_info(
            enclosure_info, result_sql, epw_obj, run_period, air_speed,
            include_humidity=True)

        # adjust the radiant temperature for shortwave solar
        pt_rad_temps = shortwave_mrt_map(
            epw_obj.location, pt_rad_temps, sun_up_hours,
            total_irradiance, direct_irradiance, ref_irradiance, solarcal_par)

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
        result_file_dict = _thermal_map_csv(
            folder, result_sql, temperature, condition, condition_intensity)
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
              'enclosure-info. If unspecified, no shortwave solar will be '
              'assumed for the study.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--ref-irradiance', '-rr', help='Path to an .ill file output by Radiance '
              'containing total ground-reflected irradiance for each sensor in the '
              'enclosure-info. If unspecified, a default ground reflectance of 0.25 '
              'will be assumed for the study.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
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
        run_period = _load_analysis_period_str(run_period)
        air_speed = _load_values(air_speed)
        solarcal_par = _load_solarcal_par_str(solarcal_par)
        comfort_par = _load_adaptive_par_str(comfort_par)

        # load and align the thermal results from the result_sql file
        pt_air_temps, pt_rad_temps, _, pt_speeds, _ = _parse_enclosure_info(
            enclosure_info, result_sql, epw_obj, run_period, air_speed)

        # adjust the radiant temperature for shortwave solar
        pt_rad_temps = shortwave_mrt_map(
            epw_obj.location, pt_rad_temps, sun_up_hours,
            total_irradiance, direct_irradiance, ref_irradiance, solarcal_par)

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
        result_file_dict = _thermal_map_csv(
            folder, result_sql, temperature, condition, condition_intensity)
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
              'enclosure-info. If unspecified, no shortwave solar will be '
              'assumed for the study.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--ref-irradiance', '-rr', help='Path to an .ill file output by Radiance '
              'containing total ground-reflected irradiance for each sensor in the '
              'enclosure-info. If unspecified, a default ground reflectance of 0.25 '
              'will be assumed for the study.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
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
@click.option('--solarcal-par', '-sp', help='A SolarCalParameter JSON to customize the '
              'assumptions of the SolarCal model.', default=None, type=str)
@click.option('--comfort-par', '-cp', help='An UTCIParameter JSON to customize the '
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
        run_period = _load_analysis_period_str(run_period)
        wind_speed = _load_values(wind_speed)
        solarcal_par = _load_solarcal_par_str(solarcal_par)
        comfort_par = _load_utci_par_str(comfort_par)

        # load and align the thermal results from the result_sql file
        pt_air_temps, pt_rad_temps, pt_humids, pt_speeds, _ = _parse_enclosure_info(
            enclosure_info, result_sql, epw_obj, run_period, wind_speed,
            include_humidity=True, use_10m_wind_speed=True)

        # adjust the radiant temperature for shortwave solar
        pt_rad_temps = shortwave_mrt_map(
            epw_obj.location, pt_rad_temps, sun_up_hours,
            total_irradiance, direct_irradiance, ref_irradiance, solarcal_par)

        # run the collections through the UTCI model and output results
        temperature, condition, condition_intensity = [], [], []
        for t_a, rh, t_r, vel in zip(pt_air_temps, pt_humids, pt_rad_temps, pt_speeds):
            utci_obj = UTCI(t_a, rh, t_r, vel, comfort_parameter=comfort_par)
            temperature.append(utci_obj.universal_thermal_climate_index)
            condition.append(utci_obj.thermal_condition)
            condition_intensity.append(utci_obj.thermal_condition_eleven_point)

        # write out the final results to CSV files
        result_file_dict = _thermal_map_csv(
            folder, result_sql, temperature, condition, condition_intensity)
        log_file.write(json.dumps(result_file_dict))
    except Exception as e:
        _logger.exception('Failed to run Adaptive model comfort map.\n{}'.format(e))
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
        run_period = _load_analysis_period_str(run_period)
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

        # write the JSON into result sub-folders
        if folder is not None:
            if not os.path.isdir(folder):
                os.makedirs(folder)
            for metric in ('temperature', 'condition', 'condition_intensity'):
                file_path = os.path.join(folder, '{}.json'.format(metric))
                with open(file_path, 'w') as fp:
                    json.dump(result_info_dict[metric], fp, indent=4)

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
@click.option('--occ-schedule-json', '-occ', help='Path to an occupancy schedule '
              'JSON output by the honeybee-energy model-occ-schedules command. If '
              'unspecified, all times of the study will be considered occupied.',
              default=None, type=click.Path(exists=True, file_okay=True, dir_okay=False,
                                            resolve_path=True))
@click.option('--folder', '-f', help='Result folder into which the result CSV files '
              'will be written. If None, they will be output into the same folder as '
              'the condition-csv.', default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output the paths to the '
              'CSV files. By default, it will be printed to stdout',
              type=click.File('w'), default='-', show_default=True)
def tcp(condition_csv, enclosure_info, occ_schedule_json, folder, log_file):
    """Compute Thermal Comfort Petcent (TCP) from thermal mapping results.

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
        if occ_schedule_json is None:
            tcp_list, hsp_list, csp_list = tcp_total(condition_csv)
        else:
            tcp_list, hsp_list, csp_list = tcp_model_schedules(
                condition_csv, enclosure_info, occ_schedule_json)

        # write the lists into CSV files
        tcp_file = os.path.join(folder, 'tcp.csv')
        hsp_file = os.path.join(folder, 'hsp.csv')
        csp_file = os.path.join(folder, 'csp.csv')
        with open(tcp_file, 'w') as fp:
            fp.write('\n'.join([str(v) for v in tcp_list]))
        with open(hsp_file, 'w') as fp:
            fp.write('\n'.join([str(v) for v in hsp_list]))
        with open(csp_file, 'w') as fp:
            fp.write('\n'.join([str(v) for v in csp_list]))
        log_file.write(json.dumps([tcp_file, hsp_file, csp_file]))
    except Exception as e:
        _logger.exception('Failed to compute TCP.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
