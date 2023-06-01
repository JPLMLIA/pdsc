"""
Implements command line tools for PDSC
"""
from __future__ import print_function
import os
import re
import warnings
from shutil import move
from shutil import copy
from itertools import count
from tempfile import NamedTemporaryFile

from .ingest import get_idx_file_pair
from .table import parse_table
from .util import standard_progress_bar

def _resize_scan_exposure_duration(sed, length):
    """
    Formats SCAN_EXPOSURE_DURATION with increasing precision until the desired
    string length is achieved

    :param sed:
        floating point SCAN_EXPOSURE_DURATION value
    :param length:
        desired formatted string length

    :return: a string with the SCAN_EXPOSURE_DURATION formatted with the
        appropriate length, or ``None`` if even the string is too long even with
        no digits after the decimal point
    """
    for i in count():
        new_sed_str = ('%%.%df' % i) % sed
        if len(new_sed_str) == length:
            return new_sed_str
        elif len(new_sed_str) > length:
            return None

def fix_hirise_index(idx, outputfile, quiet):
    """
    Repairs HiRISE EDR cumulative index files for which the value in
    SCAN_EXPOSURE_DURATION exceeds the available number of bytes for that field

    :param idx:
        path to one LBL or TAB file from the index file pair
    :param outputfile:
        output file path for the corrected index TAB file; if ``None``,
        overwrite the existing file
    :param quiet:
        if ``True``, do not output progress or results
    """
    lblfile, tabfile = get_idx_file_pair(idx)
    if outputfile is None:
        outputfile = tabfile

    start_idx, length = None, None
    instrument, table = parse_table(lblfile, tabfile)
    for column in table.columns:
        if column.name == 'SCAN_EXPOSURE_DURATION':
            start_idx = column.start_byte - 1
            length = column.length

    if start_idx is None: return

    if not quiet:
        progress = standard_progress_bar('Fixing HiRISE EDR cumulative index')
        statinfo = os.stat(tabfile)
        progress.maxval = statinfo.st_size
        progress.start()
        bytes_processed = 0
    else:
        progress = None

    lines_repaired = 0
    with NamedTemporaryFile(delete=False) as fout:
        tempname = fout.name
        with open(tabfile, 'r') as f:
            for i, line in enumerate(f):
                if len(line) != table.row_bytes:

                    end = line.find(',', start_idx)
                    sed_str = line[start_idx:end]

                    if len(sed_str) <= length:
                        raise RuntimeError(
                            'Unexpected cause of length discrepancy for line %d'
                            % i
                        )

                    sed = float(sed_str)
                    new_sed_str = _resize_scan_exposure_duration(sed, length)

                    if new_sed_str is None:
                        raise RuntimeError(
                            'Could not reduce value SCAN_EXPOSURE_DURATION '
                            '"%s" on line %d'
                            % (sed_str, i)
                        )

                    if float(new_sed_str) != sed:
                        warnings.warn(
                            'Precision lost in field size reduction '
                            '(%s -> %s) on line %d'
                            % (sed_str, new_sed_str, i),
                            RuntimeWarning
                        )

                    new_line = (line[:start_idx] + new_sed_str + line[end:])
                    lines_repaired += 1

                else:
                    new_line = line

                assert(len(new_line) == table.row_bytes)
                fout.write(new_line)
                if progress is not None:
                    bytes_processed += len(line)
                    progress.update(bytes_processed)

    move(tempname, outputfile)

    if progress is not None:
        progress.finish()
        if lines_repaired == 1:
            print('Finished: 1 line repaired.')
        else:
            print('Finished: %d lines repaired.' % lines_repaired)

def fix_hirise_idxlbl(idx, outputfile, quiet):
    """
    Repairs HiRISE RDR cumulative index files for which the values of
    FILE_RECORDS and ROWS in the LBL file do not match the total number of lines
    in the TAB file.

    :param idx:
       path to one LBL or TAB file from the index file pair
    :param outputfile:
       output file path for the corrected index TAB file; if ``None``,
       overwrite the existing file
    :param quiet:
       if ``True``, do not output progress or results
    """
    lblfile, tabfile = get_idx_file_pair(idx)

    # Count the number of lines in the TAB file
    with open(tabfile, 'r') as f:
        lines = f.readlines()
        tabrows = len(lines)

    _, table = parse_table(lblfile, tabfile)

    # If the records in the LBL file match the TAB file, there is no correction
    # needed.
    if table.n_rows == tabrows:
        if not quiet:
            print('FILE_RECORDS and ROWS in the LBL file match the number '
                  'of lines in the TAB file. No correction needed.')

        if outputfile is not None:
            copy(lblfile, outputfile)

            if not quiet:
                print('--outputfile is specified. The LBL file is copied to '
                      '%s' % outputfile)

        return

    with NamedTemporaryFile(delete=False) as fout:
        tempname = fout.name
        file_records_regex = re.compile('FILE_RECORDS = \d+')
        rows_regex = re.compile('\s+ROWS = \d+')

        with open(lblfile, 'r') as f:
            lbllines = f.readlines()

        for line in lbllines:
            # Fix FILE_RECORDS
            if file_records_regex.match(line):
                line = 'FILE_RECORDS = %d\n' % tabrows

                if not quiet:
                    print('Fixed FILE_RECORDS')

            # Fix ROWS
            if rows_regex.match(line):
                line = '    ROWS = %d\n' % tabrows

                if not quiet:
                    print('Fixed ROWS')

            fout.write(line)

    if outputfile is not None:
        move(tempname, outputfile)

        if not quiet:
            print('Output is saved to %s' % outputfile)
    else:
        move(tempname, lblfile)

        if not quiet:
            print('Output is saved to %s' % lblfile)
