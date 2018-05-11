"""
Map projection of PDS data products
"""
import numpy as np
from scipy.ndimage import zoom
from scipy.optimize import fmin
from sklearn.neighbors import DistanceMetric
# Requires geographiclib-1.49
from geographiclib.geodesic import Geodesic

from .util import registerer, standard_progress_bar

# https://tharsis.gsfc.nasa.gov/geodesy.html
MARS_RADIUS_M = 3396200
MARS_FLATTENING = 1.0 / 169.8

LOCALIZERS = {}

register_localizer = registerer(LOCALIZERS)

def geodesic_distance(latlon1, latlon2, radius=MARS_RADIUS_M):
    haversine = DistanceMetric.get_metric('haversine')
    return float(radius*haversine.pairwise([latlon1], [latlon2]))

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

class Localizer(object):

    BODY_RADIUS = MARS_RADIUS_M
    DEFAULT_RESOLUTION_M = 0.1
    NORMALIZED_PIXEL_SPACE = False

    def pixel_to_latlon(self, row, col):
        """
        Subclasses should implement this function
        """
        pass

    def latlon_to_pixel(self, lat, lon, resolution_m=None, resolution_pix=0.1):
        if resolution_m is None: resolution_m = self.DEFAULT_RESOLUTION_M

        loc = np.deg2rad([lat, lon])

        def f(u):
            loc_u = np.deg2rad(self.pixel_to_latlon(*u))
            return geodesic_distance(loc, loc_u, self.BODY_RADIUS)

        u0 = (0, 0)
        ustar = fmin(f, u0, xtol=resolution_pix, ftol=resolution_m, disp=False)
        return tuple(ustar)

class GeodesicLocalizer(Localizer):

    BODY = Geodesic(MARS_RADIUS_M, MARS_FLATTENING)

    def __init__(self, center_row, center_col, center_lat, center_lon,
            n_rows, n_cols, pixel_height_m, pixel_width_m,
            north_azimuth_deg, flight_direction=1):

        if n_rows <= 0: raise ValueError('No image rows')
        if n_cols <= 0: raise ValueError('No image columns')
        if pixel_height_m <= 0: raise ValueError('Negative pixel height')
        if pixel_width_m <= 0: raise ValueError('Negative pixel width')

        self.center_row = center_row
        self.center_col = center_col
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.n_rows = n_rows
        self.n_cols = n_cols
        self.pixel_height_m = pixel_height_m
        self.pixel_width_m = pixel_width_m
        self.north_azimuth_deg = north_azimuth_deg
        self.flight_direction = flight_direction
        self._height = None
        self._width = None

    @property
    def width(self):
        if self._width is None:
            self._width = self.pixel_width_m*self.n_cols
        return self._width

    @property
    def height(self):
        if self._height is None:
            self._height = self.pixel_height_m*self.n_rows
        return self._height

    def pixel_to_latlon(self, row, col):
        """
        Subclasses should implement this function
        """
        x_m = (col - self.center_col) * self.pixel_width_m
        y_m = (row - self.center_row) * self.pixel_height_m
        y_m *= self.flight_direction

        flight_line_point = self.BODY.Direct(
            self.center_lat, self.center_lon,
            90 - self.north_azimuth_deg,
            y_m
        )

        cross_line_point = self.BODY.Direct(
            flight_line_point['lat2'],
            flight_line_point['lon2'],
            flight_line_point['azi2'] - 90,
            x_m
        )

        return cross_line_point['lat2'], cross_line_point['lon2']

    def location_mask(self, subsample_rows=10, subsample_cols=25,
            reinterpolate=True, verbose=False):
        nrows = int(np.ceil(self.n_rows / subsample_rows))
        ncols = int(np.ceil(self.n_cols / subsample_cols))

        progress = standard_progress_bar('Computing Location Mask', verbose)
        L = np.array([
            [self.pixel_to_latlon(r, c)
                for c in np.linspace(0, self.n_cols - 1, ncols)]
            for r in progress(np.linspace(0, self.n_rows, nrows))
        ])
        if reinterpolate:
            zoom_factor = (
                float(self.n_rows) / L.shape[1],
                float(self.n_cols) / L.shape[0]
            )
            L = np.dstack([
                zoom(L[..., 0], zoom_factor, order=1, mode='nearest'),
                zoom(L[..., 1], zoom_factor, order=1, mode='nearest')
            ])
        return L

class FourCornerLocalizer(GeodesicLocalizer):

    def __init__(self, corners, n_rows, n_cols, flight_direction):

        if n_rows <= 0: raise ValueError('No image rows')
        if n_cols <= 0: raise ValueError('No image columns')

        self.n_rows = n_rows
        self.n_cols = n_cols
        self.flight_direction = flight_direction

        self.corners = np.asarray(corners)
        self.corner_matrix = np.array([
            [latlon2unit(corners[0]), latlon2unit(corners[3])],
            [latlon2unit(corners[1]), latlon2unit(corners[2])],
        ])

        corners = np.deg2rad(corners)
        self.pixel_height_m = (
            (
                geodesic_distance(corners[0], corners[3]) +
                geodesic_distance(corners[1], corners[2])
            ) / (2*n_rows)
        )
        self.pixel_width_m = (
            (
                geodesic_distance(corners[0], corners[1]) +
                geodesic_distance(corners[2], corners[3])
            ) / (2*n_cols)
        )

        self._height = None
        self._width = None

    def pixel_to_latlon(self, row, col):
        # Use bi-linear interpolation
        C = self.corner_matrix
        dx = np.array([self.n_cols - col, col])
        dy = np.array([self.n_rows - row, row])
        interpolated = np.array([
            np.dot(dx, np.dot(C[..., dim], dy.T))
            for dim in range(3)
        ]) / float(self.n_rows*self.n_cols)
        return tuple(xyz2latlon(interpolated))

class MapLocalizer(Localizer):

    MARS_RADIUS_POLAR = 3376200
    MARS_RADIUS_EQUATORIAL = 3396190

    def __init__(self, proj_type, proj_latitude, proj_longitude,
                 map_scale, row_offset, col_offset):
        self.proj_type = proj_type
        self.proj_latitude = np.deg2rad(proj_latitude)
        self.proj_longitude = np.deg2rad(proj_longitude)
        self.map_scale = map_scale
        self.row_offset = row_offset
        self.col_offset = col_offset

        a = self.MARS_RADIUS_POLAR*np.cos(self.proj_latitude)
        b = self.MARS_RADIUS_EQUATORIAL*np.sin(self.proj_latitude)
        self.R = (
            (self.MARS_RADIUS_POLAR*self.MARS_RADIUS_EQUATORIAL) /
            np.sqrt(a**2 + b**2)
        )
        self.cos_proj_lat = np.cos(self.proj_latitude)

    def _equirect_pixel_to_latlon(self, row, col):
        x = (col - self.col_offset)*self.map_scale
        y = -(row - self.row_offset)*self.map_scale
        return (
            np.rad2deg(y / self.R),
            np.rad2deg(
                self.proj_longitude + x / (self.R*self.cos_proj_lat)
            )
        )

    def _equirect_latlon_to_pixel(self, lat, lon):
        lat_rad = np.deg2rad(lat)
        lon_rad = np.deg2rad(lon)
        x = self.R*(lon_rad - self.proj_longitude)*self.cos_proj_lat
        y = self.R*lat_rad
        row = (-y / self.map_scale) + self.row_offset
        col = (x / self.map_scale) + self.col_offset
        return row, col

    def pixel_to_latlon(self, row, col):
        if self.proj_type == 'EQUIRECTANGULAR':
            return self._equirect_pixel_to_latlon(row, col)
        else:
            raise ValueError('Unknown projection type "%s"' % self.proj_type)

    def latlon_to_pixel(self, lat, lon):
        if self.proj_type == 'EQUIRECTANGULAR':
            return self._equirect_latlon_to_pixel(lat, lon)
        else:
            raise ValueError('Unknown projection type "%s"' % self.proj_type)

@register_localizer('ctx')
class CtxLocalizer(GeodesicLocalizer):

    DEFAULT_RESOLUTION_M = 1e-3

    BODY = Geodesic(MARS_RADIUS_M, 0.0) # Works better assuming sphere

    def __init__(self, metadata):
        flipped_na = (180 - metadata.north_azimuth
            if metadata.usage_note == 'F' else metadata.north_azimuth)
        super(CtxLocalizer, self).__init__(
            metadata.lines / 2.0, metadata.samples / 2.0,
            metadata.center_latitude, metadata.center_longitude,
            metadata.lines, metadata.samples,
            metadata.image_height / metadata.lines,
            metadata.image_width / metadata.samples,
            flipped_na, -1
        )

@register_localizer('themis_vis')
@register_localizer('themis_ir')
class ThemisLocalizer(GeodesicLocalizer):

    def __init__(self, metadata):
        super(ThemisLocalizer, self).__init__(
            metadata.lines / 2.0, metadata.samples / 2.0,
            metadata.center_latitude, metadata.center_longitude,
            metadata.lines, metadata.samples,
            metadata.pixel_aspect_ratio*metadata.pixel_width,
            metadata.pixel_width,
            metadata.north_azimuth, 1
        )

@register_localizer('hirise_edr')
class HiRiseLocalizer(GeodesicLocalizer):

    DEFAULT_RESOLUTION_M = 1e-6

    # Each CCD is 2048 pixels across, but they overlap
    # by 48 pixels.
    CCD_TABLE = {
        'RED0': -9000,
        'RED1': -7000,
        'RED2': -5000,
        'RED3': -3000,
        'RED4': -1000,
        'RED5':  1000,
        'RED6':  3000,
        'RED7':  5000,
        'RED8':  7000,
        'RED9':  9000,
        'IR10': -1000,
        'IR11':  1000,
        'BG12': -1000,
        'BG13':  1000,
    }
    CHANNEL_OFFSET = {
        0:  512,
        1: -512,
    }

    def __init__(self, metadata):
        helper_localizer = GeodesicLocalizer(
            metadata.lines / 2.0, metadata.samples / 2.0,
            metadata.center_latitude, metadata.center_longitude,
            metadata.lines, metadata.samples,
            metadata.pixel_width,
            metadata.pixel_width,
            metadata.north_azimuth, 1
        )
        edr_center_col = float(
            self.CCD_TABLE[metadata.ccd_name] +
            self.CHANNEL_OFFSET[metadata.channel_number]
        ) / metadata.binning
        edr_center_lat, edr_center_lon = helper_localizer.pixel_to_latlon(
            metadata.lines / 2.0, edr_center_col)

        super(HiRiseLocalizer, self).__init__(
            metadata.lines / 2.0, metadata.samples / 2.0,
            edr_center_lat, edr_center_lon,
            metadata.lines, metadata.samples,
            metadata.pixel_width,
            metadata.pixel_width,
            metadata.north_azimuth, 1
        )

class HiRiseRdrNoMapLocalizer(FourCornerLocalizer):

    DEFAULT_RESOLUTION_M = 1e-6
    NORMALIZED_PIXEL_SPACE = True

    def __init__(self, metadata):
        corners = np.array([
            [metadata.corner1_latitude, metadata.corner1_longitude],
            [metadata.corner2_latitude, metadata.corner2_longitude],
            [metadata.corner3_latitude, metadata.corner3_longitude],
            [metadata.corner4_latitude, metadata.corner4_longitude],
        ])
        super(HiRiseRdrNoMapLocalizer, self).__init__(
            corners, 1.0, 1.0, 1
        )

class HiRiseRdrLocalizer(MapLocalizer):

    DEFAULT_RESOLUTION_M = 1e-6
    NORMALIZED_PIXEL_SPACE = False

    def __init__(self, metadata):
        super(HiRiseRdrLocalizer, self).__init__(
            metadata.map_projection_type,
            metadata.projection_center_latitude,
            metadata.projection_center_longitude,
            metadata.map_scale,
            metadata.line_projection_offset,
            metadata.sample_projection_offset,
        )

@register_localizer('hirise_rdr')
def hirise_rdr_localizer(metadata, nomap=False):
    if nomap:
        return HiRiseRdrNoMapLocalizer(metadata)
    else:
        return HiRiseRdrLocalizer(metadata)

@register_localizer('moc')
class MocLocalizer(GeodesicLocalizer):

    BODY = Geodesic(MARS_RADIUS_M, 0.0) # Works better assuming sphere

    def __init__(self, metadata):
        flipped_na = (180 - metadata.north_azimuth
            if metadata.usage_note == 'F' else metadata.north_azimuth)
        super(MocLocalizer, self).__init__(
            metadata.lines / 2.0, metadata.samples / 2.0,
            metadata.center_latitude, metadata.center_longitude,
            metadata.lines, metadata.samples,
            metadata.image_height / metadata.lines,
            metadata.image_width / metadata.samples,
            flipped_na, -1
        )

def get_localizer(metadata, *args, **kwargs):
    if metadata.instrument not in LOCALIZERS:
        raise IndexError(
            'No localizer implemented for %s' % metadata.instrument)

    return LOCALIZERS[metadata.instrument](metadata, *args, **kwargs)
