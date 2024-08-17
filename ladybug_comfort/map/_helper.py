"""A collection of helper functions for the map sub-package."""
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
    with open(binary_file, 'rb') as file:
        # check if file is NumPy file
        numpy_header = file.read(6)
        if numpy_header.startswith(b'\x93NUMPY'):
            file.seek(0)
            array = np.load(file)
            return array
        file.seek(0)
        # check if file has Radiance header, if not it is a text file
        radiance_header = file.read(10).decode('utf-8')
        if radiance_header != '#?RADIANCE':
            file.seek(0)
            array = np.genfromtxt(file, dtype=np.float32)
            return array

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
        array = np.genfromtxt(matrix_file, delimiter=delimiter,  encoding='utf-8')
    else:
        array = np.load(matrix_file)

    return array
