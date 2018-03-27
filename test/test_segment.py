"""
Unit Tests for Segment Code
"""
from nose.tools import assert_raises
from numpy.testing import assert_allclose

from pdsc.segment import PointQuery

def test_point_query():

    # Test various longitudes along equator
    point_query = PointQuery(0, 0, 0)
    assert_allclose(point_query.xyz, [1, 0, 0], atol=1e-9)

    point_query = PointQuery(0, 180, 0)
    assert_allclose(point_query.xyz, [-1, 0, 0], atol=1e-9)

    point_query = PointQuery(0, 90, 0)
    assert_allclose(point_query.xyz, [0, 1, 0], atol=1e-9)

    point_query = PointQuery(0, 270, 0)
    assert_allclose(point_query.xyz, [0, -1, 0], atol=1e-9)

    # Test negative longitudes
    point_query = PointQuery(0, -90, 0)
    assert_allclose(point_query.xyz, [0, -1, 0], atol=1e-9)

    # Test nonzero latitudes
    point_query = PointQuery(90, 0, 0)
    assert_allclose(point_query.xyz, [0, 0, 1], atol=1e-9)

    point_query = PointQuery(-90, 0, 0)
    assert_allclose(point_query.xyz, [0, 0, -1], atol=1e-9)

    # Radius must be non-negative
    assert_raises(ValueError, PointQuery, 0, 0, -1)

    # Latitude in range [-90, 90]
    assert_raises(ValueError, PointQuery, -91, 0, 0)
    assert_raises(ValueError, PointQuery, 91, 0, 0)
