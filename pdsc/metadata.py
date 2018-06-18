"""
This module contains classes for representing and serializing PDS metadata
"""
import json
from datetime import datetime

METADATA_DB_SUFFIX = '_metadata.db'
"""
The suffix used to save metadata SQL database files; the full filename for an
instrument will be the instrument name followed by the suffix
"""

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
"""
The time format used by PDSC across all instruments
"""

class PdsMetadata(object):
    """
    Represents PDS metadata associated with an observation. The metadata
    available to PDSC corresponds to the metadata in the cumulative index files,
    which is sometimes a subset of what is available in the EDR/RDR headers.
    """

    def __init__(self, instrument, **kwargs):
        """
        :param instrument:
            PDSC instrument name

        :param \**kwargs:
            a dictionary mapping metadata field names to values
        """
        self.instrument = instrument
        self._kwargs = kwargs
        self._odict = dict(kwargs)
        self._odict['instrument'] = instrument
        for n, v in kwargs.items():
            setattr(self, n, v)

    def __repr__(self):
        values = ', '.join([
            ('%s=%s' % (n, repr(v)))
            for n, v in sorted(self._kwargs.items())
        ])
        return (
            'PdsMetadata(instrument=%s, %s)'
            % (repr(self.instrument), values)
        )

    def __eq__(self, other):
        if not isinstance(other, PdsMetadata):
            return False
        return self._odict == other._odict

class PdsMetadataJsonEncoder(json.JSONEncoder):
    """
    Overrides the :py:class:`json.JSONEncoder` class to provide support for
    serializing :py:class:`PdsMetadata` objects and date-valued metadata fields
    """

    def default(self, obj):
        if isinstance(obj, PdsMetadata):
            return obj._odict
        elif isinstance(obj, datetime):
            return {
                '__datetime__': {
                    '__fmt__': TIME_FORMAT,
                    '__val__': obj.strftime(TIME_FORMAT),
                }
            }
        else:
            return json.JSONEncoder.default(self, obj)

def date_decoder(obj):
    """
    Provides an ``object_hook`` to parse ``datetime`` objects out of JSON,
    assuming they were encoded using :py:class:`PdsMetadataJsonEncoder`

    :param obj:
        JSON object (``dict``)

    :return: ``obj`` if no date is detected; otherwise, return a
             :py:class:`datetime.datetime` object

    >>> json_str = (
    ...     '{ "foo": 5, "bar": { "__datetime__":'
    ...     '{ "__val__": "1985-10-26T01:20:00.000",'
    ...     '  "__fmt__": "%Y-%m-%dT%H:%M:%S.%f"}}}'
    ... )
    >>> import json
    >>> json.loads(json_str, object_hook=date_decoder)
    {u'foo': 5, u'bar': datetime.datetime(1985, 10, 26, 1, 20)}
    """
    if '__datetime__' in obj:
        dt = obj['__datetime__']
        return datetime.strptime(dt['__val__'], dt['__fmt__'])
    else:
        return obj

def json_dumps(obj):
    """
    Dumps a Python object to a JSON string, using the
    :py:class:`PdsMetadataJsonEncoder` to encode objects

    :param obj: Python object to encode

    :return: JSON string with encoded object

    >>> metadata = PdsMetadata('hirise_rdr', rows=100, cols=20)
    >>> json_dumps(metadata)
    '{"instrument": "hirise_rdr", "rows": 100, "cols": 20}'
    """
    return json.dumps(obj, cls=PdsMetadataJsonEncoder)

def json_loads(jstr):
    """
    Loads a list of :py:class:`PdsMetadata` objects from a JSON string; uses the
    :py:meth:`date_decoder` object hook to parse dates

    :param jstr: JSON string with list of :py:class:`PdsMetadata` objects

    :return: list of parsed :py:class:`PdsMetadata` objects

    >>> json_loads('[{"instrument": "hirise_rdr", "rows": 100, "cols": 20}]')
    [PdsMetadata(instrument=u'hirise_rdr', cols=20, rows=100)]
    """
    dicts = json.loads(jstr, object_hook=date_decoder)
    return [PdsMetadata(**d) for d in dicts]
