"""
Test of PDSC tools
"""
import mock
import pytest
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from .cosmic_test_tools import unit, mock_open

from pdsc.tools import _resize_scan_exposure_duration, fix_hirise_index

HIRISE_LBL_EXAMPLE = """
PDS_VERSION_ID = PDS3
RECORD_TYPE = FIXED_LENGTH
RECORD_BYTES = 27
FILE_RECORDS = 3
^EDR_INDEX_TABLE = "EDRCUMINDEX.TAB"
OBJECT = EDR_INDEX_TABLE
    INDEX_TYPE = SINGLE
    INTERCHANGE_FORMAT = ASCII
    ROWS = 3
    ROW_BYTES = 27
    COLUMNS = 2
    OBJECT = COLUMN
        NAME = VOLUME_ID
        DATA_TYPE = CHARACTER
        START_BYTE = 2
        BYTES = 10
        FORMAT = "A10"
        DESCRIPTION = "HiRISE volume identification"
    END_OBJECT
    OBJECT = COLUMN
        NAME = SCAN_EXPOSURE_DURATION
        DATA_TYPE = ASCII_REAL
        START_BYTE = 14
        BYTES = 9
        FORMAT = "F9.4"
        DESCRIPTION = "The time in microseconds ..."
    END_OBJECT
    OBJECT = COLUMN
        NAME = OTHER
        DATA_TYPE = CHARACTER
        START_BYTE = 25
        BYTES = 1
        FORMAT = "A1"
        DESCRIPTION = "Other"
    END_OBJECT
END_OBJECT
END
"""

HIRISE_TBL_EXAMPLE = """
"MROHR_0001",1438.5000,"A"
"MROHR_0002",1438.50000,"B"
"MROHR_0003",1438.5000,"C"
""".lstrip()

HIRISE_TBL_EXPECTED = """
"MROHR_0001",1438.5000,"A"
"MROHR_0002",1438.5000,"B"
"MROHR_0003",1438.5000,"C"
""".lstrip()

HIRISE_TBL_EXAMPLE2 = """
"MROHR_0001",1438.50000,"A"
"MROHR_0002",1438.50000,"B"
"MROHR_0003",1438.5000,"C"
""".lstrip()

HIRISE_TBL_EXAMPLE_OTHER = """
"MROHR_0001",1438.5000,"A"
"MROHR_0002",1438.5000,"BBB"
"MROHR_0003",1438.5000,'C"
""".lstrip()

HIRISE_TBL_EXAMPLE_CANT_REDUCE = """
"MROHR_0001",1438.5000,"A"
"MROHR_0002",1234567890,"B"
"MROHR_0003",1438.5000,'C"
""".lstrip()

HIRISE_TBL_EXAMPLE_PRECISION_LOSS = """
"MROHR_0001",1438.5000,"A"
"MROHR_0002",1438.50001,"B"
"MROHR_0003",1438.5000,"C"
""".lstrip()

class MockTempFile(object):

    MOCKED_FILES = []

    def __init__(self, *args, **kwargs):
        self.contents = StringIO()
        self.name = 'tempfile'

    def __enter__(self):
        return self

    def __exit__(self, *args):
        MockTempFile.MOCKED_FILES.append(self)

    def write(self, line):
        self.contents.write(line)

    @classmethod
    def reset(cls):
        cls.MOCKED_FILES = []

class MockProgress(object):

    def __init__(self, message): pass
    def start(self): pass
    def finish(self): pass
    def update(self, n): pass

class MockStatSt(object):

    def __init__(self, size):
        self.st_size = size

@unit
def test_resize_scan_exposure_duration():
    output = _resize_scan_exposure_duration(1.2345678, 0)
    assert output == None

    output = _resize_scan_exposure_duration(1.2345678, 3)
    assert output == '1.2'

    output = _resize_scan_exposure_duration(1.2345678, 5)
    assert output == '1.235'

    output = _resize_scan_exposure_duration(1438.50000, 9)
    assert output == '1438.5000'

@unit
@mock.patch('pdsc.table.open', mock_open)
@mock.patch('pdsc.tools.open', mock_open)
@mock.patch('pdsc.tools.NamedTemporaryFile', MockTempFile)
@mock.patch('pdsc.tools.move', autospec=True)
@mock.patch('pdsc.tools.get_idx_file_pair', autospec=True)
def test_fix_hirise_index(mock_idx_pair, mock_move):
    MockTempFile.reset()
    mock_idx_pair.return_value = (HIRISE_LBL_EXAMPLE, HIRISE_TBL_EXAMPLE)
    fix_hirise_index('idx', 'outputfile', True)
    mocked_tmp_file = MockTempFile.MOCKED_FILES.pop(0)
    assert mocked_tmp_file.contents.getvalue() == HIRISE_TBL_EXPECTED

@unit
@mock.patch('pdsc.table.open', mock_open)
@mock.patch('pdsc.tools.open', mock_open)
@mock.patch('pdsc.tools.NamedTemporaryFile', MockTempFile)
@mock.patch('pdsc.tools.standard_progress_bar', MockProgress)
@mock.patch('pdsc.tools.move', autospec=True)
@mock.patch('pdsc.tools.get_idx_file_pair', autospec=True)
@mock.patch('os.stat', autospec=True)
def test_fix_hirise_index_progress(mock_stat, mock_idx_pair, mock_move):
    MockTempFile.reset()
    mock_stat.return_value = MockStatSt(len(HIRISE_TBL_EXAMPLE))
    mock_idx_pair.return_value = (HIRISE_LBL_EXAMPLE, HIRISE_TBL_EXAMPLE)
    fix_hirise_index('idx', None, False)
    mocked_tmp_file = MockTempFile.MOCKED_FILES.pop(0)
    assert mocked_tmp_file.contents.getvalue() == HIRISE_TBL_EXPECTED

    MockTempFile.reset()
    mock_stat.return_value = MockStatSt(len(HIRISE_TBL_EXAMPLE2))
    mock_idx_pair.return_value = (HIRISE_LBL_EXAMPLE, HIRISE_TBL_EXAMPLE2)
    fix_hirise_index('idx', None, False)
    mocked_tmp_file = MockTempFile.MOCKED_FILES.pop(0)
    assert mocked_tmp_file.contents.getvalue() == HIRISE_TBL_EXPECTED

@unit
@mock.patch('pdsc.table.open', mock_open)
@mock.patch('pdsc.tools.open', mock_open)
@mock.patch('pdsc.tools.NamedTemporaryFile', MockTempFile)
@mock.patch('pdsc.tools.move', autospec=True)
@mock.patch('pdsc.tools.get_idx_file_pair', autospec=True)
def test_fix_hirise_index_errors(mock_idx_pair, mock_move):
    MockTempFile.reset()
    mock_idx_pair.return_value = (
        HIRISE_LBL_EXAMPLE, HIRISE_TBL_EXAMPLE_OTHER
    )
    with pytest.raises(RuntimeError):
        fix_hirise_index('idx', None, True)

    MockTempFile.reset()
    mock_idx_pair.return_value = (
        HIRISE_LBL_EXAMPLE, HIRISE_TBL_EXAMPLE_CANT_REDUCE
    )
    with pytest.raises(RuntimeError):
        fix_hirise_index('idx', None, True)

    MockTempFile.reset()
    mock_idx_pair.return_value = (
        HIRISE_LBL_EXAMPLE, HIRISE_TBL_EXAMPLE_PRECISION_LOSS
    )
    with pytest.warns(RuntimeWarning):
        fix_hirise_index('idx', None, True)
    mocked_tmp_file = MockTempFile.MOCKED_FILES.pop(0)
    assert mocked_tmp_file.contents.getvalue() == HIRISE_TBL_EXPECTED
