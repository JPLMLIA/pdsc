"""
Unit Tests for Segment Code
"""
import pytest
import numpy as np
from numpy.testing import assert_allclose

from cosmic_test_tools import unit

from pdsc.segment import PointQuery, TriSegment

@unit
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
    pytest.raises(ValueError, PointQuery, 0, 0, -1)

    # Latitude in range [-90, 90]
    pytest.raises(ValueError, PointQuery, -91, 0, 0)
    pytest.raises(ValueError, PointQuery, 91, 0, 0)

@unit
def test_trisegment():

    # Test basic segment
    segment = TriSegment([0, 0], [0, 90], [90, 0])

    assert (str(segment) ==
        'TriSegment(laton0=(0.000000, 0.000000), '
        'laton1=(0.000000, 90.000000), '
        'latlon2=(90.000000, 0.000000))'
    )

    # Test Spherical to XYZ
    assert_allclose(segment.xyz_points, np.eye(3), atol=1e-9)

    expected_center = [np.rad2deg(np.arcsin(0.57735026919)), 45]

    # Test segment center
    assert_allclose(segment.center(), expected_center)

    # Test center properties
    assert_allclose(
        segment.center(),
        [segment.center_latitude, segment.center_longitude]
    )
