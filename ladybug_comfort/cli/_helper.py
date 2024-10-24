"""A collection of helper functions used throughout the CLI.

Most functions assist with the serialization of objects to/from JSON or CSV.
"""
import os
import json
import numpy as np

from ladybug.analysisperiod import AnalysisPeriod
from ladybug.header import Header
from ladybug.datacollection import HourlyContinuousCollection
from ladybug.futil import preparedir

from ladybug_comfort.parameter.pmv import PMVParameter
from ladybug_comfort.parameter.adaptive import AdaptiveParameter
from ladybug_comfort.parameter.utci import UTCIParameter
from ladybug_comfort.parameter.solarcal import SolarCalParameter


def load_data(values, base_data, data_type, data_units):
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


def load_values(values):
    """Load a single value or JSON array string of values.

    Args:
        values: A number or JSON array string of numbers.
    """
    if values is not None and values != '' and values != 'None':
        if values.startswith('['):  # it's an array of values
            return json.loads(values)
        else:  # assume the user has passed a single number
            return float(values)


def load_value_list(values, calc_len, default=None):
    """Load a single value or JSON array string of values to a list of values

    Args:
        values: A number or JSON array string of numbers.
        calc_len: Integer for the length of the list to be returned.
        default: Default value to be used when the values are None.
    """
    if values is not None and values != '' and values != 'None':
        if values.startswith('['):  # it's an array of values
            return json.loads(values)
        elif os.path.isfile(values):  # it's a CSV with the values in it
            with open(values) as hourly_schedule:
                vals = [float(v) for v in hourly_schedule]
            if len(vals) == 1:
                return vals * calc_len
            return vals
        else:  # assume the user has passed a single number
            try:
                return [float(values)] * calc_len
            except ValueError:  # none of the above; just revert to the default
                pass
    return [default] * calc_len


def load_analysis_period_str(analysis_period_str):
    """Load an AnalysisPeriod from a string.

    Args:
        analysis_period_str: A string of an AnalysisPeriod to be loaded.
    """
    if analysis_period_str is not None and analysis_period_str != '' \
            and analysis_period_str != 'None':
        return AnalysisPeriod.from_string(analysis_period_str)


def load_pmv_par_str(comfort_par_str):
    """Load a PMVParameter from a string.

    Args:
        comfort_par_str: A string of a PMVParameter to be loaded.
    """
    if comfort_par_str is not None and comfort_par_str != '' \
            and comfort_par_str != 'None':
        return PMVParameter.from_string(comfort_par_str)
    return PMVParameter()


def load_adaptive_par_str(comfort_par_str):
    """Load a AdaptiveParameter from a string.

    Args:
        comfort_par_str: A string of a AdaptiveParameter to be loaded.
    """
    if comfort_par_str is not None and comfort_par_str != '' \
            and comfort_par_str != 'None':
        return AdaptiveParameter.from_string(comfort_par_str)
    return AdaptiveParameter()


def load_utci_par_str(comfort_par_str):
    """Load a UTCIParameter from a string.

    Args:
        comfort_par_str: A string of a UTCIParameter to be loaded.
    """
    if comfort_par_str is not None and comfort_par_str != '' \
            and comfort_par_str != 'None':
        return UTCIParameter.from_string(comfort_par_str)
    return UTCIParameter()


def load_solarcal_par_str(solarcal_par_str):
    """Load a SolarCalParameter from a string.

    Args:
        solarcal_par_str: A string of a SolarCalParameter to be loaded.
    """
    if solarcal_par_str is not None and solarcal_par_str != '' \
            and solarcal_par_str != 'None':
        return SolarCalParameter.from_string(solarcal_par_str)


def csv_to_num_matrix(csv_file_path):
    """Load a CSV file consisting only of numbers into a Python matrix of floats.

    Args:
        csv_file_path: Full path to a valid CSV file (e.g. c:/ladybug/test.csv)
    """
    with open(csv_file_path) as csv_data_file:
        return tuple(
            tuple(float(val) for val in row.split(',')) for row in csv_data_file
        )


def _data_to_csv(data, csv_path):
    """Write a list of data collections into a CSV file."""
    with open(csv_path, 'w') as csv_file:
        for dat in data:
            str_data = (str(v) for v in dat)
            csv_file.write(','.join(str_data) + '\n')


def _data_to_ill(data, ill_path):
    """Write a list of data collections into an ill file."""
    with open(ill_path, 'w') as ill_file:
        for dat in data:
            str_data = ('{:.7e}'.format(v) for v in dat)
            ill_file.write(' '.join(str_data) + '\n')


def thermal_map_csv(folder, temperature, condition, condition_intensity,
                    plain_text=True):
    """Write out the thermal mapping CSV files associated with every comfort map."""
    preparedir(folder, remove_content=False)
    result_file_dict = {
        'temperature': os.path.join(folder, 'temperature.csv'),
        'condition': os.path.join(folder, 'condition.csv'),
        'condition_intensity': os.path.join(folder, 'condition_intensity.csv')
    }
    if plain_text:
        _data_to_csv(temperature, result_file_dict['temperature'])
        _data_to_csv(condition, result_file_dict['condition'])
        _data_to_csv(condition_intensity, result_file_dict['condition_intensity'])
    else:
        with open(result_file_dict['temperature'], 'wb') as fp:
            np.save(fp, set_smallest_dtype(np.array(temperature)))
        with open(result_file_dict['condition'], 'wb') as fp:
            np.save(fp, set_smallest_dtype(np.array(condition)))
        with open(result_file_dict['condition_intensity'], 'wb') as fp:
            np.save(fp, set_smallest_dtype(np.array(condition_intensity)))
    return result_file_dict


def smallest_integer_dtype(array: np.ndarray):
    """Return the smallest possible integer dtype.

    Args:
        array: NumPy array.

    Returns:
        A NumPy integer dtype.
    """
    if np.all(array >= np.iinfo(np.int8).min) and \
            np.all(array <= np.iinfo(np.int8).max):
        return np.int8
    elif np.all(array >= np.iinfo(np.int16).min) and \
            np.all(array <= np.iinfo(np.int16).max):
        return np.int16
    elif np.all(array >= np.iinfo(np.int32).min) and \
            np.all(array <= np.iinfo(np.int32).max):
        return np.int32
    elif np.all(array >= np.iinfo(np.int64).min) and \
            np.all(array <= np.iinfo(np.int64).max):
        return np.int64


def smallest_float_dtype(array: np.ndarray, rtol: float = 1e-5, atol: float = 1e-5):
    """Return the smallest possible float dtype.

    The allclose function is used to check if a certain floating-point precision
    can be used without losing accuracy.

    Args:
        array: NumPy array.
        rtol: The relative tolerance parameter for `np.allclose`. The default
            is 1e-5.
        atol: The absolute tolerance parameter for `np.allclose`. The default
            is 1e-5.

    Returns:
        A NumPy floating dtype.
    """
    if np.all((array >= np.finfo(np.float16).min) &
              (array <= np.finfo(np.float16).max)):
        if np.allclose(array, array.astype(np.float16), rtol=rtol, atol=atol):
            return np.float16
    if np.all((array >= np.finfo(np.float32).min) &
              (array <= np.finfo(np.float32).max)):
        if np.allclose(array, array.astype(np.float32), rtol=rtol, atol=atol):
            return np.float32
    if np.all((array >= np.finfo(np.float64).min) &
              (array <= np.finfo(np.float64).max)):
        if np.allclose(array, array.astype(np.float64), rtol=rtol, atol=atol):
            return np.float64


def smallest_dtype(array: np.ndarray, rtol: float = 1e-5, atol: float = 1e-5):
    """Return the smallest possible dtype.

    Args:
        array: NumPy array.
        rtol: The relative tolerance parameter for `np.allclose`. The default
            is 1e-5. This is also used if the dtype of the array is np.floating.
        atol: The absolute tolerance parameter for `np.allclose`. The default
            is 1e-5. This is also used if the dtype of the array is np.floating.

    Returns:
        A NumPy dtype.
    """
    if np.issubdtype(array.dtype, np.integer):
        return smallest_integer_dtype(array)
    elif np.issubdtype(array.dtype, np.floating):
        return smallest_float_dtype(array, rtol=rtol, atol=atol)
    else:
        raise TypeError(f'Expected integer or floating dtype. Got {array.dtype}')


def set_smallest_dtype(array: np.ndarray, rtol: float = 1e-5, atol: float = 1e-5):
    """Return a NumPy array with the smallest possible dtype.

    Args:
        array: NumPy array.
        rtol: The relative tolerance parameter for `np.allclose`. The default
            is 1e-5. This is also used if the dtype of the array is np.floating.
        atol: The absolute tolerance parameter for `np.allclose`. The default
            is 1e-5. This is also used if the dtype of the array is np.floating.

    Returns:
        A new NumPy array with a smaller dtype.
    """
    dtype = smallest_dtype(array, rtol=rtol, atol=atol)
    return array.astype(dtype)
