"""Run EPW weather data through comfort models."""
import click
import sys
import logging
import json

from ladybug.epw import EPW

from ladybug_comfort.collection.utci import UTCI
from ladybug_comfort.collection.pmv import PMV
from ladybug_comfort.collection.adaptive import PrevailingTemperature

from ._helper import load_value_list, load_analysis_period_str, \
    load_adaptive_par_str

_logger = logging.getLogger(__name__)


@click.group(help='Commands for running EPW weather data through comfort models.')
def epw():
    pass


@epw.command('utci')
@click.argument('epw-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--include-wind/--exclude-wind', ' /-xw', help='Flag to note whether '
              'to include the EPW wind speed in the calculation.',
              default=True, show_default=True)
@click.option('--include-sun/--exclude-sun', ' /-xs', help='Flag to note whether '
              'to include the mean radiant temperature (MRT) delta from both shortwave '
              'solar falling directly on people and long wave radiant exchange with '
              'the sky.', default=True, show_default=True)
@click.option('--run-period', '-rp', help='An AnalysisPeriod string to dictate the '
              'start and end of the analysis (eg. "6/21 to 9/21 between 8 and 16 @1"). '
              'If unspecified, results will be generated for the entire year of '
              'the EPW.', default=None, type=str)
@click.option('--csv/--json', ' /-j', help='Flag to note whether the output data '
              'should be in CSV or JSON format.', default=True, show_default=True)
@click.option('--rows/--columns', ' /-c', help='Flag to note whether the CSV should '
              'be written with rows or columns.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the CSV or JSON '
              'string of the data. By default, it will be printed to stdout',
              type=click.File('w'), default='-', show_default=True)
def utci(epw_file, include_wind, include_sun, run_period, csv, rows, output_file):
    """Get UTCI values from an EPW weather file.

    \b
    Args:
        epw_file: Path to an .epw file.
    """
    try:
        epw_obj = EPW(epw_file)
        utci_obj = UTCI.from_epw(epw_obj, include_wind, include_sun)
        utci_data = utci_obj.universal_thermal_climate_index
        _write_data_to_file(output_file, utci_data, run_period, csv, rows)
    except Exception as e:
        _logger.exception('Failed to get UTCI from EPW file.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@epw.command('set')
@click.argument('epw-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--include-wind/--exclude-wind', ' /-xw', help='Flag to note whether '
              'to include the EPW wind speed in the calculation.',
              default=True, show_default=True)
@click.option('--include-sun/--exclude-sun', ' /-xs', help='Flag to note whether '
              'to include the mean radiant temperature (MRT) delta from both shortwave '
              'solar falling directly on people and long wave radiant exchange with '
              'the sky.', default=True, show_default=True)
@click.option('--met-rate', '-m', help='A number for metabolic rate in met.',
              type=float, default=2.4, show_default=True)
@click.option('--clo-value', '-c', help='A number for clothing level in clo.',
              type=float, default=0.7, show_default=True)
@click.option('--run-period', '-rp', help='An AnalysisPeriod string to dictate the '
              'start and end of the analysis (eg. "6/21 to 9/21 between 8 and 16 @1"). '
              'If unspecified, results will be generated for the entire year of '
              'the EPW.', default=None, type=str)
@click.option('--csv/--json', ' /-j', help='Flag to note whether the output data '
              'should be in CSV or JSON format.', default=True, show_default=True)
@click.option('--rows/--columns', ' /-c', help='Flag to note whether the CSV should '
              'be written with rows or columns.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the JSON string of '
              'the data collection. By default, it will be printed to stdout',
              type=click.File('w'), default='-', show_default=True)
def set_(epw_file, include_wind, include_sun, met_rate, clo_value, run_period,
         csv, rows, output_file):
    """Get Standard Effective Temperature (SET) values from an EPW weather file.

    \b
    Args:
        epw_file: Path to an .epw file.
    """
    try:
        epw_obj = EPW(epw_file)
        pmv_obj = PMV.from_epw(epw_obj, include_wind, include_sun, met_rate, clo_value)
        set_data = pmv_obj.standard_effective_temperature
        _write_data_to_file(output_file, set_data, run_period, csv, rows)
    except Exception as e:
        _logger.exception('Failed to get SET from EPW file.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@epw.command('prevailing')
@click.argument('epw-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--comfort-par', '-cp', help='A AdaptiveParameter string to customize the '
              'assumptions of the Adaptive model.', default=None, type=str)
@click.option('--run-period', '-rp', help='An AnalysisPeriod string to dictate the '
              'start and end of the analysis (eg. "6/21 to 9/21 between 8 and 16 @1"). '
              'If unspecified, results will be generated for the entire year of '
              'the EPW.', default=None, type=str)
@click.option('--csv/--json', ' /-j', help='Flag to note whether the output data '
              'should be in CSV or JSON format.', default=True, show_default=True)
@click.option('--rows/--columns', ' /-c', help='Flag to note whether the CSV should '
              'be written with rows or columns.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the CSV or JSON '
              'string of the data. By default, it will be printed to stdout',
              type=click.File('w'), default='-', show_default=True)
def prevailing(epw_file, comfort_par, run_period, csv, rows, output_file):
    """Get Adaptive comfort Prevailing Outdoor Temperature from an EPW weather file.

    \b
    Args:
        epw_file: Path to an .epw file.
    """
    try:
        epw_obj = EPW(epw_file)
        comf_par = load_adaptive_par_str(comfort_par)
        prev_obj = PrevailingTemperature(
            epw_obj.dry_bulb_temperature, comf_par.avg_month_or_running_mean)
        prev_data = prev_obj.hourly_prevailing_temperature
        _write_data_to_file(output_file, prev_data, run_period, csv, rows)
    except Exception as e:
        _logger.exception(
            'Failed to get Prevailing Temperature from EPW file.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@epw.command('air-speed-json')
@click.argument('epw-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('enclosure-info', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--multiply-by', '-m', help='A number to denote a factor that EPW wind '
              'speeds should be multipled by in order to represent air speeds at '
              'ground level.', type=float, default=0.5, show_default=True)
@click.option('--indoor-air-speed', '-i', help='A single number for air speed in m/s or '
              'the path to a CSV file containing a single number per row and a number '
              'of rows that aligns with the length of the --run-period. This can also '
              'be a string of a JSON array with that aligns with the --run-period, '
              'though this is only recommended for cases of short run periods. '
              'If unspecified, 0.1 m/s will be used.', default=None, type=str)
@click.option('--outdoor-air-speed', '-o', help='A single number for air speed in m/s or'
              ' the path to a CSV file containing a single number per row and a number '
              'of rows that aligns with the length of the --run-period. This can also '
              'be a string of a JSON array with that aligns with the --run-period, '
              'though this is only recommended for cases of short run periods. '
              'If unspecified, the EPW wind speed times the --multiply-by will be used.',
              default=None, type=str)
@click.option('--run-period', '-rp', help='An AnalysisPeriod string to dictate the '
              'start and end of the analysis (eg. "6/21 to 9/21 between 8 and 16 @1"). '
              'If unspecified, results will be generated for the entire year of '
              'the EPW.', default=None, type=str)
@click.option('--output-file', '-f', help='Optional file to output the JSON '
              'string. By default, it will be printed to stdout',
              type=click.File('w'), default='-', show_default=True)
def air_speed_json(epw_file, enclosure_info, multiply_by, indoor_air_speed,
                   outdoor_air_speed, run_period, output_file):
    """Get a JSON of air speeds that can be used as input for the mtx commands.

    \b
    Args:
        epw_file: Path to an .epw file.
        enclosure_info: Path to a JSON file containing information about the radiant
            enclosure that sensor points belong to.
    """
    try:
        # load the EPW object and extract the wind speeds
        epw_obj = EPW(epw_file)
        run_period = load_analysis_period_str(run_period)
        wind_speeds = epw_obj.wind_speed.values if run_period is None else \
            epw_obj.wind_speed.filter_by_analysis_period(run_period).values
        if multiply_by != 1:
            wind_speeds = tuple(v * multiply_by for v in wind_speeds)

        # process the outdoor air speeds
        if outdoor_air_speed is not None and outdoor_air_speed != '' \
                and outdoor_air_speed != 'None':
            wind_speeds_init = load_value_list(outdoor_air_speed, len(wind_speeds), None)
            if wind_speeds_init[0] is not None:
                wind_speeds = wind_speeds_init

        # process the indoor_air_speed
        in_air_speeds = load_value_list(indoor_air_speed, len(wind_speeds), 0.1)

        # assemble everything into a dictionary
        air_spd_dict = {'air_speeds': [wind_speeds, in_air_speeds]}
        with open(enclosure_info) as json_file:
            enclosure_dict = json.load(json_file)
        speed_indices = []
        for sens in enclosure_dict['sensor_indices']:
            val = 0 if sens < 0 else 1
            speed_indices.append(val)
        air_spd_dict['speed_indices'] = speed_indices

        # write the dictionary to a JSON file
        output_file.write(json.dumps(air_spd_dict))
    except Exception as e:
        _logger.exception('Failed to create air speed JSON file.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


def _write_data_to_file(output_file, data, run_period, csv, rows):
    """Write a data collection to a variety of output files."""
    run_period = load_analysis_period_str(run_period)
    if run_period is not None:
        data = data.filter_by_analysis_period(run_period)
    if csv:
        if rows:
            output_file.write('\n'.join([str(v) for v in data.values]))
        else:
            output_file.write(','.join([str(v) for v in data.values]))
    else:
        output_file.write(json.dumps(data.to_dict()))
