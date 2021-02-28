"""Run EPW weather data through comfort models."""
import click
import sys
import logging
import json

from ladybug.epw import EPW
from ladybug_comfort.collection.utci import UTCI
from ladybug_comfort.collection.pmv import PMV

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
@click.option('--csv/--json', help='Flag to note whether output data collection should '
              'be in JSON format.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the CSV or JSON '
              'string of the data. By default, it will be printed to stdout',
              type=click.File('w'), default='-', show_default=True)
def utci(epw_file, include_wind, include_sun, csv, output_file):
    """Get a data collection for UTCI from an EPW weather file.

    \b
    Args:
        epw_file: Path to an .epw file.
    """
    try:
        epw_obj = EPW(epw_file)
        utci_obj = UTCI.from_epw(epw_obj, include_wind, include_sun)
        utci_data = utci_obj.universal_thermal_climate_index
        if csv:
            output_file.write('\n'.join([str(v) for v in utci_data.values]))
        else:
            output_file.write(json.dumps(utci_data.to_dict()))
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
@click.option('--csv/--json', help='Flag to note whether output data collection should '
              'be in JSON format.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the JSON string of '
              'the data collection. By default, it will be printed to stdout',
              type=click.File('w'), default='-', show_default=True)
def set_(epw_file, include_wind, include_sun, met_rate, clo_value, csv, output_file):
    """Get a data collection for Standard Effective Temperature from an EPW weather file.

    \b
    Args:
        epw_file: Path to an .epw file.
    """
    try:
        epw_obj = EPW(epw_file)
        pmv_obj = PMV.from_epw(epw_obj, include_wind, include_sun, met_rate, clo_value)
        set_data = pmv_obj.standard_effective_temperature
        if csv:
            output_file.write('\n'.join([str(v) for v in set_data.values]))
        else:
            output_file.write(json.dumps(set_data.to_dict()))
    except Exception as e:
        _logger.exception('Failed to get SET from EPW file.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
