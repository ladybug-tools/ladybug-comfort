"""Commands to work with data collections."""
import sys
import logging
import numpy as np
from pathlib import Path
import click
import json

from ladybug.datacollection import HourlyContinuousCollection, HourlyDiscontinuousCollection
from ladybug.header import Header
from ladybug.datautil import collections_to_csv


_logger = logging.getLogger(__name__)


@click.group(help='Commands to work with data collections.')
def datacollection():
    pass


@datacollection.command('folder-to-datacollections')
@click.argument(
    'folder', type=click.Path(exists=True, dir_okay=True, resolve_path=True)
)
@click.argument(
    'data-type', type=click.Path(exists=True, dir_okay=False, resolve_path=True)
)
@click.option(
    '--sub-folder', '-sf', type=click.STRING, default='datacollections',
    show_default=True
)
def folder_to_datacollections(folder, data_type, sub_folder):
    """Read an npy file and convert every row to a data collection.

    The data collections will be saved as CSV files in subfolder.

    \b
    Args:
        npy-file: Path to npy file.
        data-type: A JSON file with the data type.
        grid-name: The name of the grid. This is used in the metadata of the
            header.
    """
    with open(Path(folder, 'grids_info.json')) as json_file:
        grid_list = json.load(json_file)
    with open(data_type) as json_file:
        data_header = Header.from_dict(json.load(json_file))
    a_per = data_header.analysis_period
    continuous = True if a_per.st_hour == 0 and a_per.end_hour == 23 else False
    if not continuous:
        dates = a_per.datetimes
    try:
        for grid in grid_list:
            grid_name = grid['full_id'] if 'full_id' in grid else 'id'
            metadata = {'grid': grid_name}
            grid_file = Path(folder, '{}.npy'.format(grid_name))
            data_matrix = np.load(grid_file).tolist()
            grid_data = []
            for i, row in enumerate(data_matrix):
                header = data_header.duplicate()
                header.metadata = metadata.copy()
                header.metadata['sensor_index'] = i
                data = HourlyContinuousCollection(header, row) if continuous else \
                    HourlyDiscontinuousCollection(header, row, dates)
                grid_data.append(data)

            file_name = grid_name + '.csv'
            collections_to_csv(grid_data, Path(folder, sub_folder), file_name)
    except Exception:
        _logger.exception('Failed to convert folder of files to data collections.')
        sys.exit(1)
    else:
        sys.exit(0)
