"""
Injests PDS metadata into databases and index structures for quick querying
"""
from __future__ import print_function
import os
import yaml
import sqlite3

from .table import parse_table
from .metadata import PdsMetadata, METADATA_DB_SUFFIX
from .segment import (
    SEGMENT_DB_SUFFIX, SEGMENT_TREE_SUFFIX,
    TriSegmentedFootprint, SegmentTree)
from .util import standard_progress_bar

# https://tharsis.gsfc.nasa.gov/geodesy.html
MARS_RADIUS_M = 3396200.
#https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html
MOON_RADIUS_M = 1736000

DEFAULT_CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'config',
)

CUMIDX_EXT_PAIRS = (
    # Label File, Table File
    ('LBL', 'TAB'),
    ('lbl', 'tab'),
)
"""
The list of valid cumulative index file extension pairs; the first is the
extension of the label file and the second is the extension of the corresponding
table file
"""

def get_idx_file_pair(path):
    """
    Returns the pair of corresponding LBL and TAB files given the path to one
    file of the pair. The case of the extension does not matter as long as it is
    consitent (i.e., all upper-case or all lower-case). The corresponding case
    and path prefix is assumed for the matching file.

    >>> get_idx_file_pair('cumindex.lbl')
    ('cumindex.lbl', 'cumindex.tab')
    >>> get_idx_file_pair('CUMINDEX.TAB')
    ('CUMINDEX.LBL', 'CUMINDEX.TAB')

    :param path:
        path to one LBL or TAB file from a pair

    :return: a pair of paths to corresponding LBL and TAB files
    """
    for l_ext, t_ext in CUMIDX_EXT_PAIRS:
        if path.endswith(l_ext):
            return (
                path,
                path[:-len(l_ext)] + t_ext
            )
        elif path.endswith(t_ext):
            return (
                path[:-len(t_ext)] + l_ext,
                path
            )

    raise ValueError('"%s" not part of any known index pair' % path)

def store_metadata(outputfile, instrument, table, config):
    """
    Converts and stores metadata into a SQL database file in accordance with
    configuration, given a PDS cumulative index table

    :param outputfile:
        output location for SQL database

    :param instrument:
        PDSC instrument name

    :param table:
        :py:class:`~pdsc.table.PdsTable` containing parsed metadata

    :param config:
        dict containing configuration; the entries used in this function are:

            - ``scale_factors``: dictionary mapping PDS cumulative index field
              names to multiplicative scale factors (e.g., for unit conversion)
            - ``index``: list containing PDSC metadata column names on which to
              build a SQL index
            - ``columns``: list of lists; each sub-list corresponds to a column
              and is a triple containing:

                - PDS cumulative index field name
                - PDSC metadata column name
                - PDSC metadata column type (a valid SQL type)

    :return: a list of :py:class:`~pdsc.metadata.PdsMetadata` objects
        associated with every entry in the created metadata table
    """
    scale_factors = config.get('scale_factors', {})
    index = config.get('index', [])
    columns = config.get('columns', [])

    converted_columns = [
        table.get_column(c[0]) if c[0] not in scale_factors else
        scale_factors[c[0]]*table.get_column(c[0])
        for c in columns
    ]
    values = zip(*map(lambda a: a.tolist(), converted_columns))

    if os.path.exists(outputfile):
        os.remove(outputfile)

    with sqlite3.connect(outputfile) as conn:
        cur = conn.cursor()
        cur.execute(
            'CREATE TABLE metadata (%s)' %
            ', '.join(['%s %s' % tuple(c[1:]) for c in columns])
        )

        for idx_col in index:
            print('Creating index on "%s"' % idx_col)
            cur.execute(
                'CREATE INDEX %s_index ON metadata (%s)' %
                (idx_col, idx_col)
            )

        cur.executemany(
            'INSERT INTO metadata VALUES (%s)' %
            ', '.join(['?' for _ in columns]),
            values
        )

        cur.execute('SELECT * FROM metadata')
        names = [description[0] for description in cur.description]

        progress = standard_progress_bar('Converting Metadata')
        return [
            PdsMetadata(instrument, **dict(zip(names, v)))
            for v in progress(cur.fetchall())
        ]

def store_segments(outputfile, metadata, config, body_radius=MARS_RADIUS_M):
    """
    Segments observations corresponding to each entry in ``metadata``, and
    stores these segments in a SQL database

    :param outputfile:
        output location for SQL database

    :param metadata:
        list of :py:class:`~pdsc.metadata.PdsMetadata` objects corresponding to
        observations to be segmented

    :param config:
        dict containing configuration; the entries used in this function are:

            - ``segmentation``: dictionary containing segmentation-specific
              parameters:

                - ``resolution``: the maximum size in meters of a side length in
                  the triangular segmentation of an observation; a good
                  heuristic is the average across-track width of an observation
                  to produce isosceles triangles.
                - ``localizer_kwargs``: the ``kwargs`` that will be supplied to
                  the :py:meth:`~pdsc.localization.get_localizer` function for
                  determining observation footprints
    :param body_radius:
        radius of celestial body, default is mars

    :return: a list of :py:class:`~pdsc.segment.TriSegment` objects for segments
        across all observations
    """
    seg_config = config.get('segmentation', {})
    resolution = seg_config.get('resolution', 50000)
    localizer_kwargs = seg_config.get('localizer_kwargs', {})

    observation_ids = []
    segments = []
    progress = standard_progress_bar('Segmenting footprints')
    for m in progress(metadata):
        try:
            # erd: if not Mars, store body radius
            if body_radius == MARS_RADIUS_M:
                s = TriSegmentedFootprint(m, resolution, localizer_kwargs)
            else:
                s = TriSegmentedFootprint(m, resolution, localizer_kwargs, body_radius)
            for si in s.segments:
                segments.append(si)
                # erd: check if observation_id attribute exists
                if hasattr(s.metadata, 'observation_id'):
                    observation_ids.append(s.metadata.observation_id)
                else:
                    raise ValueError('Please rename your index col to observation_id in the config file')
                    # erd: lroc does not have observation_id
                    #observation_ids.append(s.metadata.file_specification_name)
        except (TypeError, ValueError):
            continue

    segment_generator = (
        (i, oid) + tuple(si.latlon_points.ravel(order='C'))
        for i, (oid, si) in enumerate(zip(observation_ids, segments))
    )

    if os.path.exists(outputfile):
        os.remove(outputfile)

    with sqlite3.connect(outputfile) as conn:
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
            'INSERT INTO segments VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            segment_generator
        )

    return segments

def store_segment_tree(outputfile, segments, body_radius=MARS_RADIUS_M):
    """
    Constructs a ball tree index for segmented observations and saves the
    resulting data structure to the specified output file.

    :param outputfile:
        file to save pickled :py:class:`~pdsc.segment.SegmentTree`

    :param segments:
        a collection of :py:class:`~pdsc.segment.TriSegment` objects

    :body_radius:
        celestial body radius, default is Mars
    """
    if body_radius == MARS_RADIUS_M:
        tree = SegmentTree(segments)
    else:
        tree = SegmentTree(segments, True, body_radius)
    tree.save(outputfile)

def ingest_idx(label_file, table_file, configpath, outputdir):
    """
    Ingests a PDS cumulative index into PDSC

    :param label_file:
        a PDS cumulative index LBL file path

    :param table_file:
        a PDS cumulative index TAB file path

    :param configpath:
        a configuration file or a directory containing the configuration file
        with name ``[instrument name]_metadata.yaml``

    :param outputdir:
        the directory into which the ingested SQL databases and index structures
        will be stored
    """
    instrument, table = parse_table(label_file, table_file)

    # erd: radius will differ if mars vs moon
    if 'lroc' in instrument:
        # use moon radius
        body_radius = MOON_RADIUS_M
        print('using Moon radius in ingest_idx: ')
        print(body_radius)
    else:
        body_radius = MARS_RADIUS_M 
        print('using Mars radius in ingest_idx: ')
        print(body_radius)

    if os.path.isdir(configpath):
        configfile = os.path.join(configpath, '%s_metadata.yaml' % instrument)
    else:
        configfile = configpath

    if not os.path.exists(configfile):
        raise ValueError(
            'Required config file "%s" does not exist' %
            configfile
        )

    with open(configfile, 'r') as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)

    outputfile = os.path.join(
        outputdir,
        '%s%s' % (instrument, METADATA_DB_SUFFIX)
    )

    metadata = store_metadata(outputfile, instrument, table, config)

    outputfile = os.path.join(
        outputdir,
        '%s%s' % (instrument, SEGMENT_DB_SUFFIX)
    )
    if body_radius == MARS_RADIUS_M:
        segments = store_segments(outputfile, metadata, config)
    else:
        segments = store_segments(outputfile, metadata, config, body_radius)

    outputfile = os.path.join(
        outputdir,
        '%s%s' % (instrument, SEGMENT_TREE_SUFFIX)
    )
    if body_radius == MARS_RADIUS_M:
        store_segment_tree(outputfile, segments)
    else:
        if (segments != []):
            store_segment_tree(outputfile, segments, body_radius)
        else:
            print('No segments to save as a tree')

