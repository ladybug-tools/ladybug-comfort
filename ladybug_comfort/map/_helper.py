"""A collection of helper functions for the map sub-package."""
import numpy as np


def binary_mtx_dimension(filepath):
    """Return binary Radiance matrix dimensions if exist.

    This function returns NROWS, NCOLS, NCOMP and number of header lines including the
    white line after last header line.

    Args:
        filepath: Full path to Radiance file.

    Returns:
        nrows, ncols, ncomp, line_count
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
                break

        if not nrows or not ncols:
            error_message = (
                f'NROWS or NCOLS was not found in the Radiance header. NROWS '
                f'is {nrows} and NCOLS is {ncols}. The header must have both '
                f'elements.'
            )
            raise ValueError(error_message)
        return nrows, ncols, ncomp, len(header_lines) + 1
    finally:
        inf.close()


def binary_to_array(binary_file, nrows=None, ncols=None, ncomp=None, line_count=0):
    """Read a Radiance binary file as a NumPy array.

    Args:
        binary_file: Path to binary Radiance file.
        nrows: Number of rows in the Radiance file.
        ncols: Number of columns in the Radiance file.
        ncomp: Number of components of each element in the Radiance file.
        line_count: Number of lines to skip in the input file. Usually used to
            skip the header.

    Returns:
        A NumPy array.
    """
    with open(binary_file, 'rb') as reader:
        if (nrows or ncols or ncomp) is None:
            # get nrows, ncols and header line count
            nrows, ncols, ncomp, line_count = binary_mtx_dimension(binary_file)
        # skip first n lines from reader
        for i in range(line_count):
            reader.readline()

        array = np.fromfile(reader, dtype=np.float32)
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
