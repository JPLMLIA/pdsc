"""
This module contains code to support various types of clients that can be used
to query PDSC for metadata or find observations coincident with a point on the
surface or another point.
"""
import os
import json
import sqlite3
import requests
from glob import glob

from .metadata import PdsMetadata, METADATA_DB_SUFFIX, json_loads

from .segment import (SegmentTree, PointQuery, TriSegment,
    SEGMENT_DB_SUFFIX, SEGMENT_TREE_SUFFIX)

DATABASE_DIRECTORY_VAR = 'PDSC_DATABASE_DIR'
"""
Environment variable that holds the PDSC ingested database directory

See :ref:`Environment Variables` for details.
"""

SERVER_VAR = 'PDSC_SERVER_HOST'
"""
Environment variable that holds the PDSC server host name

See :ref:`Environment Variables` for details.
"""

PORT_VAR = 'PDSC_SERVER_PORT'
"""
Environment variable that holds the PDSC server port

See :ref:`Environment Variables` for details.
"""

class PdsClient(object):
    """
    The :py:class:`PdsClient` class handles queries to a local PDSC database for
    looking up observations based on id or location
    """

    def __init__(self, database_directory=None):
        """
        :param database_directory:
            location of the PDSC databases; if ``None``, the
            ``PDSC_DATABASE_DIR`` environment variable is used to determine the
            database directory
        """
        if database_directory is None:
            database_directory = os.environ.get(DATABASE_DIRECTORY_VAR, None)

        if database_directory is None:
            raise ValueError(
                'Must specify database directory '
                'or set "%s" environment variable'
                % DATABASE_DIRECTORY_VAR
            )

        if not os.path.exists(database_directory):
            raise ValueError(
                'Database directory "%s" does not exist'
                % database_directory
            )

        db_files = glob(os.path.join(
            database_directory, '*%s' % METADATA_DB_SUFFIX))

        self.instruments = [
            os.path.basename(db)[:-len(METADATA_DB_SUFFIX)]
            for db in db_files
        ]
        self._db_files = dict([
            (i, f) for i, f in zip(self.instruments, db_files)])

        self._seg_files = {}
        self._seg_tree_files = {}
        self._seg_trees = {}
        for i in self.instruments:
            segfile = os.path.join(database_directory,
                '%s%s' % (i, SEGMENT_DB_SUFFIX))
            treefile = os.path.join(database_directory,
                '%s%s' % (i, SEGMENT_TREE_SUFFIX))
            if not (os.path.exists(segfile) and os.path.exists(treefile)):
                continue
            self._seg_files[i] = segfile
            self._seg_tree_files[i] = treefile
            self._seg_trees[i] = None

    def _get_seg_tree(self, instrument):
        if instrument not in self._seg_trees:
            raise ValueError(
                'Localization index not available for %s' % instrument)
        if self._seg_trees[instrument] is None:
            self._seg_trees[instrument] = SegmentTree.load(
                self._seg_tree_files[instrument])
        return self._seg_trees[instrument]

    def _query(self, instrument, conditions=None):
        """
        instrument: instrument name
        conditions: list of tuples (variable name, >/=/<, value)
        """
        if instrument not in self.instruments:
            raise ValueError('Instrument "%s" not found' % instrument)

        query_str = 'SELECT * FROM metadata'

        if conditions is None or len(conditions) == 0:
            query_tup = (query_str,)

        else:
            for t in conditions:
                if len(t) != 3:
                    raise ValueError('Invalid condition "%s"' % str(t))
                if t[1] not in ('<', '=', '>', '>=', '<='):
                    raise ValueError('Invalid comparator "%s"' % t[1])

            parts, values = zip(*[
                ('%s%s?' % (col, comp), val)
                for col, comp, val in conditions
            ])
            query_str += ' WHERE %s' % (
                ' and '.join(parts)
            )
            query_tup = (query_str, values)

        db_file = self._db_files[instrument]
        params = {'detect_types': sqlite3.PARSE_DECLTYPES}
        with sqlite3.connect(db_file, **params) as conn:
            cur = conn.cursor()
            cur.execute(*query_tup)
            names = [description[0] for description in cur.description]
            while True:
                row = cur.fetchone()
                if row is None: break
                valdict = dict(zip(names, row))
                yield PdsMetadata(instrument, **valdict)

    def query(self, instrument, conditions=None):
        """
        Supports a generic query of observations based on metadata

        :param instrument:
            PDSC instrument name

        :param conditions:
            a collection of tuples indicating query constraints; each tuple
            should contain three entries:

              - metadata variable name
              - comparator (``'='``, ``'<'``, ``'>'``, ``'<='``, ``'>='``)
              - value

            A SQL-like query will be performed with a logical AND of the
            specified conditions

        :return: a list of :py:class:`~pdsc.metata.PdsMetadata` objects
            corresponding to observations matching the specified query
            conditions

        >>> import pdsc
        >>> client = pdsc.PdsClient()
        >>> metadata = client.query('hirise_rdr', [
        ...     ('corner1_latitude', '>', -0.5),
        ...     ('corner1_latitude', '<',  0.5)
        ... ])

        .. Warning::
            This function currently assumes non-adversarial inputs; the current
            implementation allows a potential SQL injection attack.
        """
        return list(self._query(instrument, conditions))

    def query_by_observation_id(self, instrument, observation_ids):
        """
        Query observation matching any of the specified ``observation_ids``

        :param instrument:
            PDSC instrument name

        :param observation_ids:
            either a collection of observation ids, or a single observation id

        :return: a list of :py:class:`~pdsc.metadata.PdsMetadata` objects
            corresponding to observations matching the specified
            ``observation_ids``

        >>> import pdsc
        >>> client = pdsc.PdsClient()
        >>> metadata = client.query_by_observation_id(
        ...     'hirise_rdr', 'PSP_005423_1780'
        ... )
        >>> len(metadata)
        2
        >>> metadata[0].product_id
        u'PSP_005423_1780_COLOR'
        >>> metadata[1].product_id
        u'PSP_005423_1780_RED'

        >>> metadata = client.query_by_observation_id(
        ...     'hirise_rdr', ['PSP_010341_1775', 'PSP_010486_1775']
        ... )
        >>> len(metadata)
        4

        .. Note::
            Some instruments generate multiple data products per
            observation, os a single observation id might correspond to multiple
            :py:class:`~pdsc.metadata.PdsMetadata` objects for each data
            product.
        """
        if instrument not in self.instruments:
            raise ValueError('Instrument "%s" not found' % instrument)

        single_id = (type(observation_ids) == str)
        if single_id:
            observation_ids = [observation_ids]

        db_file = self._db_files[instrument]
        params = {'detect_types': sqlite3.PARSE_DECLTYPES}
        with sqlite3.connect(db_file, **params) as conn:
            cur = conn.cursor()
            values = set([])
            for oid in observation_ids:
                cur.execute(
                    'SELECT * FROM metadata WHERE observation_id=?', (oid,)
                )
                rows = cur.fetchall()
                values |= set(rows)
            names = [description[0] for description in cur.description]

        metadata = [
            PdsMetadata(instrument, **dict(zip(names, v)))
            for v in sorted(values)
        ]
        return metadata

    def _query_segments(self, instrument, segment_ids):
        db_file = self._seg_files[instrument]
        with sqlite3.connect(db_file) as conn:
            cur = conn.cursor()
            values = []
            for sid in segment_ids.tolist():
                cur.execute(
                    'SELECT * FROM segments WHERE segment_id=?', (sid,)
                )
                row = cur.fetchone()
                assert(row is not None)
                values.append(row)

        segments = [
            (v[1], TriSegment(v[2:4], v[4:6], v[6:8]))
            for v in values
        ]
        return segments

    def _get_observation_segments(self, instrument, observation_id):
        db_file = self._seg_files[instrument]
        with sqlite3.connect(db_file) as conn:
            cur = conn.cursor()
            cur.execute(
                'SELECT * FROM segments WHERE observation_id=?',
                (observation_id,)
            )
            values = cur.fetchall()

        segments = [
            TriSegment(v[2:4], v[4:6], v[6:8])
            for v in values
        ]
        return segments

    def find_observations_of_latlon(self, instrument, lat, lon, radius=0):
        """
        Find observations from a particular instrument that fall within a
        radius of the given location.

        :param instrument: PDSC instrument name
        :param lat: degrees latitude
        :param lon: degrees east longitude
        :param radius: query tolerance in meters

        :return: a list of observation ids corresponding to observations within
            ``radius`` of the given location

        >>> import pdsc
        >>> client = pdsc.PdsClient()
        >>> observation_ids = client.find_observations_of_latlon(
        ...     'hirise_rdr', -4.5, 137.4, radius=0
        ... )
        >>> observation_ids # doctest: +ELLIPSIS
        [u'ESP_018854_1755', u'ESP_018920_1755', ..., u'PSP_010639_1755']
        """
        assert(instrument in self._seg_files)
        tree = self._get_seg_tree(instrument)
        point = PointQuery(lat, lon, radius)
        idx = tree.query_point(point)
        segments = self._query_segments(instrument, idx)
        overlapping_observations = set([])
        for observation_id, seg in segments:
            if observation_id in overlapping_observations:
                continue
            if seg.includes_point(point):
                overlapping_observations.add(observation_id)

        return sorted(overlapping_observations)

    def find_overlapping_observations(self, instrument, observation_id,
            other_instrument):
        """
        Find observations from ``other_instrument`` that overlap observations
        with the given ``observation_id`` from ``instrument``.

        :param instrument: PDSC instrument name for query observation
        :param observation_id: query observation id
        :param other_instrument: PDSC instrument name for target instrument

        :return: a list of observation ids corresponding to observations
            overlapping the given observation

        >>> import pdsc
        >>> client = pdsc.PdsClient()
        >>> observation_ids = client.find_overlapping_observations(
        ...     'ctx', 'P09_004477_1906_XN_10N100W', 'hirise_rdr'
        ... )
        >>> observation_ids # doctest: +ELLIPSIS
        [u'ESP_015909_1890', u'ESP_016832_1885', ..., u'PSP_007246_1890']
        """

        for i in (instrument, other_instrument):
            assert(i in self._seg_files)

        tree = self._get_seg_tree(other_instrument)

        overlapping_observations = set([])
        for seg in self._get_observation_segments(instrument, observation_id):
            idx = tree.query_segment(seg)
            other_segments = self._query_segments(other_instrument, idx)
            for other_oid, other_seg in other_segments:
                if other_oid in overlapping_observations: continue
                if seg.overlaps_segment(other_seg):
                    overlapping_observations.add(other_oid)

        return sorted(overlapping_observations)

class PdsHttpClient(object):
    """
    The :py:class:`PdsHttpClient` class handles queries to a remote PDSC
    database over HTTP for looking up observations based on id or location.

    The interface for :py:class:`PdsHttpClient` is the same as for
    :py:class:`PdsClient`.
    """

    def __init__(self, host=None, port=None):
        """
        :param host: the hostname of the :py:class:`~pdsc.server.PdsServer` to
            query
        :param port: the port to use for queries
        """
        if port is None:
            port = os.environ.get(PORT_VAR, None)
            if port is not None:
                try:
                    port = int(port)
                except ValueError:
                    raise ValueError(
                        'Port must be integer (got "%s")'
                        % port
                    )

        if host is None:
            host = os.environ.get(SERVER_VAR, None)

        if host is None:
            raise ValueError(
                'Must specify server hostname '
                'or set "%s" environment variable'
                % SERVER_VAR
            )

        self.base_url = 'http://%s%s/' % (
            host,
            '' if port is None else (':%d' % port)
        )

    def query(self, instrument, conditions=None):
        url = self.base_url + 'query'
        params = {
            'instrument': instrument
        }
        if conditions is not None:
            params['conditions'] = json.dumps(conditions)
        response = requests.post(url, data=params)
        response.raise_for_status()
        return json_loads(response.text)

    def query_by_observation_id(self, instrument, observation_ids):
        url = self.base_url + 'queryByObservationId'
        if type(observation_ids) != str:
            observation_ids = list(observation_ids)
        params = {
            'instrument': instrument,
            'observation_ids': json.dumps(observation_ids)
        }
        response = requests.post(url, data=params)
        response.raise_for_status()
        return json_loads(response.text)

    def find_observations_of_latlon(self, instrument, lat, lon, radius=0):
        url = self.base_url + 'queryByLatLon'
        params = {
            'instrument': instrument,
            'lat': lat,
            'lon': lon,
            'radius': radius,
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return list(map(str, response.json()))

    def find_overlapping_observations(self, instrument, observation_id, other_instrument):
        url = self.base_url + 'queryByOverlap'
        params = {
            'instrument': instrument,
            'observation_id': observation_id,
            'other_instrument': other_instrument,
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return list(map(str, response.json()))
