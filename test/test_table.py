"""
Unit Tests for Table Code
"""
import mock
import pytest
import builtins
import datetime
import numpy as np
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from contextlib import contextmanager
from numpy.testing import assert_equal

from .cosmic_test_tools import unit, mock_open

import pdsc
from pdsc.table import (
    parse_table, parse_simple_label, determine_instrument,
    themis_datetime, hirise_datetime, ctx_sclk, moc_observation_id,
    PdsColumnType, PdsTableColumn, ThemisTableColumn,
    HiRiseTableColumn, MocTableColumn, CtxTableColumn,
    PdsTable, ThemisTable
)

@unit
def test_parse_simple_label():

    contents = """
    TEST_KEY1 = "TEST_VALUE1"
    TEST_KEY2 = TEST_VALUE2
    """

    value = parse_simple_label(contents, 'TEST_KEY1')
    assert value == 'TEST_VALUE1'

    value = parse_simple_label(contents, 'TEST_KEY2')
    assert value == 'TEST_VALUE2'

    value = parse_simple_label(contents, 'TEST_KEY3')
    assert value is None

def _ilabel(instrument):
    """
    Helper function to return an instrument name label entry
    """
    return 'INSTRUMENT_NAME = "%s"' % instrument

THEMIS_BASE = _ilabel('THERMAL EMISSION IMAGING SYSTEM')
THEMIS_VIS = THEMIS_BASE + '\nDETECTOR_ID = "VIS"'
THEMIS_IR = THEMIS_BASE + '\nDETECTOR_ID = "IR"'

@unit
@pytest.mark.parametrize(
    'content,expected',
    [
        ('HiRISE EDR_INDEX_TABLE', 'hirise_edr'),
        ('HiRISE RDR_INDEX_TABLE', 'hirise_rdr'),
        (THEMIS_VIS, 'themis_vis'),
        (THEMIS_IR, 'themis_ir'),
        (_ilabel('CONTEXT CAMERA'), 'ctx'),
        (_ilabel('MARS ORBITER CAMERA'), 'moc'),
        ('UNKNOWN', None),
    ]
)
def test_determiner(content, expected):
    if expected is None:
        pytest.raises(ValueError, determine_instrument, content)
    else:
        assert expected == determine_instrument(content)

@unit
@pytest.mark.parametrize(
    'util,input_value,expected',
    [
        (themis_datetime,
            '1985-10-26T01:20:00.000',
            datetime.datetime(1985, 10, 26, 1, 20)),
        (hirise_datetime,
            '1985-10-26T01:20:00',
            datetime.datetime(1985, 10, 26, 1, 20)),
        (ctx_sclk, '10:1', 10.1),
        (moc_observation_id, 'FHA/00469', 'FHA00469'),
    ]
)
def test_parsing_util(util, input_value, expected):
    assert expected == util(input_value)

@unit
def test_column_type_wrapper():
    f = PdsColumnType(themis_datetime)
    assert repr(f) == '<function themis_datetime>'
    assert (
        f('1985-10-26T01:20:00.000') ==
        datetime.datetime(1985, 10, 26, 1, 20)
    )

THEMIS_COLUMN_EXAMPLE = """
  OBJECT                      = COLUMN
    NAME                      = OBSERVATION_ID
    COLUMN_NUMBER             = 1
    DATA_TYPE                 = CHARACTER
    START_BYTE                = 2
    BYTES                     = 9
    DESCRIPTION               = "Unique identifier for a THEMIS data product
                                 composed of the PRODUCT_ID without the
                                 three character processing type suffix."
  END_OBJECT                  = COLUMN
"""

MOC_COLUMN_EXAMPLE = """
OBJECT = COLUMN
NAME = PRODUCT_ID
COLUMN_NUMBER = 3
DATA_TYPE = CHARACTER
START_BYTE = 36
BYTES = 12
FORMAT = "A12"
DESCRIPTION = "product id"
END_OBJECT = COLUMN
"""

HIRISE_COLUMN_EXAMPLE = """
    OBJECT = COLUMN
        NAME = ADC_CONVERSION_SETTINGS
        DATA_TYPE = ASCII_INTEGER
        START_BYTE = 666
        BYTES = 3
        ITEMS = 2
        ITEM_BYTES = 1
        ITEM_OFFSET = 2
        FORMAT = "I1"
        DESCRIPTION = "Analog to digital waveform sampling timing 
                   settings, a vector of two values"
    END_OBJECT
"""

CTX_COLUMN_EXAMPLE = """
OBJECT = COLUMN
NAME = IMAGE_TIME
COLUMN_NUMBER = 5
DATA_TYPE = CHARACTER
START_BYTE = 100
BYTES = 23
FORMAT = "A23"
DESCRIPTION = "SCET time at start of image"
END_OBJECT = COLUMN
"""

THEMIS_COLUMN_EXAMPLE_UNKNOWN = """
  OBJECT                      = COLUMN
    NAME                      = SAMPLE_RESOLUTION
    COLUMN_NUMBER             = 20
    DATA_TYPE                 = ASCII_REAL
    START_BYTE                = 252
    BYTES                     = 5
    UNKNOWN_CONSTANT          = 32767
    UNIT                      = "KM"
    DESCRIPTION               = "The horizontal size of a pixel at the center
                                 of the image as projected onto the surface
                                 of the target."
  END_OBJECT                  = COLUMN
"""

@unit
@pytest.mark.parametrize(
    'column_str, column_cls, expected',
    [
        # Empty line fails
        ("\n", PdsTableColumn, None),
        (
            THEMIS_COLUMN_EXAMPLE,
            ThemisTableColumn,
            {
                'name': 'OBSERVATION_ID',
                'dtype': str,
                'number': 1,
                'start_byte': 2,
                'length': 9,
                'unknown_constant': None,
            }
        ),
        (
            MOC_COLUMN_EXAMPLE,
            MocTableColumn,
            {
                'name': 'PRODUCT_ID',
                'number': 3,
                'start_byte': 36,
                'length': 12,
                'unknown_constant': None,
            }
        ),
        (
            HIRISE_COLUMN_EXAMPLE,
            HiRiseTableColumn,
            {
                'name': 'ADC_CONVERSION_SETTINGS',
                'dtype': str,
                'number': None,
                'start_byte': 666,
                'length': 3,
                'unknown_constant': None,
            }
        ),
        (
            CTX_COLUMN_EXAMPLE,
            CtxTableColumn,
            {
                'name': 'IMAGE_TIME',
                'number': 5,
                'start_byte': 100,
                'length': 23,
                'unknown_constant': None,
            }
        ),
        (
            THEMIS_COLUMN_EXAMPLE_UNKNOWN,
            ThemisTableColumn,
            {
                'name': 'SAMPLE_RESOLUTION',
                'dtype': float,
                'number': 20,
                'start_byte': 252,
                'length': 5,
                'unknown_constant': 32767,
            }
        ),
    ]
)
def test_column(column_str, column_cls, expected):
    handle = StringIO(column_str)

    # Read the first line, since the function expects that the object has
    # already been encountered
    handle.readline()

    if expected is None:
        pytest.raises(ValueError, column_cls, handle)
    else:
        column = column_cls(handle)
        for k, v in expected.items():
            assert getattr(column, k) == v

THEMIS_LBL_EXAMPLE = """
PDS_VERSION_ID                = PDS3
RECORD_TYPE                   = FIXED_LENGTH
MISSION_NAME                  = "2001 MARS ODYSSEY"
INSTRUMENT_NAME               = "THERMAL EMISSION IMAGING SYSTEM"
DETECTOR_ID                   = "VIS"

OBJECT                        = TABLE
  NAME                        = THMIDX_VIS
  COLUMNS                     = 3
  ROW_BYTES                   = 44
  ROWS                        = 2

  OBJECT                      = COLUMN
    NAME                      = OBSERVATION_ID
    COLUMN_NUMBER             = 1
    DATA_TYPE                 = CHARACTER
    START_BYTE                = 2
    BYTES                     = 9
  END_OBJECT                  = COLUMN

  OBJECT                      = COLUMN
    NAME                      = START_TIME
    COLUMN_NUMBER             = 2
    DATA_TYPE                 = CHARACTER
    START_BYTE                = 13
    BYTES                     = 23
  END_OBJECT                  = COLUMN

  OBJECT                      = COLUMN
    NAME                      = CENTER_LATITUDE
    COLUMN_NUMBER             = 3
    DATA_TYPE                 = ASCII_REAL
    START_BYTE                = 37
    BYTES                     = 7
    UNKNOWN_CONSTANT          = 32767
    UNIT                      = "DEGREE"
  END_OBJECT                  = COLUMN

END_OBJECT                    = TABLE

END
"""

THEMIS_TBL_EXAMPLE = """
"V00816002",2002-02-19T19:00:29.623, 37.534
"V00816005",2002-02-19T19:11:18.520,  32767
""".strip()

@unit
@mock.patch('pdsc.table.open', mock_open)
def test_table(monkeypatch):

    # Nominal test cases
    t = ThemisTable(THEMIS_LBL_EXAMPLE, THEMIS_TBL_EXAMPLE)

    # We can lookup columns by name
    assert t.get_column_idx('OBSERVATION_ID') == 0
    pytest.raises(IndexError, t.get_column_idx, 'UNKNOWN')

    # We can get columns by idx or name
    obs_id_by_idx = t.get_column(0)
    obs_id_by_name = t.get_column('OBSERVATION_ID')
    assert_equal(obs_id_by_idx, obs_id_by_name)
    assert_equal(obs_id_by_idx, ['V00816002', 'V00816005'])

    # Test conversions of complex data type columns
    start = t.get_column('START_TIME')
    assert_equal(start, [
        themis_datetime('2002-02-19T19:00:29.623'),
        themis_datetime('2002-02-19T19:11:18.520'),
    ])

    # Test filling unknown values
    lat = t.get_column('CENTER_LATITUDE')
    assert_equal(lat, [37.534, np.nan])

    # Test column count mis-match
    mismatched_example = THEMIS_LBL_EXAMPLE.replace(
        'COLUMNS                     = 3',
        'COLUMNS                     = 2',
    )
    pytest.raises(ValueError, ThemisTable, mismatched_example, None)

    # Patch "CHECK_COLUMN_COUNT" to False to ensure that no error is raised
    monkeypatch.setattr(ThemisTable, 'CHECK_COLUMN_COUNT', False)
    t = ThemisTable(mismatched_example, None)
    assert t.n_columns == 2
    assert len(t.columns) == 3
    monkeypatch.undo()
    assert ThemisTable.CHECK_COLUMN_COUNT == True

    # Empty file leads to error
    pytest.raises(RuntimeError, ThemisTable, "", "")

    # We can handle missing column numbers
    missing_col_numbers = THEMIS_LBL_EXAMPLE.replace(
        'COLUMN_NUMBER', 'BAD_COLUMN_NUMBER'
    )
    t = ThemisTable(missing_col_numbers, None)
    assert t.get_column_idx('OBSERVATION_ID') == 0
    assert t.get_column_idx('START_TIME') == 1
    assert t.get_column_idx('CENTER_LATITUDE') == 2

    # Check case when the table object type is not specified
    no_object_id = THEMIS_LBL_EXAMPLE.replace(
        'END_OBJECT                    = TABLE',
        'END_OBJECT'
    )
    t = ThemisTable(no_object_id, None)
    assert t.n_columns == 3

@unit
@mock.patch('pdsc.table.open', mock_open)
def test_parse_table(monkeypatch):

    # Nominal case
    instrument, table = parse_table(THEMIS_LBL_EXAMPLE, THEMIS_TBL_EXAMPLE)
    assert instrument == 'themis_vis'

    # Temporarily clear out instrument table mapping
    monkeypatch.setattr(pdsc.table, 'INSTRUMENT_TABLES', {})
    pytest.raises(ValueError, parse_table, THEMIS_LBL_EXAMPLE, THEMIS_TBL_EXAMPLE)
    monkeypatch.undo()
