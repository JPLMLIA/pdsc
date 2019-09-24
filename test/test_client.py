"""
Unit Tests for Client Code
"""
import mock
import pytest
import json

from cosmic_test_tools import unit

from pdsc.client import (
    PdsClient, PdsHttpClient, PORT_VAR, SERVER_VAR,
)
from pdsc.metadata import (
    json_dumps, PdsMetadata
)

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
