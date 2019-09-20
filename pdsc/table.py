"""
Parses PDS cumulative index files into an internal table representation
"""
import re
import numpy as np
from datetime import datetime

from .util import registerer, standard_progress_bar

INSTRUMENT_TABLES = {}
register_table = registerer(INSTRUMENT_TABLES)
"""
A decorator that can be used to register a :py:class:`PdsTable` subclass to a
particular instrument.

:param instrument: PDSC instrument name
:return: decorator that registers target to given instrument

See :ref:`Extending PDSC` for more details.
"""

INSTRUMENT_DETERMINERS = {}
register_determiner = registerer(INSTRUMENT_DETERMINERS)
"""
A decorator that can be used to register a function that determines whether a
cumulative index file is for a particular instrument.

:param instrument: PDSC instrument name
:return: decorator that registers target to given instrument

See :ref:`Extending PDSC` for more details.
"""

class PdsColumnType(object):
    """
    Wraps a type used for PDS columns to ensure a deterministic representation
    that omits memory addresses. This is a workaroud for an issue in Sphinx.

    >>> f = PdsColumnType(themis_datetime)
    >>> repr(f)
    '<function themis_datetime>'
    >>> f('1985-10-26T01:20:00.000')
    datetime.datetime(1985, 10, 26, 1, 20)
    """

    def __init__(self, f):
        """
        :param f: type function to wrap
        """
        self._f = f

    def __repr__(self):
        frepr = repr(self._f)
        return re.sub(' at 0x[0-9A-Fa-f]*', '', frepr)

    def __call__(self, *args, **kwargs):
        return self._f(*args, **kwargs)

def themis_datetime(s):
    """
    Parses date/time format found in THEMIS cumulative index files

    :param s: datetime string
    :return: :py:class:`datetime.datetime` object

    >>> themis_datetime('1985-10-26T01:20:00.000')
    datetime.datetime(1985, 10, 26, 1, 20)
    """
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')

def hirise_datetime(s):
    """
    Parses date/time format found in HiRISE cumulative index files

    :param s: datetime string
    :return: :py:class:`datetime.datetime` object

    >>> hirise_datetime('1985-10-26T01:20:00')
    datetime.datetime(1985, 10, 26, 1, 20)
    """
    return datetime.strptime(s.strip(), '%Y-%m-%dT%H:%M:%S')

def ctx_sclk(s):
    '''
    Converts the CTX SCLK representation with a colon into a fractional second
    with a decimal place

    :param s: CTX SCLK string
    :return: floating-point fractional second

    >>> ctx_sclk('10:1')
    10.1
    '''
    return float(s.replace(':', '.'))

def moc_observation_id(s):
    """
    Remove the forward slash in MOC observation ids

    :param s: MOC observation id
    :return: reformatted id

    >>> moc_observation_id('FHA/00469')
    'FHA00469'
    """
    return s.replace('/', '')

@register_determiner('hirise_edr')
def hirise_edr_determiner(label_contents):
    """
    Determines whether a cumulative index file is for HiRISE EDR products

    :param label_contents: PDS cumulative index LBL file contents
    :return: ``True`` iff this label file is for HiRISE EDR products
    """
    return (
        'HiRISE' in label_contents and
        'EDR_INDEX_TABLE' in label_contents
    )

@register_determiner('hirise_rdr')
def hirise_rdr_determiner(label_contents):
    """
    Determines whether a cumulative index file is for HiRISE RDR products

    :param label_contents: PDS cumulative index LBL file contents
    :return: ``True`` iff this label file is for HiRISE RDR products
    """
    return (
        'HiRISE' in label_contents and
        'RDR_INDEX_TABLE' in label_contents
    )

def themis_determiner(label_contents, detector_name):
    """
    Determines whether a cumulative index file is for generic THEMIS products

    :param label_contents: PDS cumulative index LBL file contents
    :param detector_name: THEMIS detector name (either ``'VIS'`` or ``'IR'``)
    :return: ``True`` iff this label file is for THEMIS products with the
        specified detector
    """
    instrument = parse_simple_label(label_contents, 'INSTRUMENT_NAME')
    detector = parse_simple_label(label_contents, 'DETECTOR_ID')
    return (
        instrument is not None and detector is not None and
        'THERMAL EMISSION IMAGING SYSTEM' in instrument
        and detector_name in detector
    )

def parse_simple_label(label_contents, key):
    """
    Retrieves the value of a "simple" PDS header entry corresponding to the
    given key. Simple entries are string-valued entries that do not split
    across lines.

    :param label_contents: string contents of the PDS LBL file
    :param key: entry key to search for in PDS label
    :return: entry value string or ``None`` if not found
    """
    for line in label_contents.splitlines(False):
        match = re.match(r'^\s*(\w+)\s*=\s*"?([^"]+)"?\s*$', line)
        if match is not None:
            k = match.group(1)
            v = match.group(2)
            if key == k:
                return v

    return None

def generic_determiner(label_contents, instrument_name):
    """
    Determines whether a cumulative index file is for an instrument with the
    specified name

    :param label_contents: PDS cumulative index LBL file contents
    :param instrument_name: instrument name as reported in the cumulative index
        ``INSTRUMENT_NAME`` header
    :return: ``True`` iff this label file is for the specified instrument

    This determiner works for cumulative index files that have an explicit
    ``INSTRUMENT_NAME`` header.
    """
    instrument = parse_simple_label(label_contents, 'INSTRUMENT_NAME')
    return (instrument is not None and instrument_name in instrument)

@register_determiner('themis_vis')
def themis_vis_determiner(label_contents):
    """
    Determines whether a cumulative index file is for THEMIS VIS products

    :param label_contents: PDS cumulative index LBL file contents
    :return: ``True`` iff this label file is for THEMIS VIS products
    """
    return themis_determiner(label_contents, 'VIS')

@register_determiner('themis_ir')
def themis_ir_determiner(label_contents):
    """
    Determines whether a cumulative index file is for THEMIS IR products

    :param label_contents: PDS cumulative index LBL file contents
    :return: ``True`` iff this label file is for THEMIS IR products
    """
    return themis_determiner(label_contents, 'IR')

@register_determiner('ctx')
def ctx_determiner(label_contents):
    """
    Determines whether a cumulative index file is for CTX products

    :param label_contents: PDS cumulative index LBL file contents
    :return: ``True`` iff this label file is for CTX products
    """
    return generic_determiner(label_contents, 'CONTEXT CAMERA')

@register_determiner('moc')
def moc_determiner(label_contents):
    """
    Determines whether a cumulative index file is for MOC products

    :param label_contents: PDS cumulative index LBL file contents
    :return: ``True`` iff this label file is for MOC products
    """
    return generic_determiner(label_contents, 'MARS ORBITER CAMERA')

def determine_instrument(label_contents):
    """
    Determines the PDSC instrument name associated with a PDS cumulative index
    LBL file

    :param label_contents: contents of the PDS cumulative index LBL file
    :return: the instrument name corresponding to the first registered
        "determiner" function that returns ``True``; instruments are checked in
        alphabetical order by name
    """
    for iname, determiner in sorted(INSTRUMENT_DETERMINERS.items()):
        if determiner(label_contents): return iname
    raise ValueError('Could not determine instrument')

class PdsTableColumn(object):
    """
    Class for representing and parsing a column from a PDS cumulative index
    table
    """

    PARSE_TABLE = {
        'NAME' : ('name', str),
        'COLUMN_NUMBER' : ('number', int),
        'DATA_TYPE': ('dtype', str),
        'START_BYTE': ('start_byte', int),
        'BYTES': ('length', int),
        'NOT_APPLICABLE_CONSTANT': ('unknown_constant', str),
    }
    """
    Information for parsing table columns; each column contains associated
    metadata such as the column number, the size of the column in bytes, or the
    fill value used when an entry is not applicable

    This dictionary maps the metadata identifier to a tuple containing the name
    and type of the :py:class:`PdsTableColumn` attribute that will be set when
    parsing this column.
    """

    TYPE_TABLE = {
        'ASCII_REAL' : float,
        'ASCII_INTEGER' : int,
    }
    """
    Contains a mapping of standard column data types to assocaited Python types
    """

    SPECIAL_TYPES = {}
    """
    Contains a mapping from column names with non-standard column types to
    assocaited Python types; sub-classes should use this attribute to define
    custom column types for a particular instrument
    """

    def __init__(self, fpointer):
        """
        :param fpointer:
            an open file object, pointing to the start of the column within the
            PDS index LBL file
        """
        self.name = None
        self.dtype = None
        self.number = None
        self.start_byte = None
        self.length = None
        self.unknown_constant = None

        success = self._parse(fpointer)
        if not success:
            raise ValueError('Column was not successfully parsed!')

        # Remap column data type
        if self.name in self.SPECIAL_TYPES:
            self.dtype = self.SPECIAL_TYPES[self.name]
        else:
            self.dtype = self.TYPE_TABLE.get(self.dtype, str)

        # Recast unknown constant to type of column
        if self.unknown_constant is not None:
            self.unknown_constant = self.dtype(self.unknown_constant)

    def _parse(self, fpointer):
        while True:
            line = fpointer.readline()
            if len(line) == 0: break

            match = re.match(r'\s*(\w+)\s*=\s*(\w+)\s*', line)
            if match is None:
                if 'END_OBJECT' in line:
                    return True
                else:
                    continue # pragma: no cover
            key = match.group(1)
            val = match.group(2)
            if key == 'END_OBJECT' and val == 'COLUMN':
                return True

            action = self.PARSE_TABLE.get(key, None)
            if action is None: continue

            vdest, vtype = action
            setattr(self, vdest, vtype(val))

        return False

class PdsTable(object):
    """
    Class for representing and parsing a PDS cumulative index table
    """

    PARSE_TABLE = {
        'COLUMNS' : ('n_columns', int),
        'ROWS' : ('n_rows', int),
        'ROW_BYTES' : ('row_bytes', int),
    }
    """
    Information for parsing the table object out of the PDS cumulative index
    label file

    This dictionary maps the metadata identifier to a tuple containing the name
    and type of the :py:class:`PdsTable` attribute that will be set when parsing
    this column.
    """

    TABLE_OBJECT_NAME = 'TABLE'
    """
    The name of a TABLE object in the PDS cumulative index label
    """

    COLUMN_OBJECT_NAME = 'COLUMN'
    """
    The name of a COLUMN object in the PDS cumulative index label
    """

    COLUMN_CLASS = PdsTableColumn
    """
    The table column class used to parse columns in this table
    """

    CHECK_COLUMN_COUNT = True
    """
    Whether to check the number of columns parsed against the number of columns
    reported in the table metadata; for most instruments, these numbers match,
    but other instruments have columns with multiple fields so there is
    sometimes a discrepancy between the effective number of columns and the
    reported column count.
    """

    def __init__(self, label_file, table_file):
        """
        :param label_file: path to a PDS cumulative index LBL file
        :param table_file: path to a PDS cumulative index TAB file
        """
        self.label_file = label_file
        self.table_file = table_file
        self._data_cache = {}

        for attr, _ in self.PARSE_TABLE.values():
            setattr(self, attr, None)

        with open(label_file, 'r') as f:
            columns = self._parse(f)

        if columns is None:
            raise RuntimeError('Error parsing table')

        if self.CHECK_COLUMN_COUNT and (len(columns) != self.n_columns):
            raise ValueError(
                'Expected %d columns; got %d'
                % (self.n_columns, len(columns))
            )

        _, self.columns = zip(*sorted(columns.items()))

    def _parse(self, fpointer):
        columns = {}
        in_table = False
        while True:
            line = fpointer.readline()
            if len(line) == 0: break

            match = re.match(r'\s*(\w+)\s*=\s*(\w+)\s*', line)
            if match is None:
                if in_table and 'END_OBJECT' in line:
                    return columns
                else:
                    continue # pragma: no cover
            key = match.group(1)
            val = match.group(2)

            if in_table:
                if key == 'END_OBJECT' and val == self.TABLE_OBJECT_NAME:
                    return columns

                if key == 'OBJECT' and val == self.COLUMN_OBJECT_NAME:
                    column = self.COLUMN_CLASS(fpointer)
                    if column.number is None:
                        column.number = len(columns)
                    columns[column.number] = column
                    continue

                action = self.PARSE_TABLE.get(key, None)
                if action is None: continue

                vdest, vtype = action
                setattr(self, vdest, vtype(val))
                continue

            else:
                if key == 'OBJECT' and val == self.TABLE_OBJECT_NAME:
                    in_table = True
                    continue

        return None

    def get_column_idx(self, column_name):
        """
        Get numerical column index given column name

        :param column_name: PDS table column name

        :return: index of column within table (raises :py:class:`IndexError` if
            the column is not found)
        """
        for i, c in enumerate(self.columns):
            if c.name == column_name: return i
        raise IndexError('Column name "%s" not found' % str(column_name))

    def get_column(self, column_name_or_idx, progress=True, cache=True):
        """
        Parses all column values out of a PDS cumulative index table

        :param column_name_or_idx:
            either an integer column index, or its name as given in the PDS
            label file
        :param progress:
            if ``True``, displays a progress bar as the column is being read
        :param cache:
            if ``True``, caches the result in memory so that subsequent calls do
            not have to read from the file

        :return: a :py:class:`numpy.array` containing values for every row of
            the specified column
        """
        if type(column_name_or_idx) != int:
            cidx = self.get_column_idx(column_name_or_idx)
        else:
            cidx = column_name_or_idx

        if cidx in self._data_cache:
            return self._data_cache[cidx]

        else:
            column = self.columns[cidx]

            values = []
            pbar = standard_progress_bar('Reading column %d' % cidx, progress)
            with open(self.table_file, 'r') as f:
                for r in pbar(range(self.n_rows)):
                    f.seek(r*self.row_bytes + column.start_byte - 1)
                    value = f.read(column.length)
                    values.append(value)

            try:
                data_column = np.array(values, dtype=column.dtype)
            except TypeError:
                pbar = standard_progress_bar(
                    'Converting column %d' % cidx, progress)
                data_column = np.array([column.dtype(v) for v in pbar(values)])

            if column.unknown_constant is not None:
                data_column[data_column == column.unknown_constant] = np.nan

            if data_column.dtype.char == 'S':
                data_column = np.char.strip(data_column)

            if cache:
                self._data_cache[cidx] = data_column
            return data_column

# ****************************************************************************
# CTX
# ****************************************************************************

class CtxTableColumn(PdsTableColumn):
    """
    A subclass of :py:class:`PdsTableColumn` for the CTX instrument to define
    some special types
    """

    SPECIAL_TYPES = {
        'IMAGE_TIME': PdsColumnType(themis_datetime),
        'SPACECRAFT_CLOCK_START_COUNT': PdsColumnType(ctx_sclk),
    }
    """
    Defines special types for the CTX instrument to parse observation and
    spacecraft clock times
    """

@register_table('ctx')
class CtxTable(PdsTable):
    """
    A subclass of :py:class:`PdsTable` for the CTX instrument that uses the
    custom :py:class:`CtxTableColumn` class
    """

    COLUMN_CLASS = CtxTableColumn
    """
    The :py:class:`CtxTable` class should use :py:class:`CtxTableColumn` for
    parsing columns
    """

# ****************************************************************************
# THEMIS
# ****************************************************************************

class ThemisTableColumn(PdsTableColumn):
    """
    A subclass of :py:class:`PdsTableColumn` for the THEMIS instrument to
    override column metadata and define some special types
    """

    PARSE_TABLE = {
        'NAME' : ('name', str),
        'COLUMN_NUMBER' : ('number', int),
        'DATA_TYPE': ('dtype', str),
        'START_BYTE': ('start_byte', int),
        'BYTES': ('length', int),
        'UNKNOWN_CONSTANT': ('unknown_constant', str),
    }
    """
    Override column metadata, which follows a slightly different convention for
    THEMIS
    """

    SPECIAL_TYPES = {
        'START_TIME': PdsColumnType(themis_datetime),
        'STOP_TIME': PdsColumnType(themis_datetime),
        'SPACECRAFT_CLOCK_START_COUNT': float,
        'SPACECRAFT_CLOCK_STOP_COUNT': float,
        'START_TIME_ET': float,
        'STOP_TIME_ET': float,
        'UNCORRECTED_SCLK_START_COUNT': float,
        'BAND_NUMBER': int,
        'LOCAL_TIME': float,
    }
    """
    Defines special types for the THEMIS observation metadata
    """

@register_table('themis_vis')
@register_table('themis_ir')
class ThemisTable(PdsTable):
    """
    A subclass of :py:class:`PdsTable` for the THEMIS instrument that uses the
    custom :py:class:`ThemisTableColumn` class
    """

    COLUMN_CLASS = ThemisTableColumn
    """
    The :py:class:`ThemisTable` class should use :py:class:`ThemisTableColumn`
    for parsing columns
    """

# ****************************************************************************
# HiRISE
# ****************************************************************************

class HiRiseTableColumn(PdsTableColumn):
    """
    A subclass of :py:class:`PdsTableColumn` for the HiRISE instrument to define
    some special types
    """

    SPECIAL_TYPES = {
        'OBSERVATION_START_TIME': PdsColumnType(hirise_datetime),
        'START_TIME': PdsColumnType(hirise_datetime),
        'OBSERVATION_START_COUNT': PdsColumnType(ctx_sclk),
        'STOP_TIME': PdsColumnType(hirise_datetime),
        'SPACECRAFT_CLOCK_START_COUNT': PdsColumnType(ctx_sclk),
        'SPACECRAFT_CLOCK_STOP_COUNT': PdsColumnType(ctx_sclk),
        'ADC_CONVERSION_SETTINGS': str,
    }
    """
    Defines special types for the HiRISE observation metadata
    """

@register_table('hirise_edr')
class HiRiseEdrTable(PdsTable):
    """
    A subclass of :py:class:`PdsTable` for the HiRISE instrument that uses the
    custom :py:class:`HiRiseTableColumn` class
    """

    COLUMN_CLASS = HiRiseTableColumn
    """
    The :py:class:`HiRiseEdrTable` class should use
    :py:class:`HiRiseTableColumn` for parsing columns
    """

    TABLE_OBJECT_NAME = 'EDR_INDEX_TABLE'
    """
    The HiRISE EDR table has a custom name
    """

    CHECK_COLUMN_COUNT = False
    """
    Ignore the column count discrepancy for the HiRISE EDR table
    """

# ****************************************************************************
# HiRISE RDR
# ****************************************************************************

@register_table('hirise_rdr')
class HiRiseRdrTable(PdsTable):
    """
    A subclass of :py:class:`PdsTable` for the HiRISE instrument that uses the
    custom :py:class:`HiRiseTableColumn` class
    """

    COLUMN_CLASS = HiRiseTableColumn
    """
    The :py:class:`HiRiseRdrTable` class should use
    :py:class:`HiRiseTableColumn` for parsing columns
    """

    TABLE_OBJECT_NAME = 'RDR_INDEX_TABLE'
    """
    The HiRISE RDR table has a custom name
    """

# ****************************************************************************
# MOC
# ****************************************************************************

class MocTableColumn(PdsTableColumn):
    """
    A subclass of :py:class:`PdsTableColumn` for the MOC instrument to define
    some special types
    """

    SPECIAL_TYPES = {
        'IMAGE_TIME': PdsColumnType(themis_datetime),
        'SPACECRAFT_CLOCK_START_COUNT': PdsColumnType(ctx_sclk),
        'PRODUCT_ID': PdsColumnType(moc_observation_id),
    }
    """
    Defines special types for the MOC observation metadata
    """

@register_table('moc')
class MocTable(PdsTable):
    """
    A subclass of :py:class:`PdsTable` for the MOC instrument that uses the
    custom :py:class:`MocTableColumn` class
    """

    COLUMN_CLASS = MocTableColumn
    """
    The :py:class:`MocTable` class should use :py:class:`MocTableColumn` for
    parsing columns
    """

def parse_table(label_file, table_file):
    """
    Parses a PDS cumulative index table

    :param label_file:
        path to the PDS LBL file assocated with the cumulate index
    :param table_file:
        path to the PDS TAB file assocated with the cumulate index

    :return: a :py:class:`PdsTable` object containing parsed table metadata

    This function first uses :py:meth:`determine_instrument` to determine the
    instrument name associated with the ``label_file``. Then, the function looks
    up the :py:class:`PdsTable` subclass that has been registered to the
    instrument and uses this class to parse the table.  See :ref:`Extending
    PDSC` for more details.
    """
    with open(label_file, 'r') as f:
        instrument = determine_instrument(f.read())

    if instrument not in INSTRUMENT_TABLES:
        raise ValueError('Table parsing not implemented for %s' % instrument)

    return instrument, INSTRUMENT_TABLES[instrument](label_file, table_file)
