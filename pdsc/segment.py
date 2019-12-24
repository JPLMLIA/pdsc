"""
Code for decomposing an observation footprint into triangular segments and
storing these in a tree data structure for efficient querying
"""
from __future__ import print_function
from future.utils import with_metaclass
import abc
import pickle
import numpy as np
from sklearn.neighbors import BallTree
from Polygon import Polygon # (the Polygon2 package)

from .localization import (
    MARS_RADIUS_M, geodesic_distance, get_localizer,
    latlon2unit, xyz2latlon
)
from .util import standard_progress_bar

SEGMENT_DB_SUFFIX = '_segments.db'
"""
The suffix used to save segment SQL database files; the full filename for an
instrument will be the instrument name followed by the suffix
"""

SEGMENT_TREE_SUFFIX = '_segment_tree.pkl'
"""
The suffix used to save segment tree index files; the full filename for an
instrument will be the instrument name followed by the suffix
"""

INCLUSION_EPSILON = 1e-10 # corresponds to < 1 mm error in inclusion check
"""
Numerical precision for checking point inclusion in a segment; this is required
due to floating point error, and corresponds to a roughly 1 mm error on the
surface of Mars
"""

class PointQuery(object):
    """
    Encapsulates the information corresponding to a point inclusion query
    """

    def __init__(self, lat, lon, radius):
        """
        :param lat: latitude in degrees
        :param lon: east longitude in degrees
        :param radius: radius in meters

        This query is for all observations that overlap with a circle of the
        given radius around the specified location on the surface
        """
        if radius < 0:
            raise ValueError('Radius must be non-negative')
        if lat < -90 or lat > 90:
            raise ValueError('Latitude must be in range [-90, 90]')
        self.latlon = np.array([lat, lon])
        self.radius = radius
        self._xyz = None

    @property
    def xyz(self):
        """
        The point on a unit sphere expressed in Cartesian coordinates
        corresponding to the query point
        """
        if self._xyz is None:
            self._xyz = latlon2unit(self.latlon)
        return self._xyz

class SegmentTree(object):
    """
    Encapsulates a ball tree data structure used to efficiently find all
    observation segments within some radius of a query point
    """

    def __init__(self, segments, verbose=True):
        """
        :param segments: collection of all observation segments
        :param verbose: if ``True`` display a progress bar as the index is being
            built
        """
        progress = standard_progress_bar('Finding segment centers', verbose)
        data = np.deg2rad([
            [s.center_latitude, s.center_longitude]
            for s in progress(segments)
        ])

        progress = standard_progress_bar('Finding segment radii', verbose)
        self.max_radius = np.max([
            s.radius for s in progress(segments)
        ])

        if verbose: print('Building index...')
        self.ball_tree = BallTree(data, metric='haversine')
        if verbose: print('...done.')

    def query_point(self, point):
        """
        Queries the :py:class:`SegmentTree` for all segments that potentially
        overlap the given query point

        :param point: a :py:class:`PointQuery`

        :return: a collection of segment ids for segments that satisfy the query
        """
        total_radius = point.radius + self.max_radius
        haversine_radius = total_radius / MARS_RADIUS_M
        X = np.deg2rad(point.latlon).reshape((1, -1))
        return self.ball_tree.query_radius(X, haversine_radius)[0]

    def query_segment(self, segment):
        """
        Queries the :py:class:`SegmentTree` for all segments that potentially
        overlap the given segment

        :param segment: a :py:class:`TriSegment`

        :return: a collection of segment ids for segments that satisfy the query
        """
        total_radius = segment.radius + self.max_radius
        haversine_radius = total_radius / MARS_RADIUS_M
        X = np.deg2rad([[segment.center_latitude, segment.center_longitude]])
        return self.ball_tree.query_radius(X, haversine_radius)[0]

    def save(self, outputfile):
        """
        Saves this :py:class:`SegmentTree` to the specified file

        :param outputfile: output file path for pickled :py:class:`SegmentTree`
        """
        with open(outputfile, 'wb+') as f:
            pickle.dump(self, f)

    @staticmethod
    def load(inputfile):
        """
        Loads a :py:class:`SegmentTree` from the specified file

        :param inputfile: path to pickled :py:class:`SegmentTree`

        :return: parsed :py:class:`SegmentTree` object
        """
        with open(inputfile, 'rb') as f:
            return pickle.load(f)

class TriSegment(object):
    """
    Represent a single triangular segment into which observations are decomposed
    for indexing and efficient querying.
    """

    def __init__(self, latlon0, latlon1, latlon2):
        """
        The three points of the triangular segment are enumerated in
        *counterclockwise* order looking down on the surface. Each point is a
        pair of (latitude, longitude) in degrees (east longitude).

        :param latlon0:
            represents the first point (index 0) in a triangular segment
        :param latlon1:
            represents the second point (index 1) in a triangular segment
        :param latlon2:
            represents the third point (index 2) in a triangular segment
        """
        self.latlon_points = np.array([latlon0, latlon1, latlon2])
        self._center_longitude = None
        self._center_latitude = None
        self._xyz_points = None
        self._radius = None
        self._normals = None
        self._projection_plane = None

    def __repr__(self):
        return (
            'TriSegment(laton0=(%f, %f), laton1=(%f, %f), latlon2=(%f, %f))'
            % tuple(self.latlon_points.flat)
        )

    def center(self):
        """
        Computes the center of this :py:class:`TriSegment` by converting the
        latitude and longitude of the vertices to Cartesian coordiantes, taking
        an average, then converting back to spherical coordinates


        :return: a :py:class:`numpy.array` containing the latitude and east
            longitude (in degrees) of the center of this triangular segment
        """
        xyz_center = np.average(self.xyz_points, axis=0)
        return xyz2latlon(xyz_center)

    @property
    def xyz_points(self):
        """
        A 3-by-3 :py:class:`numpy.array` where each row contains a vertix of
        this :py:class:`TriSegment` represented in Cartesian coordinates
        """
        if self._xyz_points is None:
            self._xyz_points = np.vstack(
                list(map(latlon2unit, self.latlon_points)))
        return self._xyz_points

    @property
    def center_latitude(self):
        """
        The center latitude as compuated via :py:meth:`TriSegment.center`
        """
        if self._center_latitude is None:
            self._center_latitude, self._center_longitude = self.center()
        return self._center_latitude

    @property
    def center_longitude(self):
        """
        The center longitude as compuated via :py:meth:`TriSegment.center`
        """
        if self._center_longitude is None:
            self._center_latitude, self._center_longitude = self.center()
        return self._center_longitude

    @property
    def radius(self):
        """
        The radius of this :py:class:`TriSegment` in meters: the maximum
        distance from the center to any vertex
        """
        if self._radius is None:
            llcenter = np.deg2rad([self.center_latitude, self.center_longitude])
            self._radius = np.max([
                geodesic_distance(llcenter, np.deg2rad(ll))
                for ll in self.latlon_points
            ])
        return self._radius

    @property
    def normals(self):
        """
        A 3-by-3 :py:class:`numpy.array` where each row contains a normal vector
        to a plane that passes through two of the vertices of this
        :py:class:`TriSegment` and the origin
        """
        if self._normals is None:
            xyz = self.xyz_points
            self._normals = np.cross(
                xyz, [xyz[1], xyz[2], xyz[0]])
            self._normals = (
                self.normals.T / np.linalg.norm(self.normals, axis=1)
            ).T
        return self._normals

    @property
    def projection_plane(self):
        """
        Returns a 2-by-3 :py:class:`numpy.array` holding two orthonormal vectors
        defining a plane that is tangent the unit sphere at this segment's
        center
        """
        if self._projection_plane is None:
            normal = latlon2unit([self.center_latitude, self.center_longitude])
            I = np.eye(3)
            idx = np.argmin(np.abs(np.dot(I, normal)))
            u = np.cross(I[idx], normal)
            v = np.cross(u, normal)
            uv = np.vstack([u, v])
            self._projection_plane = (uv.T / np.linalg.norm(uv, axis=1)).T
        return self._projection_plane

    def is_inside(self, xyz):
        """
        Returns ``True`` iff the given vector falls within this
        :py:class:`TriSegment` (i.e., it is on the positive side of every plane
        defined by :py:meth:`TriSegment.normals`)
        """
        return np.all(np.dot(self.normals, xyz) >= -INCLUSION_EPSILON)

    def distance_to_point(self, xyz):
        """
        Computes the distance from the given point in Cartesian coordiantes to
        this :py:class:`TriSegment`

        If the point falls within the segment, the distance is zero; otherwise,
        the distance is the minimum geodesic distance between the point and any
        vertex or edge of the segment.

        The geodesic distance between this point and an edge is approximated as
        the geodesic distance between this point expressed in spherical
        coordinates and this point projected onto the edge plane (the plane
        formed by the two vertices of the edge and the origin), expressed in
        spherical coordinates.

        :param xyz: query point in Cartesian coordinates

        :return: distance (in meters) between this :py:class:`TriSegment` and
            the query point
        """
        if self.is_inside(xyz):
            return 0.0

        points_to_check = [
            corner for corner in self.latlon_points
        ]

        projections = xyz - (self.normals.T*np.dot(self.normals, xyz)).T
        for pi in projections:
            if np.sum(pi) != 0 and self.is_inside(pi):
                points_to_check.append(xyz2latlon(pi))

        p = np.deg2rad(xyz2latlon(xyz))
        return np.min([
            geodesic_distance(p, pi)
            for pi in np.deg2rad(points_to_check)
        ])

    def includes_point(self, point_query):
        """
        Determines whether the query point falls within this
        :py:class:`TriSegment`

        :param point_query: a :py:class:`PointQuery`

        :return: ``True`` iff the query point falls within the specified radius
            of this :py:class:`TriSegment`
        """
        if point_query.radius == 0:
            return self.is_inside(point_query.xyz)
        else:
            dist = self.distance_to_point(point_query.xyz)
            return (dist <= point_query.radius)

    def overlaps_segment(self, other):
        """
        Determines whether the query segment overlaps with this
        :py:class:`TriSegment`

        :param other: query :py:class:`TriSegment`

        :return: ``True`` iff the query segment overlaps with this segment
        """
        p_self = Polygon(np.dot(self.xyz_points, self.projection_plane.T))
        p_other = Polygon(np.dot(other.xyz_points, self.projection_plane.T))
        return ((p_self & p_other).area() > 0)

class SegmentedFootprint(with_metaclass(abc.ABCMeta, object)):
    """
    Base class for segmenting an observation footprint
    """

    def __init__(self, metadata, resolution, localizer_kwargs):
        """
        :param metadata:
            a :py:class:`~pdsc.metadata.PdsMetadata` object
        :param resolution:
            segmentation resolution (the maximum size of a segment edge)
        :param localizer_kwargs:
            the ``kwargs`` passed to the localizer used to convert observation
            pixel coordinates into real-world coordinates
        """
        self.metadata = metadata
        self.resolution = resolution
        self.localizer = get_localizer(metadata, **localizer_kwargs)
        n_row_chunks = int(np.ceil(
            self.localizer.observation_length_m / resolution
        ))
        n_col_chunks = int(np.ceil(
            self.localizer.observation_width_m / resolution
        ))
        row_idx = np.linspace(0, self.localizer.n_rows, n_row_chunks + 1)
        col_idx = np.linspace(0, self.localizer.n_cols, n_col_chunks + 1)
        xx, yy = np.meshgrid(row_idx, col_idx)
        self.pixel_grid = np.dstack(np.meshgrid(row_idx, col_idx))
        vfunc = np.frompyfunc(self.localizer.pixel_to_latlon, 2, 2)
        self.latlon_grid = np.dstack(vfunc(xx, yy)).astype(float)

        self.segments = list(self._segment())

    @abc.abstractmethod
    def _segment(self):
        """
        Abstract method for generating segments of an observation footprint
        """
        pass # pragma: no cover

class TriSegmentedFootprint(SegmentedFootprint):
    """
    Segments a footprint using triangular segments

    By using triangular segments, each segment is guaranteed to be convex, so
    determing whether a point falls within a segment can be done more
    efficiently than with rectangular segments.
    """

    def _segment(self):
        """
        Generates :py:class:`TriSegment` objects corresponding to the segments
        into which this observation footprint has been decomposed
        """
        L = self.latlon_grid
        for c in range(L.shape[1]-1):
            for r in range(L.shape[0]-1):
                if self.localizer.flight_direction > 0:
                    yield TriSegment(L[r, c], L[r, c+1], L[r+1, c])
                    yield TriSegment(L[r+1, c+1], L[r+1, c], L[r, c+1])
                else:
                    yield TriSegment(L[r, c], L[r+1, c], L[r, c+1])
                    yield TriSegment(L[r+1, c+1], L[r, c+1], L[r+1, c])
