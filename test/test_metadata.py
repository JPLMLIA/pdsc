"""
Unit Tests for Metadata Code
"""
import pytest
import datetime
import json

from .cosmic_test_tools import unit

from pdsc.metadata import (
    PdsMetadata, date_decoder, json_dumps, json_loads
)

@unit
def test_date_decoder():
    json_str = (
        '{ "foo": 5, "bar": { "__datetime__":'
        '{ "__val__": "1985-10-26T01:20:00.000",'
        '  "__fmt__": "%Y-%m-%dT%H:%M:%S.%f"}}}'
    )
    obj = json.loads(json_str, object_hook=date_decoder)
    assert obj['foo'] == 5
    assert obj['bar'] == datetime.datetime(1985, 10, 26, 1, 20)

@unit
def test_metadata_repr():
    meta = PdsMetadata(
        instrument='test_instrument', other_field='test_other'
    )
    expected = (
        "PdsMetadata(instrument='test_instrument', "
        "other_field='test_other')"
    )
    assert repr(meta) == expected

@unit
def test_metadata_consistency():
    meta = PdsMetadata(
        instrument='test_instrument', other_field_str='test_other',
        other_field_int=5, other_field_float=1.234,
        other_field_date=datetime.datetime(1985, 10, 26, 1, 20),
    )
    metas = [meta]

    meta_json_str = json_dumps(metas)
    metas_reloaded = json_loads(meta_json_str)

    assert len(metas_reloaded) == 1
    meta_reloaded = metas_reloaded[0]

    assert meta == meta_reloaded

    # Test not equal to an object of a different type
    assert not meta == None

@unit
def test_metadata_dump_fallback():
    meta = PdsMetadata(
        instrument='test_instrument', test_strange_type=set([1, 2, 3]),
    )

    # Cannot serialize `set` data type
    with pytest.raises(TypeError):
        json_dumps([meta])
