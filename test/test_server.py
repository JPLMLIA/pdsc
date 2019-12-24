"""
Unit Tests for Server
"""
import mock
import pytest
import json

from .cosmic_test_tools import unit

from pdsc.server import PdsServer, content_type

@unit
@mock.patch('pdsc.cherrypy.config', autospec=True)
@mock.patch('pdsc.cherrypy.quickstart', autospec=True)
@mock.patch('pdsc.server.PdsClient', autospec=True)
def test_server(mock_client, mock_quickstart, mock_cherrypy_config):
    server = PdsServer()

    server.start()
    mock_quickstart.assert_called_once_with(server)
    mock_cherrypy_config.update.assert_called()

    mocked_result = ['expected result']
    server.client.query.return_value = mocked_result
    meta = server.query('test_instrument', '[]')
    server.client.query.assert_called_once_with('test_instrument', [])
    assert json.loads(meta) == mocked_result

    server.client.query.reset_mock()
    meta = server.query('test_instrument')
    server.client.query.assert_called_once_with('test_instrument', [])
    assert json.loads(meta) == mocked_result

    server.client.query_by_observation_id.return_value = mocked_result
    meta = server.queryByObservationId('test_instrument', 'obsid')
    server.client.query_by_observation_id.assert_called_once_with(
        'test_instrument', 'obsid'
    )
    assert json.loads(meta) == mocked_result

    server.client.query_by_observation_id.reset_mock()
    meta = server.queryByObservationId('test_instrument', '["obsid"]')
    server.client.query_by_observation_id.assert_called_once_with(
        'test_instrument', ['obsid']
    )
    assert json.loads(meta) == mocked_result

    server.client.find_observations_of_latlon.return_value = mocked_result
    meta = server.queryByLatLon('test_instrument', '1.0', '2.0', '3.0')
    server.client.find_observations_of_latlon.assert_called_once_with(
        'test_instrument', 1.0, 2.0, 3.0
    )
    assert json.loads(meta) == mocked_result

    server.client.find_overlapping_observations.return_value = mocked_result
    meta = server.queryByOverlap('instrument1', 'osbid', 'instrument2')
    server.client.find_overlapping_observations.assert_called_once_with(
        'instrument1', 'osbid', 'instrument2'
    )
    assert json.loads(meta) == mocked_result

@unit
def test_content_decorator():
    f = lambda: 0
    fprime = content_type('type')(f)
    assert hasattr(fprime, '_cp_config')
    assert fprime._cp_config['response.headers.Content-Type'] == 'type'
