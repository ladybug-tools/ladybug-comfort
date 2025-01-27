"""A collection of helper functions for the map sub-package."""
import json
from pathlib import Path
import numpy as np


def binary_mtx_dimension(filepath):
    """Return binary Radiance matrix dimensions if exist.

    This function returns NROWS, NCOLS, NCOMP and number of header lines including the
    white line after last header line.

    Args:
        filepath: Full path to Radiance file.

    Returns:
        nrows, ncols, ncomp, line_count, fmt
    """
    try:
        inf = open(filepath, 'rb', encoding='utf-8')
    except Exception:
        inf = open(filepath, 'rb')
    try:
        first_line = next(inf).rstrip().decode('utf-8')
        if first_line[:10] != '#?RADIANCE':
            error_message = (
                f'File with Radiance header must start with #?RADIANCE not '
                f'{first_line}.'
            )
            raise ValueError(error_message)

        header_lines = [first_line]
        nrows = ncols = ncomp = None
        for line in inf:
            line = line.rstrip().decode('utf-8')
            header_lines.append(line)
            if line[:6] == 'NROWS=':
                nrows = int(line.split('=')[-1])
            if line[:6] == 'NCOLS=':
                ncols = int(line.split('=')[-1])
            if line[:6] == 'NCOMP=':
                ncomp = int(line.split('=')[-1])
            if line[:7] == 'FORMAT=':
                fmt = line.split('=')[-1]
                break

        if not nrows or not ncols:
            error_message = (
                f'NROWS or NCOLS was not found in the Radiance header. NROWS '
                f'is {nrows} and NCOLS is {ncols}. The header must have both '
                f'elements.'
            )
            raise ValueError(error_message)
        return nrows, ncols, ncomp, len(header_lines) + 1, fmt
    finally:
        inf.close()


def binary_to_array(
        binary_file, nrows=None, ncols=None, ncomp=None, fmt=None,
        line_count=0):
    """Read a Radiance binary file as a NumPy array.

    Args:
        binary_file: Path to binary Radiance file.
        nrows: Number of rows in the Radiance file.
        ncols: Number of columns in the Radiance file.
        ncomp: Number of components of each element in the Radiance file.
        fmt: Format of the Radiance file. Can be either "ascii", "float", or "double.
        line_count: Number of lines to skip in the input file. Usually used to
            skip the header.

    Returns:
        A NumPy array.
    """
    if (nrows or ncols or ncomp or fmt) is None:
        # get nrows, ncols and header line count
        nrows, ncols, ncomp, line_count, fmt = binary_mtx_dimension(binary_file)
    with open(binary_file, 'rb') as reader:
        # skip first n lines from reader
        for i in range(line_count):
            reader.readline()

        if fmt == 'ascii':
            array = np.loadtxt(reader, dtype=np.float32)
        elif fmt == 'float':
            array = np.fromfile(reader, dtype=np.float32)
        elif fmt == 'double':
            array = np.fromfile(reader, dtype=np.float64)

        if ncomp != 1:
            array = array.reshape(nrows, ncols, ncomp)
        else:
            array = array.reshape(nrows, ncols)

    return array


def load_matrix(matrix_file, delimiter=','):
    with open(matrix_file, 'rb') as inf:
        first_char = inf.read(1)
        second_char = inf.read(1)
    is_text = True if first_char.isdigit() or second_char.isdigit() else False
    if is_text:
        array = np.genfromtxt(
            matrix_file, delimiter=delimiter, encoding='utf-8',
            filling_values=np.nan)
        if array.ndim == 1:
            array = array.reshape(-1, 1)
        if np.isnan(array[:, -1]).all():
            # remove last column if all in column is NaN
            # this may happen if the CSV has trailing commas
            array = array[:, :-1]
    else:
        array = np.load(matrix_file)

    return array


def restore_original_distribution(
        input_folder, output_folder, extension='npy', dist_info=None,
        output_extension='ill', as_text=False, fmt='%.2f', input_delimiter=',',
        delimiter='tab'):
    """Restructure files to the original distribution based on the distribution info.
    
    It will assume that the files in the input folder are NumPy files. However,
    if it fails to load the files as arrays it will try to load from binary
    Radiance files to array.

    Args:
        input_folder: Path to input folder.
        output_folder: Path to the new restructured folder
        extension: Extension of the files to collect data from. Default is ``npy`` for
            NumPy files. Another common extension is ``ill`` for the results of daylight
            studies.
        dist_info: Path to dist_info.json file. If None, the function will try to load
            ``_redist_info.json`` file from inside the input_folder. (Default: None).
        output_extension: Output file extension. This is only used if as_text
            is set to True. Otherwise the output extension will be ```npy``.
        as_text: Set to True if the output files should be saved as text instead
            of NumPy files.
        fmt: Format for the output files when saved as text.
        input_delimiter: Delimiter for the input files. This is used only if the
            input files are text files.
        delimiter: Delimiter for the output files when saved as text.
    """
    if not dist_info:
        _redist_info_file = Path(input_folder, '_redist_info.json')
    else:
        _redist_info_file = Path(dist_info)

    assert _redist_info_file.is_file(), 'Failed to find %s' % _redist_info_file

    with open(_redist_info_file) as inf:
        data = json.load(inf)

    # create output folder
    output_folder = Path(output_folder)
    if not output_folder.is_dir():
        output_folder.mkdir(parents=True, exist_ok=True)

    src_file = Path()
    for f in data:
        output_file = Path(output_folder, f['identifier'])
        # ensure the new folder is created. in case the identifier has a subfolder
        parent_folder = output_file.parent
        if not parent_folder.is_dir():
            parent_folder.mkdir()

        out_arrays = []
        for src_info in f['dist_info']:
            st = src_info['st_ln']
            end = src_info['end_ln']
            new_file = Path(input_folder, '%s.%s' % (src_info['identifier'], extension))
            if not new_file.samefile(src_file):
                src_file = new_file
                try:
                    array = np.load(src_file)
                except:
                    try:
                        array = binary_to_array(src_file)
                    except:
                        try:
                            array = np.loadtxt(
                                src_file, delimiter=input_delimiter)
                        except Exception:
                            raise RuntimeError(
                                f'Failed to load input file "{src_file}"')
            slice_array = array[st:end+1,:]

            out_arrays.append(slice_array)

        out_array = np.concatenate(out_arrays)
        # save numpy array, .npy extension is added automatically
        if not as_text:
            np.save(output_file, out_array)
        else:
            if output_extension.startswith('.'):
                output_extension = output_extension[1:]
            if delimiter == 'tab':
                delimiter = '\t'
            elif delimiter == 'space':
                delimiter = ' '
            elif delimiter == 'comma':
                delimiter = ','
            np.savetxt(output_file.with_suffix(f'.{output_extension}'),
                       out_array, fmt=fmt, delimiter=delimiter)
