"""
Implmements an HTTP server that wraps client for remote calls to PDSC
"""
from __future__ import print_function
import json
import cherrypy
from cherrypy import expose, HTTPError

from .client import PdsClient
from .metadata import json_dumps

DEFAULT_SERVER_PORT = 7372
"""
The default PDSC server port (7372 is P-D-S-C on a numeric keypad)
"""

DEFAULT_SOCKET_TIMEOUT = 10000
"""
The default PDSC server socket timeout in seconds
"""

def content_type(t):
    """
    Creates a decorator to set the response ``Content-Type`` header for CherryPy
    response handlers

    :param t: content type

    :return: content type decorator
    """
    def decorator(f):
        f._cp_config = {
            'response.headers.Content-Type': t,
        }
        return f

    return decorator

class PdsServer(object):
    """
    Implements an HTTP server for PDSC using :py:mod:`cherrypy`

    .. Warning::
        The PDSC server is not yet designed to be robust against malicious
        queries. While some care has been taken to properly parse arguments to
        avoid SQL injection attacks, for example, a thorough review of
        potential security vulnerabilities has not yet been performed.
    """

    def __init__(self, database_directory=None,
            socket_host='0.0.0.0', port=DEFAULT_SERVER_PORT):
        """
        :param database_directory:
            location of the PDSC databases; if ``None``, the
            ``PDSC_DATABASE_DIR`` environment variable is used to determine the
            database directory

        :param socket_host:
            specifies the network interface on which the server will listen

        :param port:
            specifies the port on which the server will listen
        """
        self.client = PdsClient(database_directory)

        self.socket_host = socket_host
        self.port = port

    def start(self):
        """
        Starts the server; this function will block until the process is
        interrupted or killed
        """
        cherrypy.config.update({
            'server.socket_port' : self.port,
            'server.socket_host' : self.socket_host,
            'server.socket_timeout': DEFAULT_SOCKET_TIMEOUT,
        })
        cherrypy.quickstart(self)

    @content_type('application/json')
    @expose
    def query(self, instrument, conditions=None):
        """
        Serves an interface to :py:meth:`PdsClient.query
        <pdsc.client.PdsClient.query>`

        :param instrument:
            PDSC instrument name

        :param conditions:
            JSON-encoded conditions of the kind described for
            :py:meth:`PdsClient.query <pdsc.client.PdsClient.query>`

        :return: JSON-encoded list of :py:class:`~pdsc.metadata.PdsMetadata`
            objects corresponding to observations matching the specified query
            conditions
        """
        instrument = str(instrument)
        if conditions is None:
            conditions = []
        else:
            conditions = json.loads(conditions)
        metadata = self.client.query(instrument, conditions)
        return json_dumps(metadata)

    @content_type('application/json')
    @expose
    def queryByObservationId(self, instrument, observation_ids):
        """
        Serves an interface to :py:meth:`PdsClient.query_by_observation_id
        <pdsc.client.PdsClient.query_by_observation_id>`

        :param instrument:
            PDSC instrument name

        :param observation_ids:
            either a JSON-encoded list of observation ids, or a single
            observation id string

        :return: JSON-encoded list of :py:class:`~pdsc.metadata.PdsMetadata`
            objects corresponding to observations matching the specified
            ``observation_ids``
        """
        # TODO: Handle Bad arguments
        instrument = str(instrument)
        try:
            observation_ids = json.loads(observation_ids)
        except:
            observation_ids = str(observation_ids)

        if type(observation_ids) == list:
            observation_ids = list(map(str, observation_ids))
        else:
            observation_ids = str(observation_ids)
        metadata = self.client.query_by_observation_id(
            instrument, observation_ids)
        return json_dumps(metadata)

    @content_type('application/json')
    @expose
    def queryByLatLon(self, instrument, lat, lon, radius=0):
        """
        Serves an interface to :py:meth:`PdsClient.find_observations_of_latlon
        <pdsc.client.PdsClient.find_observations_of_latlon>`

        :param instrument: PDSC instrument name
        :param lat: degrees latitude
        :param lon: degrees east longitude
        :param radius: query tolerance in meters

        :return: JSON-encoded list of observation ids corresponding to
            observations within ``radius`` of the given location
        """
        instrument = str(instrument)
        lat = float(lat)
        lon = float(lon)
        radius = float(radius)
        observations = self.client.find_observations_of_latlon(
            instrument, lat, lon, radius
        )
        return json.dumps(observations)

    @content_type('application/json')
    @expose
    def queryByOverlap(self, instrument, observation_id, other_instrument):
        """
        Serves an interface to :py:meth:`PdsClient.find_observations_of_latlon
        <pdsc.client.PdsClient.find_observations_of_latlon>`

        :param instrument: PDSC instrument name for query observation
        :param observation_id: query observation id
        :param other_instrument: PDSC instrument name for target instrument

        :return: JSON-encoded list of observation ids corresponding to
            observations overlapping the given observation
        """
        instrument = str(instrument)
        observation_id = str(observation_id)
        other_instrument = str(other_instrument)
        observations = self.client.find_overlapping_observations(
            instrument, observation_id, other_instrument
        )
        return json.dumps(observations)
