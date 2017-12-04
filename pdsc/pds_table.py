"""
Code for parsing PDS cumidx tables
"""
import re
import numpy as np
from datetime import datetime
from pds.core.parser import Parser
from progressbar import ProgressBar, Bar, ETA

def themis_datetime(s):
    return datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%f')

def hirise_datetime(s):
    return datetime.strptime(s.strip(), '%Y-%m-%dT%H:%M:%S')

def ctx_sclk(s):
    return float(s.replace(':', '.'))

def moc_observation_id(s):
    return s.replace('/', '')

def determine_instrument(label_file):
    exception = ValueError('Could not determine instrument')
    with open(label_file, 'r') as f:
        try:
            parser = Parser()
            labels = parser.parse(f)
            instrument = labels.get('INSTRUMENT_NAME', None)
        except AssertionError:
            instrument = None

        if instrument is None:
            f.seek(0)
            raw = f.read()
            if 'HiRISE' in raw:
                return 'hirise'
            else:
                raise exception

        elif 'THERMAL EMISSION IMAGING SYSTEM' in instrument:
            detector = labels.get('DETECTOR_ID', None)
            if 'VIS' in detector:
                return 'themis_vis'
            elif 'IR' in detector:
                return 'themis_ir'
            else:
                raise exception

        elif 'CONTEXT CAMERA' in instrument:
            return 'ctx'

        elif 'MARS ORBITER CAMERA' in instrument:
            return 'moc'

        else:
            raise exception

class PdsTableColumn(object):

    PARSE_TABLE = {
        'NAME' : ('name', str),
        'COLUMN_NUMBER' : ('number', int),
        'DATA_TYPE': ('dtype', str),
        'START_BYTE': ('start_byte', int),
        'BYTES': ('length', int),
        'NOT_APPLICABLE_CONSTANT': ('unknown_constant', str),
        'UNIT' : ('unit', str),
    }

    TYPE_TABLE = {
        'ASCII_REAL' : float,
        'ASCII_INTEGER' : int,
    }

    SPECIAL_TYPES = {}

    def __init__(self, fpointer):
        self.name = None
        self.dtype = None
        self.number = None
        self.start_byte = None
        self.length = None
        self.unknown_constant = None
        self.unit = None

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
                    continue
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

    PARSE_TABLE = {
        'COLUMNS' : ('n_columns', int),
        'ROWS' : ('n_rows', int),
        'ROW_BYTES' : ('row_bytes', int),
    }
    TABLE_OBJECT_NAME = 'TABLE'
    COLUMN_OBJECT_NAME = 'COLUMN'
    COLUMN_CLASS = PdsTableColumn
    CHECK_COLUMN_COUNT = True

    def __init__(self, label_file, table_file):
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
                    continue
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
        for i, c in enumerate(self.columns):
            if c.name == column_name: return i
        return IndexError('Column name "%s" not found' % str(column_name))

    def get_column(self, column_name_or_idx, progress=True, cache=True):
        if type(column_name_or_idx) != int:
            cidx = self.get_column_idx(column_name_or_idx)
        else:
            cidx = column_name_or_idx

        if cidx in self._data_cache:
            return self._data_cache[cidx]

        else:
            column = self.columns[cidx]

            if progress:
                pbar = ProgressBar(widgets=[
                    'Reading column %d: ' % cidx, Bar('='), ' ', ETA()
                ])
            else:
                pbar = lambda x: x

            values = []
            with open(self.table_file, 'r') as f:
                for r in pbar(range(self.n_rows)):
                    f.seek(r*self.row_bytes + column.start_byte - 1)
                    value = f.read(column.length)
                    values.append(value)

            try:
                data_column = np.array(values, dtype=column.dtype)
            except TypeError:
                if progress:
                    pbar = ProgressBar(widgets=[
                        'Converting column %d: ' % cidx, Bar('='), ETA()
                    ])
                else:
                    pbar = lambda x: x
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

    SPECIAL_TYPES = {
        'IMAGE_TIME': themis_datetime,
        'SPACECRAFT_CLOCK_START_COUNT': ctx_sclk,
    }

class CtxTable(PdsTable): COLUMN_CLASS = CtxTableColumn

# ****************************************************************************
# THEMIS
# ****************************************************************************

class ThemisTableColumn(PdsTableColumn):

    PARSE_TABLE = {
        'NAME' : ('name', str),
        'COLUMN_NUMBER' : ('number', int),
        'DATA_TYPE': ('dtype', str),
        'START_BYTE': ('start_byte', int),
        'BYTES': ('length', int),
        'UNKNOWN_CONSTANT': ('unknown_constant', str),
        'UNIT' : ('unit', str),
    }

    SPECIAL_TYPES = {
        'START_TIME': themis_datetime,
        'STOP_TIME': themis_datetime,
        'SPACECRAFT_CLOCK_START_COUNT': float,
        'SPACECRAFT_CLOCK_STOP_COUNT': float,
        'START_TIME_ET': float,
        'STOP_TIME_ET': float,
        'UNCORRECTED_SCLK_START_COUNT': float,
        'BAND_NUMBER': int,
        'LOCAL_TIME': float,
    }

class ThemisTable(PdsTable): COLUMN_CLASS = ThemisTableColumn

# ****************************************************************************
# HiRISE
# ****************************************************************************

class HiRiseTableColumn(PdsTableColumn):

    SPECIAL_TYPES = {
        'OBSERVATION_START_TIME': hirise_datetime,
        'START_TIME': hirise_datetime,
        'OBSERVATION_START_COUNT': ctx_sclk,
        'STOP_TIME': hirise_datetime,
        'SPACECRAFT_CLOCK_START_COUNT': ctx_sclk,
        'SPACECRAFT_CLOCK_STOP_COUNT': ctx_sclk,
        'ADC_CONVERSION_SETTINGS': str,
    }

class HiRiseTable(PdsTable):
    COLUMN_CLASS = HiRiseTableColumn
    TABLE_OBJECT_NAME = 'EDR_INDEX_TABLE'
    CHECK_COLUMN_COUNT = False

# ****************************************************************************
# MOC
# ****************************************************************************

class MocTableColumn(PdsTableColumn):

    SPECIAL_TYPES = {
        'IMAGE_TIME': themis_datetime,
        'SPACECRAFT_CLOCK_START_COUNT': ctx_sclk,
        'PRODUCT_ID': moc_observation_id,
    }

class MocTable(PdsTable): COLUMN_CLASS = MocTableColumn

INSTRUMENT_TABLES = {
    'ctx': CtxTable,
    'themis_ir': ThemisTable,
    'themis_vis': ThemisTable,
    'hirise': HiRiseTable,
    'moc': MocTable,
}

def parse_table(label_file, table_file):
    instrument = determine_instrument(label_file)
    if instrument not in INSTRUMENT_TABLES:
        raise ValueError('Table parsing not implemented for %s' % instrument)

    return instrument, INSTRUMENT_TABLES[instrument](label_file, table_file)
