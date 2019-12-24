"""
Unit Tests for Segment Code
"""
import mock
import pytest
import numpy as np
from numpy.testing import (
    assert_allclose, assert_almost_equal
)

from .cosmic_test_tools import unit, Approximately

from pdsc.segment import (
    PointQuery, TriSegment, SegmentTree, SegmentedFootprint,
    TriSegmentedFootprint, latlon2unit, MARS_RADIUS_M
)
from pdsc.metadata import PdsMetadata
from pdsc.localization import get_localizer

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

    # Test center property when longitude is computed first
    segment2 = TriSegment(*segment.latlon_points)
    assert segment2.center_longitude == segment.center_longitude

    uv = segment.projection_plane
    assert_allclose(np.dot(uv[0], uv[1]), 0) # Ortho...
    assert_allclose(np.linalg.norm(uv, axis=1), [1, 1]) # ...normal
    # Vectors tangent to center point vector
    xyz_center = latlon2unit(segment.center())
    assert_allclose(np.dot(uv, xyz_center.T), [0, 0])

    normals = segment.normals
    expected_normals = np.array([
        [0, 0, 1],
        [1, 0, 0],
        [0, 1, 0],
    ])
    assert_allclose(expected_normals, normals, atol=1e-9)

    # Test strict inclusion
    assert segment.is_inside([1, 1, 1])
    assert not segment.is_inside([-1, 1, 1])
    assert not segment.is_inside([1, -1, 1])
    assert not segment.is_inside([1, 1, -1])
    assert segment.is_inside([0, 1, 1]) # Edge case
    assert segment.is_inside([0, 0, 0]) # Corner case

    # Test distance
    quarter_circ = np.pi*MARS_RADIUS_M/2.0
    assert_allclose(segment.distance_to_point(xyz_center), 0)
    assert_allclose(segment.distance_to_point([-1, 0, 0]), quarter_circ)
    assert_allclose(segment.distance_to_point([0, -1, 0]), quarter_circ)
    assert_allclose(segment.distance_to_point([0, 0, -1]), quarter_circ)

    # Test inclusion queries
    assert segment.includes_point(PointQuery(0, 0, 0))
    assert not segment.includes_point(PointQuery(0, 270, 0))
    assert segment.includes_point(PointQuery(45, 45, 0))
    assert segment.includes_point(PointQuery(45, 45, 1))
    assert segment.includes_point(PointQuery(0, 135, quarter_circ))
    assert not segment.includes_point(PointQuery(-45, 225, quarter_circ))

@unit
@pytest.mark.parametrize(
    'latlon1,latlon2,overlaps',
    [
        (
            [(0, 0), (0, 90), (90, 0)],
            [(0, 45), (0, 75), (75, 75)],
            True
        ),
        (
            [(0, 0), (0, 90), (90, 0)],
            [(0, 125), (0, 180), (75, 180)],
            False
        ),
        (
            [(0, 0), (0, 90), (90, 0)],
            [(0, 125), (0, 180), (90, 180)],
            False
        ),
    ]
)
def test_segment_overlap(latlon1, latlon2, overlaps):
    segment1 = TriSegment(*latlon1)
    segment2 = TriSegment(*latlon2)
    assert segment1.overlaps_segment(segment2) == overlaps

@unit
@mock.patch('pdsc.segment.open', new_callable=mock.mock_open)
@mock.patch('pdsc.segment.BallTree', autospec=True)
@mock.patch('pdsc.pickle.dump', autospec=True)
@mock.patch('pdsc.pickle.load', autospec=True)
def test_segment_tree(mock_pickle_load, mock_pickle_dump, mock_balltree, mock_open):

    segment = TriSegment([0, 0], [0, 90], [90, 0])
    tree = SegmentTree([segment], verbose=False)

    expected_data = np.array([[np.arcsin(0.57735026919), np.deg2rad(45)]])

    mock_balltree.assert_called_once_with(
        Approximately(expected_data), metric='haversine'
    )

    point_query = PointQuery(0, 0, 0)
    tree.query_point(point_query)
    tree.ball_tree.query_radius.assert_called_with(
        Approximately(np.array([[1e-12, 0]])), Approximately(0.9553166181245093)
    )

    tree.query_segment(segment)
    args, kwargs = tree.ball_tree.query_radius.call_args_list[-1]
    tree.ball_tree.query_radius.assert_called_with(
        Approximately(expected_data), Approximately(1.9106332362490186)
    )

    # Test saving object
    assert tree.save('output') is None
    mock_open.assert_called_with('output', 'wb+')
    mock_pickle_dump.assert_called_once_with(tree, mock.ANY)

    # Test loading object
    mock_pickle_load.return_value = 'object'
    assert SegmentTree.load('input') == 'object'
    mock_open.assert_called_with('input', 'rb')
    mock_pickle_load.assert_called_once_with(mock.ANY)

@unit
def test_abstract_method():
    with pytest.raises(TypeError):
        seg = SegmentedFootprint(None, None, None)

@unit
def test_segmentation():
    themis_meta = PdsMetadata(
        'themis_vis', lines=100, samples=50,
        center_latitude=0, center_longitude=0,
        pixel_width=1.0, pixel_aspect_ratio=1.0,
        north_azimuth=0.0,
    )
    ctx_meta = PdsMetadata(
        'ctx', lines=100, samples=50,
        center_latitude=0, center_longitude=0,
        image_width=50.0, image_height=100.0,
        north_azimuth=0.0, usage_note='N',
    )

    test_cases = [
        (1, 1, True),
        (-10, -10, False),
        (50, 25, True),
        (150, 75, False),
    ]
    resolutions = [
        (50.0, 4),
        (100.0, 2),
    ]

    for meta in [themis_meta, ctx_meta]:
        loc = get_localizer(meta)
        for resolution, exp_segs in resolutions:

            tsf = TriSegmentedFootprint(meta, resolution, {})
            assert len(tsf.segments) == exp_segs

            for row, col, exp in test_cases:
                lat, lon = loc.pixel_to_latlon(row, col)
                n_inclusions = sum([
                    segment.includes_point(PointQuery(lat, lon, 0))
                    for segment in tsf.segments
                ])
                if exp:
                    # Could be in up to 2 segments if it fall along a boundary
                    assert n_inclusions in (1, 2)
                else:
                    assert n_inclusions == 0
