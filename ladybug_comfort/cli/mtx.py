"""Run matrices of thermal conditions through comfort models."""
import click
import sys
import logging
import json
import os

from ladybug_comfort.pmv import predicted_mean_vote, predicted_mean_vote_no_set
from ladybug_comfort.adaptive import adaptive_comfort_ashrae55, \
    adaptive_comfort_en15251, adaptive_comfort_conditioned_function, \
    cooling_effect_ashrae55, cooling_effect_en15251
from ladybug_comfort.utci import universal_thermal_climate_index

from ._helper import load_value_list, thermal_map_csv, csv_to_num_matrix, \
    load_pmv_par_str, load_adaptive_par_str, load_utci_par_str

_logger = logging.getLogger(__name__)


@click.group(help='Commands for running matrices of conditions through comfort models.')
def mtx():
    pass


@mtx.command('pmv')
@click.argument('temperature-mtx', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('rel-humidity-mtx', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--rad-temperature-mtx', '-rm', help='Path to a CSV file with with a '
              'matrix of MRT values. If unspecified, the radiant and the air '
              'temperature will be assumed to be the same.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--rad-delta-mtx', '-dm', help='Path to a CSV file with with a matrix '
              'of MRT deltas to be added to the base MRT values. This can be used to '
              'account for shortwave solar.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--air-speed-mtx', '-vm', help='Path to a CSV file with with a matrix '
              'of air speed values in m/s. If specified, this overrides both the '
              '--air-speed-json and the --air-speed inputs.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--air-speed-json', '-vm', help='Path to a JSON file conaining a '
              'simplified set of air speed values for each row of the matrix in m/s. '
              'If specified, this overrides the the --air-speed input.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--air-speed', '-v', help='A single number for air speed in m/s or a '
              'string of a JSON array with numbers that align with width of the matrix. '
              'If unspecified, 0.1 m/s will be used.', default='0.1', type=str)
@click.option('--met-rate', '-m', help='A single number for metabolic rate in met '
              'or a string of a JSON array with numbers that align with the '
              'width of the matrix. If unspecified, 1.1 met will be used.',
              default='1.1', type=str)
@click.option('--clo-value', '-c', help='A single number for clothing level in clo '
              'or a string of a JSON array with numbers that align with the '
              'width of the matrix. If unspecified, 0.7 clo will be used.',
              default='0.7', type=str)
@click.option('--write-op-map/--write-set-map', ' /-set', help='Flag to note whether '
              'the output temperature CSV should record Operative Temperature '
              'or Standard Effective Temperature (SET). SET is relatively intense '
              'to compute and so only recording Operative Temperature can greatly '
              'reduce run time, particularly when air speeds are low. However, SET '
              'accounts for all 6 PMV model inputs and so is a more representative '
              '"feels-like" temperature for the PMV model.', default=True)
@click.option('--comfort-par', '-cp', help='A PMVParameter string to customize the '
              'assumptions of the PMV model.', default=None, type=str)
@click.option('--folder', '-f', help='Folder into which the result CSV files will be '
              'written. If None, files will be written to a "thermal_mtx" sub-folder in'
              'same directory as the temperature-mtx.', default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output the paths to the '
              'generated CSV files. By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def pmv_mtx(temperature_mtx, rel_humidity_mtx, rad_temperature_mtx, rad_delta_mtx,
            air_speed_mtx, air_speed_json, air_speed,
            met_rate, clo_value, write_op_map, comfort_par, folder, log_file):
    """Get CSV files with matrices of PMV comfort from matrices of PMV inputs.

    \b
    Args:
        temperature_mtx: Path to a CSV file with with a matrix of temperature
            values in Celsius.
        rel_humidity_mtx: Path to a CSV file with with a matrix of relative humidity
            values in Percent.
    """
    try:
        # load up the matrices of values
        air_temp = csv_to_num_matrix(temperature_mtx)
        rel_h = csv_to_num_matrix(rel_humidity_mtx)
        rad_temp = csv_to_num_matrix(rad_temperature_mtx) \
            if rad_temperature_mtx is not None else air_temp
        if rad_delta_mtx is not None:
            d_rad_temp = csv_to_num_matrix(rad_delta_mtx)
            rad_temp = tuple(tuple(t + dt for t, dt in zip(t_pt, dt_pt))
                             for t_pt, dt_pt in zip(rad_temp, d_rad_temp))
        mtx_len = len(air_temp[0])

        # process any of the other inputs for air speed
        a_speed = None
        if air_speed_mtx is not None:
            a_speed = csv_to_num_matrix(air_speed_mtx)
        if a_speed is None and air_speed_json is not None:
            with open(air_speed_json) as json_file:
                a_speed_dict = json.load(json_file)
            speeds = a_speed_dict['air_speeds']
            a_speed = tuple(speeds[i] for i in a_speed_dict['speed_indices'])
        if a_speed is None:
            air_speed = load_value_list(air_speed, mtx_len, 0.1)
            a_speed = [air_speed] * len(air_temp)

        # load the met rate, clo value, and comfort parameters
        met_rate = load_value_list(met_rate, mtx_len, 1.1)
        clo_value = load_value_list(clo_value, mtx_len, 0.7)
        comfort_par = load_pmv_par_str(comfort_par)
        sa_thresh = comfort_par.still_air_threshold

        # run the collections through the PMV model and output results
        temper, cond, cond_intensity = [], [], []
        if write_op_map:
            for sat, srt, sas, srh in zip(air_temp, rad_temp, a_speed, rel_h):
                s_temper, s_cond, s_cond_intensity = [], [], []
                for ta, tr, vel, rh, met, clo in \
                        zip(sat, srt, sas, srh, met_rate, clo_value):
                    result = predicted_mean_vote_no_set(
                        ta, tr, vel, rh, met, clo, 0, sa_thresh)
                    s_cond_intensity.append(result['pmv'])
                    s_cond.append(
                        comfort_par.thermal_condition(result['pmv'], result['ppd']))
                    s_temper.append((ta + tr) / 2)
                temper.append(s_temper)
                cond.append(s_cond)
                cond_intensity.append(s_cond_intensity)
        else:
            for sat, srt, sas, srh in zip(air_temp, rad_temp, a_speed, rel_h):
                s_temper, s_cond, s_cond_intensity = [], [], []
                for ta, tr, vel, rh, met, clo in \
                        zip(sat, srt, sas, srh, met_rate, clo_value):
                    result = predicted_mean_vote(
                        ta, tr, vel, rh, met, clo, 0, sa_thresh)
                    s_cond_intensity.append(result['pmv'])
                    s_cond.append(
                        comfort_par.thermal_condition(result['pmv'], result['ppd']))
                    temper.append(result['set'])

        # write out the final results to CSV files
        if folder is None:
            folder = os.path.join(os.path.dirname(temperature_mtx), 'thermal_mtx')
        result_file_dict = thermal_map_csv(folder, temper, cond, cond_intensity)
        log_file.write(json.dumps(result_file_dict))
    except Exception as e:
        _logger.exception('Failed to run PMV matrix.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@mtx.command('adaptive')
@click.argument('temperature-mtx', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('prevail-temp', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--rad-temperature-mtx', '-rm', help='Path to a CSV file with with a '
              'matrix of MRT values. If unspecified, the radiant and the air '
              'temperature will be assumed to be the same.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--rad-delta-mtx', '-dm', help='Path to a CSV file with with a matrix '
              'of MRT deltas to be added to the base MRT values. This can be used to '
              'account for shortwave solar.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--air-speed-mtx', '-vm', help='Path to a CSV file with with a matrix '
              'of air speed values in m/s. If specified, this overrides both the '
              '--air-speed-json and the --air-speed inputs.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--air-speed-json', '-vm', help='Path to a JSON file conaining a '
              'simplified set of air speed values for each row of the matrix in m/s. '
              'If specified, this overrides the the --air-speed input.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--air-speed', '-v', help='A single number for air speed in m/s or a '
              'string of a JSON array with numbers that align with width of the matrix. '
              'If unspecified, 0.1 m/s will be used.', default='0.1', type=str)
@click.option('--comfort-par', '-cp', help='A AdaptiveParameter string to customize the '
              'assumptions of the Adaptive model.', default=None, type=str)
@click.option('--folder', '-f', help='Folder into which the result CSV files will be '
              'written. If None, files will be written to a "thermal_mtx" sub-folder in'
              'same directory as the temperature-mtx.', default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output the paths to the '
              'generated CSV files. By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def adaptive_mtx(temperature_mtx, prevail_temp, rad_temperature_mtx, rad_delta_mtx,
                 air_speed_mtx, air_speed_json, air_speed, comfort_par, folder, log_file):
    """Get CSV files with matrices of Adaptive comfort from matrices of Adaptive inputs.

    \b
    Args:
        temperature_mtx: Path to a CSV file with with a matrix of temperature
            values in Celsius.
        prevail_temp: Path to a CSV file with with a list of prevailing outdoor
            temperatures in a single row (one temperautre per column).
    """
    try:
        # load up the matrices of values
        air_temp = csv_to_num_matrix(temperature_mtx)
        prevail_temp = csv_to_num_matrix(prevail_temp)[0]
        rad_temp = csv_to_num_matrix(rad_temperature_mtx) \
            if rad_temperature_mtx is not None else air_temp
        if rad_delta_mtx is not None:
            d_rad_temp = csv_to_num_matrix(rad_delta_mtx)
            rad_temp = tuple(tuple(t + dt for t, dt in zip(t_pt, dt_pt))
                             for t_pt, dt_pt in zip(rad_temp, d_rad_temp))
        mtx_len = len(air_temp[0])

        # process any of the other inputs for air speed
        a_speed = None
        if air_speed_mtx is not None:
            a_speed = csv_to_num_matrix(air_speed_mtx)
        if a_speed is None and air_speed_json is not None:
            with open(air_speed_json) as json_file:
                a_speed_dict = json.load(json_file)
            speeds = a_speed_dict['air_speeds']
            a_speed = tuple(speeds[i] for i in a_speed_dict['speed_indices'])
        if a_speed is None:
            air_speed = load_value_list(air_speed, mtx_len, 0.1)
            a_speed = [air_speed] * len(air_temp)

        # load the comfort parameters
        comfort_par = load_adaptive_par_str(comfort_par)
        # determine the comfort function to use
        if comfort_par.conditioning != 0:
            comf_funct = adaptive_comfort_conditioned_function(
                comfort_par.conditioning, comfort_par.standard)
        elif comfort_par.ashrae55_or_en15251 is True:
            comf_funct = adaptive_comfort_ashrae55
        else:
            comf_funct = adaptive_comfort_en15251
        # determine the cooling effect function to use
        if comfort_par.discrete_or_continuous_air_speed is True:
            cooling_funct = cooling_effect_ashrae55
        else:
            cooling_funct = cooling_effect_en15251

        # run the collections through the PMV model and output results
        temper, cond, cond_intensity = [], [], []
        for sat, srt, sas in zip(air_temp, rad_temp, a_speed):
            s_temper, s_cond, s_cond_intensity = [], [], []
            for tp, ta, tr, vel in zip(prevail_temp, sat, srt, sas):
                to = (ta + tr) / 2
                result = comf_funct(tp, to)
                ce = cooling_funct(vel, to)
                s_cond_intensity.append(result['deg_comf'])
                s_cond.append(comfort_par.thermal_condition(result, ce))
                s_temper.append(to)
            temper.append(s_temper)
            cond.append(s_cond)
            cond_intensity.append(s_cond_intensity)

        # write out the final results to CSV files
        if folder is None:
            folder = os.path.join(os.path.dirname(temperature_mtx), 'thermal_mtx')
        result_file_dict = thermal_map_csv(folder, temper, cond, cond_intensity)
        log_file.write(json.dumps(result_file_dict))
    except Exception as e:
        _logger.exception('Failed to run PMV matrix.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@mtx.command('utci')
@click.argument('temperature-mtx', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('rel-humidity-mtx', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--rad-temperature-mtx', '-rm', help='Path to a CSV file with with a '
              'matrix of MRT values. If unspecified, the radiant and the air '
              'temperature will be assumed to be the same.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--rad-delta-mtx', '-dm', help='Path to a CSV file with with a matrix '
              'of MRT deltas to be added to the base MRT values. This can be used to '
              'account for shortwave solar.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--air-speed-mtx', '-vm', help='Path to a CSV file with with a matrix '
              'of air speed values in m/s. Note that these values are not '
              'meteorological and should be AT OCCUPANT LEVEL. If specified, this '
              'overrides both the --wind-speed-json and the --wind-speed inputs.',
              default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--wind-speed-json', '-vm', help='Path to a JSON file conaining a set of '
              'meteorological wind speed values for each row of the matrix in m/s. '
              'If specified, this overrides the the --wind-speed input.', default=None,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--wind-speed', '-v', help='A single number for meteorological wind '
              'speed in m/s or a string of a JSON array with numbers that align with '
              'the result-sql reporting period. If unspecified, 0.5 m/s will be used.',
              default=None, type=str)
@click.option('--comfort-par', '-cp', help='A UTCIParameter string to customize the '
              'assumptions of the UTCI model.', default=None, type=str)
@click.option('--folder', '-f', help='Folder into which the result CSV files will be '
              'written. If None, files will be written to a "thermal_mtx" sub-folder in'
              'same directory as the temperature-mtx.', default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output the paths to the '
              'generated CSV files. By default this will be printed out to stdout',
              type=click.File('w'), default='-', show_default=True)
def utci_mtx(temperature_mtx, rel_humidity_mtx, rad_temperature_mtx, rad_delta_mtx,
             air_speed_mtx, wind_speed_json, wind_speed, comfort_par, folder, log_file):
    """Get CSV files with matrices of UTCI comfort from matrices of UTCI inputs.

    \b
    Args:
        temperature_mtx: Path to a CSV file with with a matrix of temperature
            values in Celsius.
        rel_humidity_mtx: Path to a CSV file with with a matrix of relative humidity
            values in Percent.
    """
    try:
        # load up the matrices of values
        air_temp = csv_to_num_matrix(temperature_mtx)
        rel_h = csv_to_num_matrix(rel_humidity_mtx)
        rad_temp = csv_to_num_matrix(rad_temperature_mtx) \
            if rad_temperature_mtx is not None else air_temp
        if rad_delta_mtx is not None:
            d_rad_temp = csv_to_num_matrix(rad_delta_mtx)
            rad_temp = tuple(tuple(t + dt for t, dt in zip(t_pt, dt_pt))
                             for t_pt, dt_pt in zip(rad_temp, d_rad_temp))
        mtx_len = len(air_temp[0])

        # process any of the other inputs for air speed
        w_speed = None
        if air_speed_mtx is not None:
            a_speed = csv_to_num_matrix(air_speed_mtx)
            w_speed = tuple(tuple(v * 2 for v in row) for row in a_speed)
        if w_speed is None and wind_speed_json is not None:
            with open(wind_speed_json) as json_file:
                w_speed_dict = json.load(json_file)
            speeds = w_speed_dict['air_speeds']
            w_speed = tuple(speeds[i] for i in w_speed_dict['speed_indices'])
        if w_speed is None:
            wind_speed = load_value_list(wind_speed, mtx_len, 0.5)
            w_speed = [wind_speed] * len(air_temp)

        # load the comfort parameters
        comfort_par = load_utci_par_str(comfort_par)

        # run the collections through the UTCI model and output results
        temper, cond, cond_intensity = [], [], []
        for sat, srt, sws, srh in zip(air_temp, rad_temp, w_speed, rel_h):
            s_temper, s_cond, s_cond_intensity = [], [], []
            for ta, tr, vel, rh in zip(sat, srt, sws, srh):
                result = universal_thermal_climate_index(ta, tr, vel, rh)
                s_temper.append(result)
                s_cond.append(comfort_par.thermal_condition(result))
                s_cond_intensity.append(
                    comfort_par.thermal_condition_eleven_point(result))
            temper.append(s_temper)
            cond.append(s_cond)
            cond_intensity.append(s_cond_intensity)

        # write out the final results to CSV files
        if folder is None:
            folder = os.path.join(os.path.dirname(temperature_mtx), 'thermal_mtx')
        result_file_dict = thermal_map_csv(folder, temper, cond, cond_intensity)
        log_file.write(json.dumps(result_file_dict))
    except Exception as e:
        _logger.exception('Failed to run UTCI matrix.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
