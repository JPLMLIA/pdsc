#!/usr/bin/env python
from __future__ import print_function
"""
Implmements server that wraps client for remote calls over HTTP
"""
import json
import cherrypy
from cherrypy import expose, HTTPError

from client import PdsClient
from metadata import json_dumps

def content_type(t):
    def decorator(f):
        f._cp_config = {
            'response.headers.Content-Type': t,
        }
        return f

    return decorator

class PdsServer(object):

    def __init__(self, database_directory=None,
            socket_host='127.0.0.1', port=2115):
        self.client = PdsClient(database_directory)

        self.socket_host = socket_host
        self.port = port

    def start(self):
        cherrypy.config.update({
            'server.socket_port' : self.port,
            'server.socket_host' : self.socket_host,
        })
        cherrypy.quickstart(self)

    @content_type('application/json')
    @expose
    def queryByObservationId(self, instrument, observation_ids):
        # TODO: Handle Bad arguments
        instrument = str(instrument)
        try:
            observation_ids = json.loads(observation_ids)
        except:
            observation_ids = str(observation_ids)

        if type(observation_ids) == list:
            observation_ids = map(str, observation_ids)
        else:
            observation_ids = str(observation_ids)
        metadata = self.client.query_by_observation_id(
            instrument, observation_ids)
        return json_dumps(metadata)

    @content_type('application/json')
    @expose
    def queryByLatLon(self, instrument, lat, lon, radius=0):
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
        instrument = str(instrument)
        observation_id = str(observation_id)
        other_instrument = str(other_instrument)
        observations = self.client.find_overlapping_observations(
            instrument, observation_id, other_instrument
        )
        return json.dumps(observations)

def main(database_directory, port, socket_host):
    server = PdsServer(
        database_directory=database_directory,
        port=port,
        socket_host=socket_host
    )
    server.start()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)

    parser.add_argument('-d', '--database_directory', default=None)
    parser.add_argument('-p', '--port', default=2115)
    parser.add_argument('-s', '--socket_host', default='127.0.0.1')

    args = parser.parse_args()
    main(**vars(args))
