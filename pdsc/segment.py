from __future__ import print_function
"""
Decomposes an observation footprint into triangular segments
"""
import pickle
import numpy as np
from sklearn.neighbors import BallTree
from progressbar import ProgressBar, Bar, ETA
from Polygon import Polygon # (the Polygon2 package)

from .localization import MARS_RADIUS_M, geodesic_distance, get_localizer

SEGMENT_DB_SUFFIX = '_segments.db'
SEGMENT_TREE_SUFFIX = '_segment_tree.pkl'
INCLUSION_EPSILON = 1e-10 # corresponds to < 1 mm error in inclusion check

def latlon2unit(latlon):
    llrad = np.deg2rad(latlon)
    sinll = np.sin(llrad)
    cosll = np.cos(llrad)
    return np.array([
        cosll[0]*cosll[1],
        cosll[0]*sinll[1],
        sinll[0]
    ])

def xyz2latlon(xyz):
    x, y, z = (xyz / np.linalg.norm(xyz))
    return np.rad2deg([
        np.arcsin(z), 
        np.arctan2(y, x)
    ])

class PointQuery(object):

    def __init__(self, lat, lon, radius):
        self.latlon = np.array([lat, lon])
        self.radius = radius
        self._xyz = None

    @property
    def xyz(self):
        if self._xyz is None:
            self._xyz = latlon2unit(self.latlon)
        return self._xyz

class SegmentTree(object):

    def __init__(self, segments, verbose=True):
        if verbose:
            progress = ProgressBar(
                widgets=['Finding segment centers: ', Bar('='), ' ', ETA()])
        else:
            progress = lambda p : p

        data = np.deg2rad([
            [s.center_latitude, s.center_longitude]
            for s in progress(segments)
        ])

        if verbose:
            progress = ProgressBar(
                widgets=['Finding segment radii: ', Bar('='), ' ', ETA()])
        else:
            progress = lambda p : p

        self.max_radius = np.max([
            s.radius for s in progress(segments)
        ])

        if verbose: print('Building index...')
        self.ball_tree = BallTree(data, metric='haversine')
        if verbose: print('...done.')

    def query_point(self, point):
        total_radius = point.radius + self.max_radius
        haversine_radius = total_radius / MARS_RADIUS_M
        X = np.deg2rad(point.latlon).reshape((1, -1))
        return self.ball_tree.query_radius(X, haversine_radius)[0]

    def query_segment(self, segment):
        total_radius = segment.radius + self.max_radius
        haversine_radius = total_radius / MARS_RADIUS_M
        X = np.deg2rad([[segment.center_latitude, segment.center_longitude]])
        return self.ball_tree.query_radius(X, haversine_radius)[0]

    def save(self, outputfile):
        with open(outputfile, 'w+') as f:
            pickle.dump(self, f)

    @staticmethod
    def load(inputfile):
        with open(inputfile, 'r') as f:
            return pickle.load(f)

class TriSegment(object):

    def __init__(self, latlon0, latlon1, latlon2):
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
        xyz_center = np.average(self.xyz_points, axis=0)
        return xyz2latlon(xyz_center)

    @property
    def xyz_points(self):
        if self._xyz_points is None:
            self._xyz_points = np.vstack(
                map(latlon2unit, self.latlon_points))
        return self._xyz_points

    @property
    def center_latitude(self):
        if self._center_latitude is None:
            self._center_latitude, self._center_longitude = self.center()
        return self._center_latitude

    @property
    def center_longitude(self):
        if self._center_longitude is None:
            self._center_latitude, self._center_longitude = self.center()
        return self._center_longitude

    @property
    def radius(self):
        if self._radius is None:
            llcenter = np.deg2rad([self.center_latitude, self.center_longitude])
            self._radius = np.min([
                geodesic_distance(llcenter, np.deg2rad(ll))
                for ll in self.latlon_points
            ])
        return self._radius

    @property
    def normals(self):
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
        if self._projection_plane is None:
            normal = latlon2unit([self.center_latitude, self.center_longitude])
            I = np.eye(3)
            proj = I - np.outer(np.dot(I, normal), normal)
            norms = np.linalg.norm(proj, axis=1)
            idx = np.argsort(norms)
            proj = proj[idx]
            norms = norms[idx]
            self._projection_plane = (proj[1:].T / norms[1:]).T
        return self._projection_plane

    def is_inside(self, xyz):
        return np.all(np.dot(self.normals, xyz) >= -INCLUSION_EPSILON)

    def distance_to_point(self, xyz):
        if self.is_inside(xyz):
            return 0.0

        points_to_check = [
            corner for corner in self.latlon_points
        ]

        projections = xyz - (self.normals.T*np.dot(self.normals, xyz)).T
        for pi in projections:
            if self.is_inside(pi):
                points_to_check.append(xyz2latlon(pi))

        p = np.deg2rad(xyz2latlon(xyz))
        return np.min([
            geodesic_distance(p, pi)
            for pi in np.deg2rad(points_to_check)
        ])

    def includes_point(self, point_query):
        if point_query.radius == 0:
            return self.is_inside(point_query.xyz)
        else:
            dist = self.distance_to_point(point_query.xyz)
            return (dist <= point_query.radius)

    def overlaps_segment(self, other):
        p_self = Polygon(np.dot(self.xyz_points, self.projection_plane.T))
        p_other = Polygon(np.dot(other.xyz_points, self.projection_plane.T))
        return ((p_self & p_other).area() > 0)

class SegmentedFootprint(object):

    def __init__(self, metadata, resolution):
        self.metadata = metadata
        self.resolution = resolution
        self.localizer = get_localizer(metadata)
        n_row_chunks = int(np.ceil(self.localizer.height / resolution))
        n_col_chunks = int(np.ceil(self.localizer.width / resolution))
        row_idx = np.linspace(0, self.localizer.n_rows-1, n_row_chunks + 1)
        col_idx = np.linspace(0, self.localizer.n_cols-1, n_col_chunks + 1)
        xx, yy = np.meshgrid(row_idx, col_idx)
        self.pixel_grid = np.dstack(np.meshgrid(row_idx, col_idx))
        vfunc = np.frompyfunc(self.localizer.pixel_to_latlon, 2, 2)
        self.latlon_grid = np.dstack(vfunc(xx, yy)).astype(float)

        self.segments = list(self._segment())

    def _segment(self):
        """
        Generate segments based on the lat-lon grid
        """
        pass

class TriSegmentedFootprint(SegmentedFootprint):

    def _segment(self):
        L = self.latlon_grid
        for c in range(L.shape[1]-1):
            for r in range(L.shape[0]-1):
                if self.localizer.flight_direction > 0:
                    yield TriSegment(L[r, c], L[r, c+1], L[r+1, c])
                    yield TriSegment(L[r+1, c+1], L[r+1, c], L[r, c+1])
                else:
                    yield TriSegment(L[r, c], L[r+1, c], L[r, c+1])
                    yield TriSegment(L[r+1, c+1], L[r, c+1], L[r+1, c])
