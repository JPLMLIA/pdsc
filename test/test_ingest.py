"""
Functional Test of Ingestion process
"""
import os
import mock
import pytest
import subprocess
from unittest import TestCase
from tempfile import mkdtemp
from shutil import rmtree
import numpy as np

from .cosmic_test_tools import functional, unit, MockDbManager

from pdsc.metadata import PdsMetadata
from pdsc.segment import TriSegmentedFootprint
from pdsc.ingest import (
    get_idx_file_pair, ingest_idx, store_segment_tree,
    store_segments, store_metadata
)

TEST_DATA = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'data'
)

TEST_META = PdsMetadata(
    'themis_ir', observation_id='themis_id',
    center_latitude=-54.121, center_longitude=202.748,
    lines=272, samples=320, north_azimuth=100.239,
    pixel_aspect_ratio=0.845, pixel_height=102.0, pixel_width=120.0,
)

TEST_CONFIG = {
    'scale_factors': {
        'col2': 2.0,
    },
    'index': [
        'col1',
    ],
    'columns': [
        ('col1', 'col1', 'integer'),
        ('col2', 'col2', 'real'),
    ],
}

class MockTable(object):

    def __init__(self, column_mapping):
        self.column_mapping = column_mapping

    def get_column(self, column_name):
        return self.column_mapping[column_name]

TEST_TABLE = MockTable({
    'col1': np.array([0, 1, 2]),
    'col2': np.array([3, 4, 5]),
})

class EvilTriSegmentedFootprint(TriSegmentedFootprint):
    """
    Subclasss of `TriSegmentedFootprint` that raises a `ValueError` the first
    time it is instantiated, then behaves normally all subsequent times.
    """

    BE_EVIL = True

    def __init__(self, *args):
        if EvilTriSegmentedFootprint.BE_EVIL:
            EvilTriSegmentedFootprint.BE_EVIL = False
            raise ValueError('Evil!')
        super(EvilTriSegmentedFootprint, self).__init__(*args)

@functional
class TestIngest(TestCase):

    def setUp(self):
        self.outputdir = mkdtemp()

    def test_ingest(self):
        self.assertTrue(os.path.exists(self.outputdir))
        process = subprocess.Popen([
            'pdsc_ingest',
            os.path.join(TEST_DATA, 'index.lbl'),
            self.outputdir,
            '-c', os.path.join(TEST_DATA, 'test_metadata.yaml'),
            '-e', os.path.join(TEST_DATA, 'test_extension.py')
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdoutdata, stderrdata = process.communicate()
        self.assertEqual(process.poll(), os.EX_OK)

    def tearDown(self):
        rmtree(self.outputdir)

@pytest.fixture()
def mock_db_manager():
    db_manager = MockDbManager()
    db_manager.new_connection('output.db')
    yield db_manager
    db_manager.close()

@unit
def test_get_idx_file_pair():
    output = get_idx_file_pair('cumindex.lbl')
    expected = ('cumindex.lbl', 'cumindex.tab')
    assert output == expected

    output = get_idx_file_pair('CUMINDEX.TAB')
    expected = ('CUMINDEX.LBL', 'CUMINDEX.TAB')
    assert output == expected

    with pytest.raises(ValueError):
        get_idx_file_pair('bad.ext')

@unit
@mock.patch('pdsc.ingest.open', new_callable=mock.mock_open)
@mock.patch('pdsc.yaml.load', autospec=True)
@mock.patch('os.path.exists', autospec=True)
@mock.patch('os.path.isdir', autospec=True)
@mock.patch('pdsc.ingest.store_metadata', autospec=True)
@mock.patch('pdsc.ingest.store_segments', autospec=True)
@mock.patch('pdsc.ingest.store_segment_tree', autospec=True)
@mock.patch('pdsc.ingest.parse_table', autospec=True)
def test_ingest_idx(mock_parse_table, mock_store_segment_tree,
        mock_store_segments, mock_store_metadata,
        mock_isdir, mock_exists, mock_load, mock_open):

    mock_parse_table.return_value = ('instrument_name', 'table_obj')
    mock_load.return_value = 'config_contents'
    mock_store_metadata.return_value = 'metadata'
    mock_store_segments.return_value = 'segments'

    mock_exists.return_value = False
    mock_isdir.return_value = True
    with pytest.raises(ValueError):
        ingest_idx('test.lbl', 'test.tbl', 'test_config', 'test_output')
        mock_exists.assert_called_with(os.path.join(
            'test_config',
            'instrument_name_metadata.yaml'
        ))

    mock_isdir.return_value = False
    with pytest.raises(ValueError):
        ingest_idx('test.lbl', 'test.tbl', 'test_config.yaml', 'test_output')
        mock_exists.assert_called_with('test_config.yaml')

    mock_exists.return_value = True
    ingest_idx('test.lbl', 'test.tbl', 'test_config.yaml', 'test_output')
    mock_open.assert_called_with('test_config.yaml', 'r')
    mock_store_metadata.assert_called_with(
        os.path.join('test_output', 'instrument_name_metadata.db'),
        'instrument_name', 'table_obj', 'config_contents'
    )
    mock_store_segments.assert_called_with(
        os.path.join('test_output', 'instrument_name_segments.db'),
        'metadata', 'config_contents'
    )
    mock_store_segment_tree.assert_called_with(
        os.path.join('test_output', 'instrument_name_segment_tree.pkl'),
        'segments'
    )

@unit
@mock.patch('pdsc.ingest.SegmentTree', autospec=True)
def test_store_segment_tree(mock_segment_tree):
    mock_tree = mock.Mock()
    mock_segment_tree.return_value = mock_tree
    store_segment_tree('outputfile', 'segments')
    mock_segment_tree.assert_called_with('segments')
    mock_tree.save.assert_called_with('outputfile')

@unit
@mock.patch('os.path.exists', autospec=True)
def test_store_segments(mock_exists, mock_db_manager):
    meta = [ TEST_META ]
    mock_exists.return_value = False
    with mock.patch('sqlite3.connect', mock_db_manager):
        store_segments('output.db', meta, {})

    with mock_db_manager('output.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM segments')
        results = cursor.fetchall()

    assert len(results) == 2

@unit
@mock.patch('os.path.exists', autospec=True)
@mock.patch('os.remove', autospec=True)
def test_store_segments_remove(mock_remove, mock_exists, mock_db_manager):
    meta = [ TEST_META ]
    mock_exists.return_value = True
    with mock.patch('sqlite3.connect', mock_db_manager):
        store_segments('output.db', meta, {})
    mock_remove.assert_called_with('output.db')

@unit
@mock.patch('os.path.exists', autospec=True)
@mock.patch('pdsc.ingest.TriSegmentedFootprint', EvilTriSegmentedFootprint)
def test_store_segments_execption(mock_exists, mock_db_manager):
    meta = [ TEST_META, TEST_META ]
    mock_exists.return_value = False
    with mock.patch('sqlite3.connect', mock_db_manager):
        store_segments('output.db', meta, {})

    with mock_db_manager('output.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM segments')
        results = cursor.fetchall()

    assert len(results) == 2

@unit
@mock.patch('os.path.exists', autospec=True)
def test_store_metadata(mock_exists, mock_db_manager):
    mock_exists.return_value = False
    with mock.patch('sqlite3.connect', mock_db_manager):
        metadata = store_metadata(
            'output.db', 'instrument_name', TEST_TABLE, TEST_CONFIG
        )

    assert len(metadata) == 3
    assert metadata[0] == PdsMetadata('instrument_name', col1=0, col2=6.0)
    assert metadata[1] == PdsMetadata('instrument_name', col1=1, col2=8.0)
    assert metadata[2] == PdsMetadata('instrument_name', col1=2, col2=10.0)

    with mock_db_manager('output.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM metadata')
        results = cursor.fetchall()

    assert len(results) == 3

@unit
@mock.patch('os.path.exists', autospec=True)
@mock.patch('os.remove', autospec=True)
def test_store_metadata_remove(mock_remove, mock_exists, mock_db_manager):
    mock_exists.return_value = True
    with mock.patch('sqlite3.connect', mock_db_manager):
        metadata = store_metadata(
            'output.db', 'instrument_name', TEST_TABLE, TEST_CONFIG
        )
    mock_remove.assert_called_with('output.db')
