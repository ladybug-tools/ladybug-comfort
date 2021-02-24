"""A collection of helper functions used throughout the CLI.

Most functions assist with the serialization of objects to/from JSON or CSV.
"""
import os
import json

from ladybug.analysisperiod import AnalysisPeriod
from ladybug.header import Header
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.futil import preparedir

from ladybug_comfort.parameter.pmv import PMVParameter
from ladybug_comfort.parameter.adaptive import AdaptiveParameter
from ladybug_comfort.parameter.utci import UTCIParameter
from ladybug_comfort.parameter.solarcal import SolarCalParameter


def _load_data(values, base_data, data_type, data_units):
    """Load a JSON array string of values to a data collection.

    Args:
        values: A number or JSON array string of numbers.
        base_data: A DataCollection object that serves as the base template
            for re-serialization.
        data_type: The class of the data type for the values.
        data_units: The units of the values.
    """
    if values is not None and values != '' and values != 'None':
        if values.startswith('['):  # it's an array of values
            value_list = json.loads(values)
            header = Header(data_type(), data_units, base_data.header.analysis_period)
            if isinstance(base_data, HourlyContinuousCollection):
                return HourlyContinuousCollection(header, value_list)
            else:
                return base_data.__class__(header, value_list, base_data.datetimes)
        else:  # assume the user has passed a single number
            return float(values)


def _load_values(values):
    """Load a JSON array string of values to a data collection.

    Args:
        values: A number or JSON array string of numbers.
    """
    if values is not None and values != '' and values != 'None':
        if values.startswith('['):  # it's an array of values
            return json.loads(values)
        else:  # assume the user has passed a single number
            return float(values)


def _load_analysis_period_str(analysis_period_str):
    """Load an AnalysisPeriod from a string.

    Args:
        analysis_period_str: A string of an AnalysisPeriod to be loaded.
    """
    if analysis_period_str is not None and analysis_period_str != '' \
            and analysis_period_str != 'None':
        return AnalysisPeriod.from_string(analysis_period_str)


def _load_pmv_par_str(comfort_par_str):
    """Load a PMVParameter from a string.

    Args:
        comfort_par_str: A string of a PMVParameter to be loaded.
    """
    if comfort_par_str is not None and comfort_par_str != '' \
            and comfort_par_str != 'None':
        return PMVParameter.from_string(comfort_par_str)


def _load_adaptive_par_str(comfort_par_str):
    """Load a AdaptiveParameter from a string.

    Args:
        comfort_par_str: A string of a AdaptiveParameter to be loaded.
    """
    if comfort_par_str is not None and comfort_par_str != '' \
            and comfort_par_str != 'None':
        return AdaptiveParameter.from_string(comfort_par_str)


def _load_utci_par_str(comfort_par_str):
    """Load a UTCIParameter from a string.

    Args:
        comfort_par_str: A string of a UTCIParameter to be loaded.
    """
    if comfort_par_str is not None and comfort_par_str != '' \
            and comfort_par_str != 'None':
        return UTCIParameter.from_string(comfort_par_str)


def _load_solarcal_par_str(solarcal_par_str):
    """Load a SolarCalParameter from a string.

    Args:
        solarcal_par_str: A string of a SolarCalParameter to be loaded.
    """
    if solarcal_par_str is not None and solarcal_par_str != '' \
            and solarcal_par_str != 'None':
        return SolarCalParameter.from_string(solarcal_par_str)


def _data_to_csv(data, csv_path):
    """Write a list of data collections into a CSV file."""
    with open(csv_path, 'w') as csv_file:
        for dat in data:
            str_data = (str(v) for v in dat)
            csv_file.write(','.join(str_data) + '\n')


def _thermal_map_csv(folder, result_sql, temperature, condition, condition_intensity):
    """Write out the thermal mapping CSV files associated with every comfort map."""
    if folder is None:
        folder = os.path.join(os.path.dirname(result_sql), 'thermal_map')
    preparedir(folder, remove_content=False)
    result_file_dict = {
        'temperature': os.path.join(folder, 'temperature.csv'),
        'condition': os.path.join(folder, 'condition.csv'),
        'condition_intensity': os.path.join(folder, 'condition_intensity.csv')
    }
    _data_to_csv(temperature, result_file_dict['temperature'])
    _data_to_csv(condition, result_file_dict['condition'])
    _data_to_csv(condition_intensity, result_file_dict['condition_intensity'])
    return result_file_dict
