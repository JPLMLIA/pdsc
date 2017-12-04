"""
Classes for representing PDS metadata
"""
import json
from datetime import datetime

METADATA_DB_SUFFIX = '_metadata.db'
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

class PdsMetadata(object):

    def __init__(self, instrument, **kwargs):
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
    if '__datetime__' in obj:
        dt = obj['__datetime__']
        return datetime.strptime(dt['__val__'], dt['__fmt__'])
    else:
        return obj

def json_dumps(obj):
    return json.dumps(obj, cls=PdsMetadataJsonEncoder)

def json_loads(jstr):
    dicts = json.loads(jstr, object_hook=date_decoder)
    return [PdsMetadata(**d) for d in dicts]
