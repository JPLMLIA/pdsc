"""
Map projection of PDS data products
"""
import numpy as np
from scipy.optimize import fmin
from sklearn.neighbors import DistanceMetric
# Requires geographiclib-1.49
from geographiclib.geodesic import Geodesic

from .util import registerer

# https://tharsis.gsfc.nasa.gov/geodesy.html
MARS_RADIUS_M = 3396200
MARS_FLATTENING = 1.0 / 169.8

LOCALIZERS = {}

register_localizer = registerer(LOCALIZERS)

def geodesic_distance(latlon1, latlon2, radius=MARS_RADIUS_M):
    haversine = DistanceMetric.get_metric('haversine')
    return float(radius*haversine.pairwise([latlon1], [latlon2]))

class Localizer(object):

    BODY_RADIUS = MARS_RADIUS_M
    DEFAULT_RESOLUTION_M = 0.1

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

@register_localizer('ctx')
class CtxLocalizer(GeodesicLocalizer):

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

@register_localizer('hirise')
class HiRiseLocalizer(GeodesicLocalizer):

    def __init__(self, metadata):
        super(HiRiseLocalizer, self).__init__(
            metadata.lines / 2.0, metadata.samples / 2.0,
            metadata.center_latitude, metadata.center_longitude,
            metadata.lines, metadata.samples,
            metadata.pixel_width,
            metadata.pixel_width,
            metadata.north_azimuth, 1
        )

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

def get_localizer(metadata):
    if metadata.instrument not in LOCALIZERS:
        raise ValueError(
            'No localizer implemented for %s' % metadata.instrument)

    return LOCALIZERS[metadata.instrument](metadata)
