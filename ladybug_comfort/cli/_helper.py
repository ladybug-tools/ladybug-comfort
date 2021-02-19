"""A collection of helper functions used throughout the CLI.

Most functions assist with the serialization of objects to/from JSON or CSV.
"""
import os
import json

from ladybug.analysisperiod import AnalysisPeriod
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.futil import preparedir

from ladybug_comfort.parameter.pmv import PMVParameter
from ladybug_comfort.parameter.adaptive import AdaptiveParameter
from ladybug_comfort.parameter.utci import UTCIParameter
from ladybug_comfort.parameter.solarcal import SolarCalParameter


def _load_data_json(data_json, base_collection):
    """Load a data collection from a JSON file.
    
    Args:
        data_json: A JSON file of a data collection to be loaded.
        base_collection: A DataCollection object that serves as the base template
            for re-serialization. The class of this object is used to re-serialize
            the data_json from dict.
    """
    if data_json is not None and data_json != 'None':
        if os.path.isfile(data_json):
            with open(data_json) as json_file:
                data = json.load(json_file)
            return base_collection.__class__.from_dict(data)
        else:  # assume the user has passed a single number instead of a file
            return float(data_json)


def _load_hourly_data_json(data_json):
    """Load an hourly continuous data collection from a JSON file.
    
    Args:
        data_json: A JSON file of an hourly continuous data collection to be loaded.
            This can also be a single number.
    """
    if data_json is not None and data_json != 'None':
        if os.path.isfile(data_json):
            with open(data_json) as json_file:
                data = json.load(json_file)
            return HourlyContinuousCollection.from_dict(data)
        else:  # assume the user has passed a single number instead of a file
            return float(data_json)


def _load_analysis_period_json(analysis_period_json):
    """Load an AnalysisPeriod from a JSON file.
    
    Args:
        analysis_period_json: A JSON file of an AnalysisPeriod to be loaded.
    """
    if analysis_period_json is not None and analysis_period_json != 'None':
        with open(analysis_period_json) as json_file:
            data = json.load(json_file)
        return AnalysisPeriod.from_dict(data)


def _load_pmv_par_json(comfort_par_json):
    """Load a PMVParameter from a JSON file.
    
    Args:
        comfort_par_json: A JSON file of a PMVParameter to be loaded.
    """
    if comfort_par_json is not None and comfort_par_json != 'None':
        with open(comfort_par_json) as json_file:
            comfort_par_data = json.load(json_file)
        return PMVParameter.from_dict(comfort_par_data)


def _load_adaptive_par_json(comfort_par_json):
    """Load a AdaptiveParameter from a JSON file.
    
    Args:
        comfort_par_json: A JSON file of a AdaptiveParameter to be loaded.
    """
    if comfort_par_json is not None and comfort_par_json != 'None':
        with open(comfort_par_json) as json_file:
            comfort_par_data = json.load(json_file)
        return AdaptiveParameter.from_dict(comfort_par_data)


def _load_utci_par_json(comfort_par_json):
    """Load a UTCIParameter from a JSON file.
    
    Args:
        comfort_par_json: A JSON file of a UTCIParameter to be loaded.
    """
    if comfort_par_json is not None and comfort_par_json != 'None':
        with open(comfort_par_json) as json_file:
            comfort_par_data = json.load(json_file)
        return UTCIParameter.from_dict(comfort_par_data)


def _load_solarcal_par_json(solarcal_par_json):
    """Load a SolarCalParameter from a JSON file.
    
    Args:
        solarcal_par_json: A JSON file of a SolarCalParameter to be loaded.
    """
    if solarcal_par_json is not None and solarcal_par_json != 'None':
        with open(solarcal_par_json) as json_file:
            solarcal_par_data = json.load(json_file)
        return SolarCalParameter.from_dict(solarcal_par_data)


def _data_to_csv(data, csv_path):
    """Write a list of data collections into a CSV file."""
    with open(csv_path, 'w') as csv_file:
        for dat in data:
            str_data = (str(v) for v in dat)
            csv_file.write(','.join(str_data) + '\n')


def _thermal_map_csv(folder, temperature, condition, condition_intensity):
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
