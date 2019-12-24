"""
Unit Tests for Client Code
"""
import os
import mock
import pytest
import json
import numpy as np

from .cosmic_test_tools import unit, MockDbManager

from pdsc.client import (
    PdsClient, PdsHttpClient, PORT_VAR, SERVER_VAR,
    DATABASE_DIRECTORY_VAR, SEGMENT_DB_SUFFIX, SEGMENT_TREE_SUFFIX
)
from pdsc.metadata import (
    json_dumps, PdsMetadata, METADATA_DB_SUFFIX
)

TEST_SEGMENTS = [
    (0, 'obs1', 2.0, 1.0, 2.0, -1.0, -2.0, -1.0),
    (1, 'obs1', 2.0, 1.0, -2.0, -1.0, -2.0, 1.0),
    (2, 'obs2', 1.0, 2.0, 1.0, -2.0, -1.0, -2.0),
    (3, 'obs2', 1.0, 2.0, -1.0, -2.0, -1.0, 2.0),
    (4, 'obs3', 2.0, 91.0, 2.0, 89.0, -2.0, 89.0),
    (5, 'obs3', 2.0, 91.0, -2.0, 89.0, -2.0, 91.0),
]

class MockSegmentTree(object):
    """
    This mock class just returns all segments for every query; it should only
    be used for tests with small numbers of segments where effiiency of the
    proper tree implementation is not a concern
    """

    def __init__(self, n):
        self.n = n

    def query_point(self, point):
        return np.arange(self.n)

    def query_segment(self, segment):
        return np.arange(self.n)

    @staticmethod
    def load(inputfile):
        return MockSegmentTree(len(TEST_SEGMENTS))

@pytest.fixture()
def mock_db_manager():
    # Setup
    db_manager = MockDbManager()

    # Setup metadata DB
    metadata_file = os.path.join(
        'test_directory', 'test_instrument' + METADATA_DB_SUFFIX
    )
    conn = db_manager.new_connection(metadata_file)
    cur = conn.cursor()
    cur.execute(
        'CREATE TABLE metadata (observation_id text, field1 real)'
    )
    cur.executemany(
        'INSERT INTO metadata VALUES (?, ?)',
        [('obs1', 1.0), ('obs2', 2.0), ('obs3', 3.0)]
    )

    # Setup segment DB
    segment_file = os.path.join(
        'test_directory', 'test_instrument' + SEGMENT_DB_SUFFIX
    )
    conn = db_manager.new_connection(segment_file)
    cur = conn.cursor()
    cur.execute(
        'CREATE TABLE segments (segment_id integer, '
        'observation_id text, '
        'latitude0 real, longitude0 real, '
        'latitude1 real, longitude1 real, '
        'latitude2 real, longitude2 real)'
    )
    cur.execute('CREATE INDEX segment_index ON segments (segment_id)')
    cur.execute('CREATE INDEX observation_index ON segments (observation_id)')
    cur.executemany(
        'INSERT INTO segments VALUES (?, ?, ?, ?, ?, ?, ?, ?)', TEST_SEGMENTS
    )

    yield db_manager

    # Teardown
    db_manager.close()

@unit
@mock.patch('os.environ.get', autospec=True)
@mock.patch('requests.post', autospec=True)
@mock.patch('requests.get', autospec=True)
def test_http_client(mock_get, mock_post, mock_env):

    mock_env.reset_mock()
    mock_env.return_value = '1234'
    client = PdsHttpClient(host='localhost')
    mock_env.assert_called_once_with(PORT_VAR, None)
    assert client.base_url == 'http://localhost:1234/'

    mock_env.reset_mock()
    mock_env.return_value = '12.34'
    with pytest.raises(ValueError):
        client = PdsHttpClient(host='localhost')
    mock_env.assert_called_once_with(PORT_VAR, None)

    mock_env.reset_mock()
    mock_env.return_value = None
    client = PdsHttpClient(host='localhost')
    mock_env.assert_called_once_with(PORT_VAR, None)
    assert client.base_url == 'http://localhost/'

    mock_env.reset_mock()
    mock_env.return_value = 'localhost'
    client = PdsHttpClient(port=1234)
    mock_env.assert_called_once_with(SERVER_VAR, None)
    assert client.base_url == 'http://localhost:1234/'

    mock_env.reset_mock()
    mock_env.return_value = None
    with pytest.raises(ValueError):
        client = PdsHttpClient(port=1234)
    mock_env.assert_called_once_with(SERVER_VAR, None)

    # Port must be integer, not string
    with pytest.raises(TypeError):
        client = PdsHttpClient(host='localhost', port='1234')

    class MockResponse(object):

        def __init__(self, expected):
            self.expected = expected
            self.text = json_dumps(self.expected)

        def json(self):
            return self.expected

        def raise_for_status(self):
            pass

        def assert_expected(self, retval):
            assert retval == self.expected

    mock_response = MockResponse(['test_a', 'test_b'])
    mock_get.return_value = mock_response

    mock_get.reset_mock()
    client = PdsHttpClient(host='localhost', port=1234)
    overlapping = client.find_overlapping_observations(
        'instrument1', 'obsid', 'instrument2'
    )
    mock_get.assert_called_once_with(
        'http://localhost:1234/queryByOverlap',
        {
            'instrument': 'instrument1',
            'observation_id': 'obsid',
            'other_instrument': 'instrument2',
        }
    )
    mock_response.assert_expected(overlapping)

    mock_get.reset_mock()
    obs = client.find_observations_of_latlon('instrument', 0, 1, 2)
    mock_get.assert_called_once_with(
        'http://localhost:1234/queryByLatLon',
        {
            'instrument': 'instrument',
            'lat': 0,
            'lon': 1,
            'radius': 2,
        }
    )
    mock_response.assert_expected(obs)

    mock_response = MockResponse([PdsMetadata(
        instrument='test_instrument',
        field1='value1',
    )])
    mock_post.return_value = mock_response

    mock_post.reset_mock()
    obs = client.query_by_observation_id('instrument', 'obsid')
    mock_post.assert_called_once_with(
        'http://localhost:1234/queryByObservationId',
        {
            'instrument': 'instrument',
            'observation_ids': '"obsid"',
        }
    )
    mock_response.assert_expected(obs)

    mock_post.reset_mock()
    obs = client.query_by_observation_id('instrument', ['obsid1'])
    mock_post.assert_called_once_with(
        'http://localhost:1234/queryByObservationId',
        {
            'instrument': 'instrument',
            'observation_ids': '["obsid1"]',
        }
    )
    mock_response.assert_expected(obs)

    mock_post.reset_mock()
    obs = client.query('instrument')
    mock_post.assert_called_once_with(
        'http://localhost:1234/query',
        {
            'instrument': 'instrument',
        }
    )
    mock_response.assert_expected(obs)

    mock_post.reset_mock()
    obs = client.query('instrument', conditions=[
        ('corner1_latitude', '>', -0.5)
    ])
    mock_post.assert_called_once_with(
        'http://localhost:1234/query',
        {
            'instrument': 'instrument',
            'conditions': '[["corner1_latitude", ">", -0.5]]',
        }
    )
    mock_response.assert_expected(obs)

@unit
@mock.patch('os.environ.get', autospec=True)
@mock.patch('os.path.exists', autospec=True)
@mock.patch('pdsc.client.glob', autospec=True)
@mock.patch('pdsc.client.SegmentTree', MockSegmentTree)
def test_pds_client(mock_glob, mock_exists, mock_env, mock_db_manager):

    # No directory specified
    mock_glob.return_value = []
    mock_exists.return_value = True
    mock_env.return_value = None

    with pytest.raises(ValueError):
        client = PdsClient()

    mock_env.assert_called_once_with(DATABASE_DIRECTORY_VAR, None)

    # Directory does not exist
    test_directory = 'test_directory'
    mock_env.return_value = test_directory
    mock_exists.return_value = False
    mock_env.reset_mock()

    with pytest.raises(ValueError):
        client = PdsClient()

    mock_env.assert_called_once_with(DATABASE_DIRECTORY_VAR, None)
    mock_exists.assert_called_once_with(test_directory)

    # Successful, but no files found
    mock_env.reset_mock()
    mock_exists.reset_mock()
    mock_exists.return_value = True

    client = PdsClient()
    assert len(client.instruments) == 0
    assert len(client._db_files) == 0
    assert len(client._seg_files) == 0
    assert len(client._seg_tree_files) == 0
    assert len(client._seg_trees) == 0

    mock_env.assert_called_once_with(DATABASE_DIRECTORY_VAR, None)
    mock_exists.assert_called_once_with(test_directory)

    # Successful, one mock file
    test_instrument = 'test_instrument'
    mock_env.reset_mock()
    mock_exists.reset_mock()
    mock_exists.return_value = True
    mock_glob.return_value = [os.path.join(
        test_directory, (test_instrument + METADATA_DB_SUFFIX)
    )]

    test_seg_db = os.path.join(
        test_directory,
        test_instrument + SEGMENT_DB_SUFFIX
    )
    test_seg_tree = os.path.join(
        test_directory,
        test_instrument + SEGMENT_TREE_SUFFIX
    )

    client = PdsClient()
    assert len(client.instruments) == 1
    assert len(client._db_files) == 1
    assert len(client._seg_files) == 1
    assert len(client._seg_tree_files) == 1
    assert len(client._seg_trees) == 1

    mock_env.assert_called_once_with(DATABASE_DIRECTORY_VAR, None)
    mock_exists.assert_has_calls(list(map(mock.call, [
        test_directory, test_seg_db, test_seg_tree
        ])), any_order=True
    )

    # Test calls with bad instrument names
    with pytest.raises(ValueError):
        client._get_seg_tree('bad_instrument')

    with pytest.raises(ValueError):
        client.query('bad_instrument')

    with pytest.raises(ValueError):
        client.query_by_observation_id('bad_instrument', '')

    with pytest.raises(AssertionError):
        client.find_observations_of_latlon('bad_instrument', 0, 0)

    with pytest.raises(AssertionError):
        client.find_overlapping_observations('bad_instrument', '', '')

    seg_tree = client._get_seg_tree('test_instrument')
    assert seg_tree.n == len(TEST_SEGMENTS)

    with mock.patch('sqlite3.connect', mock_db_manager):
        # Nominal query for single id
        meta = client.query_by_observation_id(
            'test_instrument', 'obs1'
        )
        assert len(meta) == 1
        assert meta[0].observation_id == 'obs1'
        assert meta[0].field1 == 1.0

        # Nominal query for multiple ids
        meta = client.query_by_observation_id(
            'test_instrument', ['obs1', 'obs2']
        )
        assert len(meta) == 2

        # Query for missing id
        meta = client.query_by_observation_id(
            'test_instrument', 'obs4'
        )
        assert len(meta) == 0

        # Expect two observations of a point
        obs_ids = client.find_observations_of_latlon(
            'test_instrument', 0.0, 0.0
        )
        assert len(obs_ids) == 2
        assert 'obs1' in obs_ids
        assert 'obs2' in obs_ids

        # Expect one observation of a point
        obs_ids = client.find_observations_of_latlon(
            'test_instrument', 0.0, 90.0
        )
        assert len(obs_ids) == 1
        assert 'obs3' in obs_ids

        # Expect zero observation of a point
        obs_ids = client.find_observations_of_latlon(
            'test_instrument', 0.0, 180.0
        )
        assert len(obs_ids) == 0

        # Expect an overlapping observation
        obs_ids = client.find_overlapping_observations(
            'test_instrument', 'obs1', 'test_instrument'
        )
        assert len(obs_ids) == 2
        assert 'obs1' in obs_ids
        assert 'obs2' in obs_ids

        # Overlap is symmetric
        obs_ids = client.find_overlapping_observations(
            'test_instrument', 'obs2', 'test_instrument'
        )
        assert len(obs_ids) == 2
        assert 'obs1' in obs_ids
        assert 'obs2' in obs_ids

        # No additional overlapping observations
        obs_ids = client.find_overlapping_observations(
            'test_instrument', 'obs3', 'test_instrument'
        )
        assert len(obs_ids) == 1
        assert 'obs3' in obs_ids

        # Query all
        meta = client.query('test_instrument')
        assert len(meta) == 3

        # Query with conditions
        meta = client.query(
            'test_instrument',
            [
                ('field1', '<', 2.5),
                ('field1', '>', 1.5),
            ]
        )
        assert len(meta) == 1
        assert meta[0].observation_id == 'obs2'

        # Bad conditions
        with pytest.raises(ValueError):
            # Malformed conditions
            client.query('test_instrument', [('field1', )])

        with pytest.raises(ValueError):
            # Bad operator
            client.query('test_instrument', [('field1', '~', 1.0)])

def _isnt_tree_file(filename):
    """
    Returns True except for files with the SEGMENT_TREE_SUFFIX
    """
    return (SEGMENT_TREE_SUFFIX not in filename)

@unit
@mock.patch('os.environ.get', autospec=True)
@mock.patch('os.path.exists', wraps=_isnt_tree_file)
@mock.patch('pdsc.client.glob', autospec=True)
def test_pds_client_missing_file(mock_glob, mock_exists, mock_env):

    # Successful, but no files found
    mock_glob.return_value = ['test_instrument' + METADATA_DB_SUFFIX]
    mock_env.return_value = 'test_directory'

    client = PdsClient()
    assert len(client.instruments) == 1
    assert len(client._db_files) == 1
    assert len(client._seg_files) == 0
    assert len(client._seg_tree_files) == 0
    assert len(client._seg_trees) == 0
